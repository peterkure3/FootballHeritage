"""Train isolated domestic league models with date-blocked selection and calibration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import LabelEncoder

from config import MODEL_DIR
from models.features import FEATURE_NAMES, build_feature_frame
from models.league_data import load_histories
from models.selection import expert_candidates
from models.training_resources import training_threads
from models.validation import chronological_split, probability_metrics

DOMESTIC_LEAGUES = ['PD', 'BL1', 'SA', 'FL1', 'PPL', 'DED', 'ELC', 'BSA']


def train_league(code: str, history, directory: Path, threads: int = 2, trees: int = 200) -> dict:
    if len(history) < 1000:
        raise ValueError(f'{code}: need 1000 completed matches; found {len(history)}')
    X, fixtures = build_feature_frame(history)
    splits = chronological_split(fixtures.date)
    encoder = LabelEncoder().fit(['away_win', 'draw', 'home_win'])
    y = encoder.transform(fixtures.result)
    for indices in splits.values():
        if len(indices) < 30 or len(np.unique(y[indices])) != 3:
            raise ValueError(f'{code}: all split periods need 30 games and three outcome classes')
    train, tune, calibration, test = [splits[key] for key in ['train', 'tune', 'calibration', 'test']]
    # Historical archive odds have no verified observation times. Exclude every market feature.
    columns = FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    candidates = expert_candidates(columns, trees)
    scores = {}
    with training_threads(threads):
        for name, candidate in candidates.items():
            print(f'{code}: fitting {name} ({len(train)} training games)', flush=True)
            candidate.fit(X.iloc[train], y[train])
            scores[name] = probability_metrics(y[tune], candidate.predict_proba(X.iloc[tune]), list(encoder.classes_))
        selected = min(scores, key=lambda name: scores[name]['log_loss'])
        development = np.concatenate([train, tune])
        estimator = clone(candidates[selected]).fit(X.iloc[development], y[development])
        model = CalibratedClassifierCV(FrozenEstimator(estimator), method='sigmoid', cv=2)
        model.fit(X.iloc[calibration], y[calibration])
        probabilities = model.predict_proba(X.iloc[test])
    counts = np.bincount(y[development], minlength=3) + 1
    baseline = np.tile(counts/counts.sum(), (len(test), 1))
    metrics = {'competition_code': code, 'status': 'evaluated_league_candidate', 'active': False,
        'trained_at': datetime.now(timezone.utc).isoformat(), 'classes': list(encoder.classes_),
        'features': FEATURE_NAMES, 'used_features': columns, 'market_features_used': False,
        'selected': selected, 'tuning': scores,
        'test': probability_metrics(y[test], probabilities, list(encoder.classes_)),
        'test_development_prior': probability_metrics(y[test], baseline, list(encoder.classes_)),
        'training_games': len(fixtures), 'history_through': fixtures.date.max().isoformat(),
        'splits': {key: {'games': len(indices), 'start': fixtures.iloc[indices].date.min().isoformat(),
                         'end': fixtures.iloc[indices].date.max().isoformat()} for key, indices in splits.items()}}
    directory.mkdir(parents=True, exist_ok=False)
    fixtures.to_parquet(directory/'dataset.parquet', index=False)
    joblib.dump(model, directory/'model.pkl')
    for filename in ['dataset.parquet', 'model.pkl']:
        metrics[filename.replace('.', '_') + '_sha256'] = hashlib.sha256((directory/filename).read_bytes()).hexdigest()
    # Verify artifact replay against the untouched test period before publishing its registry entry.
    with training_threads(threads):
        np.testing.assert_allclose(joblib.load(directory/'model.pkl').predict_proba(X.iloc[test]), probabilities, atol=1e-12)
    replay = fixtures.iloc[test][['date', 'home_team', 'away_team', 'result']].copy()
    for index, name in enumerate(encoder.classes_):
        replay[name] = probabilities[:, index]
    replay.to_csv(directory/'holdout_predictions.csv', index=False)
    (directory/'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(f"{code}: test accuracy={metrics['test']['accuracy']:.4f}, log_loss={metrics['test']['log_loss']:.4f}", flush=True)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--leagues', nargs='+', default=DOMESTIC_LEAGUES)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--publish', action='store_true', help='Generate and publish evaluated league forecasts after training')
    args = parser.parse_args()
    if args.threads < 1 or any(code not in [*DOMESTIC_LEAGUES, 'PL', 'CL'] for code in args.leagues):
        parser.error('Use supported league codes and at least one thread')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = args.output_dir or MODEL_DIR/'league_models'/stamp
    output.mkdir(parents=True, exist_ok=False)
    identities = (Path(__file__).parent/'league_identities.json').read_bytes()
    (output/'league_identities.json').write_bytes(identities)
    histories = load_histories()
    insufficient = {code: len(histories.get(code, [])) for code in args.leagues
                    if len(histories.get(code, [])) < 1000}
    if insufficient:
        raise ValueError(f'League histories below the 1000-game minimum: {insufficient}')
    report = {'run_id': output.name, 'created_at': datetime.now(timezone.utc).isoformat(),
              'identity_sha256': hashlib.sha256(identities).hexdigest(), 'leagues': {}}
    for code in args.leagues:
        report['leagues'][code] = train_league(code, histories[code], output/code, args.threads)
        (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'League model report: {output / "report.json"}', flush=True)
    if args.publish:
        from models.predict_football_leagues import predict
        forecasts = predict(output, publish=True)
        print(f"Published {len(forecasts['predictions'])} league forecasts", flush=True)


if __name__ == '__main__':
    main()
