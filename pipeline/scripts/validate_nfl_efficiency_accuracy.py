"""Paired retrospective NFL history/efficiency validation; research artifacts only."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from models.nfl_accuracy_research import sha
from models.gridiron_sources import summarize_pbp
from models.gridiron_efficiency import build_efficiency_features
from models.sport_features import HISTORY_FEATURES
from models.train_sports import supervised_splits, select_expert
from models.training_resources import training_threads
from models.validation import probability_metrics


def run(bundle: Path, capture: Path, development: Path, output: Path):
    metadata = json.loads((bundle/'metrics.json').read_text())
    dev = json.loads((development/'report.json').read_text())
    if not dev['promising'] or dev['dataset_sha256'] != metadata['dataset_sha256']:
        raise ValueError('Frozen development evidence mismatch')
    for file, digest in dev['source_sha256'].items():
        if sha(Path(file)) != digest:
            raise ValueError('Frozen NFL feature/selection code changed')
    for file, digest in dev['raw_pbp_sha256'].items():
        if sha(capture/file) != digest:
            raise ValueError('Frozen raw play-by-play changed')
    for file, key in [('dataset.parquet', 'dataset_sha256'), ('model.pkl', 'model_sha256')]:
        if sha(bundle/file) != metadata[key]:
            raise ValueError('Frozen NFL artifact changed')
    games = pd.read_parquet(bundle/'dataset.parquet')
    X = build_efficiency_features(games, summarize_pbp(capture))
    np.testing.assert_allclose(X, pd.read_parquet(bundle/'features.parquet'), rtol=0, atol=1e-12)
    splits, exclusions = supervised_splits(games, 'nfl')
    for name, index in splits.items():
        if (len(index) != metadata['splits'][name]['samples']
                or games.iloc[index].date.min() != pd.Timestamp(metadata['splits'][name]['start'])
                or games.iloc[index].date.max() != pd.Timestamp(metadata['splits'][name]['end'])):
            raise ValueError('Original purged NFL split changed')
    classes = ['away_win', 'home_win']
    y = np.array([classes.index(value) if value in classes else -1 for value in games.result])
    with training_threads(2):
        efficiency = joblib.load(bundle/'model.pkl').predict_proba(X.iloc[splits['test']])
        replay = probability_metrics(y[splits['test']], efficiency, classes)
        for key in ['accuracy', 'log_loss', 'brier_score']:
            if not np.isclose(replay[key], metadata['test'][key], rtol=0, atol=1e-12):
                raise ValueError('Original efficiency metric replay failed')
        model, selection = select_expert(X, y, splits, HISTORY_FEATURES, np.ones(len(games), dtype=bool))
        if model is None:
            raise ValueError('History comparator could not fit original splits')
        history = model.predict_proba(X.iloc[splits['test']][HISTORY_FEATURES])
    labels = y[splits['test']]; one_hot = np.eye(2)[labels]
    differences = {'accuracy': (efficiency.argmax(axis=1)==labels).astype(float)-(history.argmax(axis=1)==labels),
        'log_loss': -np.log(np.clip(efficiency[np.arange(len(labels)), labels], 1e-15, 1))
                    +np.log(np.clip(history[np.arange(len(labels)), labels], 1e-15, 1)),
        'brier_score': ((efficiency-one_hot)**2).sum(axis=1)-((history-one_hot)**2).sum(axis=1)}
    days = games.iloc[splits['test']].date.dt.normalize().to_numpy()
    blocks = [np.flatnonzero(days==day) for day in np.unique(days)]
    rng = np.random.default_rng(42); bootstrap = {key: [] for key in differences}
    for _ in range(2000):
        indices = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        for key, delta in differences.items():
            bootstrap[key].append(float(delta[indices].mean()))
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump(model, output/'history_comparator.pkl')
    frame = games.iloc[splits['test']][['date', 'provider_event_id', 'home_team', 'away_team', 'result']].copy()
    for name, p in [('history', history), ('efficiency', efficiency)]:
        for i, label in enumerate(classes):
            frame[name+'_'+label] = p[:, i]
    frame.to_csv(output/'predictions.csv', index=False)
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': 'retrospective_efficiency_ablation',
        'dataset_sha256': metadata['dataset_sha256'], 'efficiency_model_sha256': metadata['model_sha256'],
        'history_comparator_sha256': sha(output/'history_comparator.pkl'), 'selection': {'history': selection,
            'efficiency': metadata['selection']}, 'classes': classes, 'splits': metadata['splits'],
        'split_exclusions': exclusions, 'metrics': {'history': probability_metrics(labels, history, classes), 'efficiency': replay},
        'paired_difference': {key: {'mean': float(delta.mean()),
            'match_day_bootstrap_95_percent_interval': np.quantile(bootstrap[key], [.025, .975]).tolist()}
            for key, delta in differences.items()}, 'bootstrap': {'resamples': 2000, 'seed': 42, 'unit': 'UTC match day'},
        'probability_basis': 'CONDITIONAL_ON_NO_FINAL_TIE', 'settlement': 'INCLUDING_OVERTIME_TIES_VOID',
        'limitations': ['Small retrospective paired comparison, not fresh holdout or prospective validation.',
            'Historical PBP availability is assumed; archived observation receipts are absent.',
            'Not directly comparable to the main long-history NFL artifact.',
            'Bootstrap omits full cross-day dependence and model-selection uncertainty.'],
        'production_changed': False, 'active': False, 'promotion_authorized': False}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'metrics': {name: {key: value[key] for key in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for name, value in report['metrics'].items()}, 'paired_difference': report['paired_difference']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['bundle', 'capture', 'development', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); run(args.bundle, args.capture, args.development, args.output)
