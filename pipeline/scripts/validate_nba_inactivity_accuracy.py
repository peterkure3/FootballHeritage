"""Frozen, retrospective NBA inactivity validation. No production writes."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from models.nba_accuracy_research import fit, inactivity_features
from models.sport_features import build_features
from models.training_resources import training_threads
from models.validation import probability_metrics


def run(bundle: Path, output: Path):
    metadata = json.loads((bundle/'metrics.json').read_text())
    for file, key in [('model.pkl', 'model_sha256'), ('dataset.parquet', 'dataset_sha256')]:
        if hashlib.sha256((bundle/file).read_bytes()).hexdigest() != metadata[key]:
            raise ValueError('Frozen NBA artifact changed')
    games = pd.read_parquet(bundle/'dataset.parquet')
    splits = {}
    for name, bounds in metadata['splits'].items():
        mask = games.date.between(pd.Timestamp(bounds['start']), pd.Timestamp(bounds['end']))
        splits[name] = np.flatnonzero(mask)
        if len(splits[name]) != bounds['samples']:
            raise ValueError('Original NBA split membership changed')
    train = np.concatenate([splits['train'], splits['tune']]); calibration = splits['calibration']; test = splits['test']
    if set(games.league) != {'basketball_nba'} or not games.result.isin(metadata['classes']).all():
        raise ValueError('Invalid NBA validation corpus')
    classes = metadata['classes']; y = pd.Categorical(games.result, categories=classes).codes
    original = joblib.load(bundle/'model.pkl')
    with training_threads(2):
        baseline = original.predict_proba(build_features(games, 'basketball').iloc[test])
        baseline_metrics = probability_metrics(y[test], baseline, classes)
        for key in ['accuracy', 'log_loss', 'brier_score']:
            if not np.isclose(baseline_metrics[key], metadata['test'][key], rtol=0, atol=1e-12):
                raise ValueError('Original NBA metric replay failed')
        X = inactivity_features(games)
        model = fit('inactivity_reset', X, y, games.date, train, calibration)
        updated = model.predict_proba(X.iloc[test])
    candidate_metrics = probability_metrics(y[test], updated, classes)
    labels = y[test]; one_hot = np.eye(2)[labels]
    paired = {
        'accuracy': (updated.argmax(axis=1) == labels).astype(float) - (baseline.argmax(axis=1) == labels),
        'log_loss': -np.log(np.clip(updated[np.arange(len(test)), labels], 1e-15, 1))
                    + np.log(np.clip(baseline[np.arange(len(test)), labels], 1e-15, 1)),
        'brier_score': ((updated-one_hot)**2).sum(axis=1) - ((baseline-one_hot)**2).sum(axis=1)}
    days = games.iloc[test].date.dt.normalize().to_numpy(); unique = np.unique(days)
    indices = [np.flatnonzero(days == day) for day in unique]; rng = np.random.default_rng(42)
    bootstraps = {key: [] for key in paired}
    for _ in range(2000):
        draw = np.concatenate([indices[i] for i in rng.integers(0, len(indices), len(indices))])
        for key, delta in paired.items():
            bootstraps[key].append(float(delta[draw].mean()))
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump(model, output/'history_model.pkl')
    frame = games.iloc[test][['date', 'home_team', 'away_team', 'result']].copy()
    for name, p in [('baseline', baseline), ('inactivity_reset', updated)]:
        for index, label in enumerate(classes):
            frame[name+'_'+label] = p[:, index]
    frame.to_csv(output/'predictions.csv', index=False)
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': 'retrospective_research_validation',
        'dataset_sha256': metadata['dataset_sha256'], 'baseline_model_sha256': metadata['model_sha256'],
        'candidate_model_sha256': hashlib.sha256((output/'history_model.pkl').read_bytes()).hexdigest(),
        'feature_contract': {'schema': 'nba-inactivity-90-50-research-1.0', 'columns': list(X.columns),
            'inactive_days': 90, 'retained_elo_deviation': .5, 'clear_rolling_history': True,
            'availability': 'Inherited dataset timestamps with next-UTC-day floor, not verified observation provenance'},
        'splits': metadata['splits'], 'classes': classes,
        'metrics': {'baseline': baseline_metrics, 'inactivity_reset': candidate_metrics},
        'paired_difference': {key: {'mean': float(delta.mean()),
            'match_day_bootstrap_95_percent_interval': np.quantile(bootstraps[key], [.025, .975]).tolist()}
            for key, delta in paired.items()}, 'bootstrap': {'iterations': 2000, 'seed': 42, 'unit': 'UTC match day'},
        'source_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in
            ['models/nba_accuracy_research.py', 'scripts/validate_nba_inactivity_accuracy.py']},
        'limitations': ['Reserved period already inspected: retrospective, not fresh holdout.',
            'Uneven source coverage and inherited historical availability assumptions.',
            'History-model pickle requires inactivity features; do not serve with production features.',
            'Bootstrap does not account for all cross-day dependence or model-selection uncertainty.'],
        'production_changed': False, 'active': False, 'promotion_authorized': False}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'metrics': {name: {k: value[k] for k in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for name, value in report['metrics'].items()}, 'paired_difference': report['paired_difference']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.bundle, args.output)
