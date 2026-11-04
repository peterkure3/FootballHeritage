"""Paired causal historical replay of existing soccer artifacts; no retraining."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from config import MODEL_DIR
from models.features import FEATURE_NAMES, build_feature_frame
from models.train_model_v2 import load_training_data
from models.training_resources import training_threads
from models.validation import probability_metrics


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cutoff = pd.Timestamp.now(tz='UTC').normalize()
    raw = load_training_data()
    raw = raw[raw.date.lt(cutoff)].copy()
    X, fixtures = build_feature_frame(raw)
    complete = fixtures.result.notna()
    X = X.loc[complete].reset_index(drop=True)
    fixtures = fixtures.loc[complete].reset_index(drop=True)
    if fixtures.empty:
        raise ValueError('No completed history')
    classes = ['away_win', 'draw', 'home_win']
    y = pd.Categorical(fixtures.result, categories=classes).codes
    if (y < 0).any():
        raise ValueError('Unknown outcome')
    manifests, probabilities, provenance = {}, {}, {}
    for version, directory in [('2.0.0', MODEL_DIR), ('2.1.0', args.candidate)]:
        files = {name: directory / f'{name}_v{version}.pkl' for name in ['model', 'features', 'label_encoder']}
        manifest_path = directory / f'metrics_v{version}.json'
        manifests[version] = json.loads(manifest_path.read_text())
        model, features, encoder = [joblib.load(files[name]) for name in ['model', 'features', 'label_encoder']]
        expected = FEATURE_NAMES[:-1] if version == '2.0.0' else FEATURE_NAMES
        if features != expected or model.n_features_in_ != len(features):
            raise ValueError(f'Unexpected feature contract for {version}')
        if list(encoder.classes_) != classes or list(model.classes_) != [0, 1, 2]:
            raise ValueError('Unexpected class ordering')
        if (directory / f'scaler_v{version}.pkl').exists():
            raise ValueError('External scaler requires explicit support')
        print(f'Predicting {version} on {len(X)} fixtures', flush=True)
        with training_threads(2):
            probabilities[version] = model.predict_proba(X[features])
        provenance[version] = {'directory': str(directory.resolve()), 'type': type(model).__name__,
                               'trained_at': manifests[version]['trained_at'],
                               'sha256': {name: digest(path) for name, path in files.items()},
                               'manifest_sha256': digest(manifest_path)}
    covered = X.odds_missing.eq(0).to_numpy()
    candidate_test = manifests['2.1.0']['data_report']['splits']['test']
    candidate_start = pd.to_datetime(candidate_test['start'], utc=True)
    candidate_end = pd.to_datetime(candidate_test['end'], utc=True)
    latest_fit = max(pd.to_datetime(m['trained_at'], utc=True) for m in manifests.values())
    masks = {'all_history_mixed_training_overlap': np.ones(len(y), dtype=bool),
             'with_recorded_odds': covered, 'without_odds': ~covered,
             'candidate_test_dates_baseline_overlap_unknown': fixtures.date.between(candidate_start, candidate_end).to_numpy(),
             'after_both_artifacts_created': fixtures.date.gt(latest_fit).to_numpy()}
    for year in sorted(fixtures.date.dt.year.unique()):
        masks[f'year_{year}'] = fixtures.date.dt.year.eq(year).to_numpy()
    for league in sorted(fixtures.competition.dropna().unique()):
        masks[f'competition_{league}'] = fixtures.competition.eq(league).to_numpy()
    summary = {}
    for name, mask in masks.items():
        entry = {'samples': int(mask.sum())}
        if mask.any():
            entry['models'] = {v: probability_metrics(y[mask], p[mask], classes) for v, p in probabilities.items()}
            market_mask = mask & covered
            if market_mask.any():
                market = X.loc[market_mask, ['fair_away_prob', 'fair_draw_prob', 'fair_home_prob']].to_numpy()
                entry['market_same_recorded_odds'] = probability_metrics(y[market_mask], market, classes)
        summary[name] = entry
    output = fixtures.copy()
    output['odds_available'] = covered
    for version, p in probabilities.items():
        for i, outcome in enumerate(classes):
            output[f'{version}_{outcome}'] = p[:, i]
        output[f'{version}_prediction'] = np.asarray(classes)[p.argmax(axis=1)]
        output[f'{version}_correct'] = p.argmax(axis=1) == y
    output.to_csv(args.output / 'predictions.csv', index=False)
    X.to_parquet(args.output / 'causal_features.parquet', index=False)
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'cutoff_exclusive': cutoff.isoformat(),
              'start': fixtures.date.min().isoformat(), 'end': fixtures.date.max().isoformat(),
              'provenance': provenance, 'summary': summary,
              'limitations': [
                  'All-history scores include training overlap and are not out-of-sample performance.',
                  'Legacy training membership is unavailable; candidate test dates do not establish a joint holdout.',
                  'Both artifacts receive the same causal feature definitions. Legacy serving uses different form and venue approximations; this is not an exact replay of legacy production.',
                  'Historical prices lack complete observation-time provenance; no executable ROI or profitability claim.',
                  'Features only consume results from earlier UTC days; frozen models may themselves have learned later labels.',
                  'Missing odds use the shared fallback inputs for 2.0.0 and the history expert for 2.1.0.']}
    report['prediction_sha256'] = digest(args.output / 'predictions.csv')
    (args.output / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# Frozen soccer model historical comparison', '', f'Completed fixtures: {len(y):,}; {report["start"]} to {report["end"]}.', '',
             '| Segment | Matches | 2.0.0 accuracy | 2.1.0 accuracy | 2.0.0 log loss | 2.1.0 log loss |',
             '|---|---:|---:|---:|---:|---:|']
    for name, entry in summary.items():
        if 'models' in entry:
            a, b = entry['models']['2.0.0'], entry['models']['2.1.0']
            lines.append(f'| {name} | {entry["samples"]} | {a["accuracy"]:.2%} | {b["accuracy"]:.2%} | {a["log_loss"]:.4f} | {b["log_loss"]:.4f} |')
        else:
            lines.append(f'| {name} | 0 | — | — | — | — |')
    lines += ['', '## Interpretation limits', '', *['- ' + item for item in report['limitations']]]
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({name: {v: {k: score[k] for k in ['samples', 'accuracy', 'log_loss', 'brier_score']} for v, score in item.get('models', {}).items()} for name, item in summary.items() if not name.startswith(('year_', 'competition_'))}, indent=2))


if __name__ == '__main__':
    main()
