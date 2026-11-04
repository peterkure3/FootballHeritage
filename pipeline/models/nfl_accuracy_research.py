"""Paired NFL efficiency ablation using nested chronological development folds."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models.gridiron_sources import summarize_pbp
from models.gridiron_efficiency import build_efficiency_features, EFFICIENCY_FEATURES
from models.sport_features import HISTORY_FEATURES
from models.train_sports import select_expert
from models.training_resources import training_threads
from models.validation import forward_folds, probability_metrics


def nested_partitions(games, development, test):
    days = np.sort(games.iloc[development].date.dt.normalize().unique())
    tune_start, calibration_start = [pd.Timestamp(days[int(len(days)*f)]) for f in [.6, .8]]
    test_start = games.iloc[test].date.min().normalize()
    block = games.iloc[development]; dates = block.date.dt.normalize()
    target = block.result.isin(['away_win', 'home_win'])
    masks = [dates.lt(tune_start) & block.result_available_at.lt(tune_start),
        dates.ge(tune_start) & dates.lt(calibration_start) & block.result_available_at.lt(calibration_start),
        dates.ge(calibration_start) & block.result_available_at.lt(test_start)]
    splits = {name: development[(mask & target).to_numpy()]
              for name, mask in zip(['train', 'tune', 'calibration'], masks)}
    splits['test'] = test[games.iloc[test].result.isin(['away_win', 'home_win']).to_numpy()]
    return splits


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(bundle: Path, capture: Path, output: Path):
    metadata = json.loads((bundle/'metrics.json').read_text())
    if sha(bundle/'dataset.parquet') != metadata['dataset_sha256']:
        raise ValueError('Frozen NFL research dataset changed')
    manifest = json.loads((capture/'manifest.json').read_text()); raw_hashes = {}
    for path in sorted(capture.glob('nfl_pbp_*.parquet')):
        expected = manifest['captures'][path.name]['sha256']
        if sha(path) != expected:
            raise ValueError('Captured nflfastR source changed')
        raw_hashes[path.name] = expected
    if len(raw_hashes) != 3:
        raise ValueError('Expected the frozen three-season nflfastR corpus')
    games = pd.read_parquet(bundle/'dataset.parquet')
    stats = summarize_pbp(capture)
    X = build_efficiency_features(games, stats)
    np.testing.assert_allclose(X, pd.read_parquet(bundle/'features.parquet'), rtol=0, atol=1e-12)
    boundary = pd.Timestamp(metadata['splits']['test']['start'])
    keep = games.date.lt(boundary)
    games = games[keep].reset_index(drop=True); X = X.loc[keep].reset_index(drop=True)
    if set(games.league) != {'americanfootball_nfl'}:
        raise ValueError('NFL-only snapshot required')
    classes = ['away_win', 'home_win']
    y = np.array([classes.index(value) if value in classes else -1 for value in games.result])
    configurations = {'history': HISTORY_FEATURES, 'efficiency': EFFICIENCY_FEATURES}
    folds = []; rows = []
    for fold, (development, test) in enumerate(forward_folds(games.date, 3)):
        splits = nested_partitions(games, development, test)
        summary = {'fold': fold, 'models': {}, 'selection': {}, 'partitions': {
            name: {'samples': len(index), 'start': games.iloc[index].date.min().isoformat(),
                   'end': games.iloc[index].date.max().isoformat()} for name, index in splits.items()}}
        for name, columns in configurations.items():
            print(f'NFL fold {fold+1}/3: {name}', flush=True)
            with training_threads(2):
                model, selection = select_expert(X, y, splits, columns, np.ones(len(games), dtype=bool))
                if model is None:
                    raise ValueError('Insufficient causal NFL fold coverage')
                p = model.predict_proba(X.iloc[splits['test']][columns])
            summary['selection'][name] = selection
            summary['models'][name] = probability_metrics(y[splits['test']], p, classes)
            for index, probabilities in zip(splits['test'], p):
                game = games.iloc[index]
                rows.append({'row': int(index), 'fold': fold, 'model': name, 'date': game.date.isoformat(),
                    'id': str(game.provider_event_id), 'home': game.home_team, 'away': game.away_team,
                    'actual': int(y[index]), **dict(zip(classes, probabilities.tolist()))})
        folds.append(summary)
    predictions = pd.DataFrame(rows); aggregate = {}
    for name in configurations:
        arm = predictions[predictions.model.eq(name)]
        aggregate[name] = probability_metrics(arm.actual.to_numpy(), arm[classes].to_numpy(), classes)
    baseline = aggregate['history']; extra = aggregate['efficiency']
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': 'development_efficiency_ablation',
        'dataset_sha256': metadata['dataset_sha256'], 'saved_features_sha256': sha(bundle/'features.parquet'),
        'raw_pbp_sha256': raw_hashes, 'excluded_test_start': boundary.isoformat(), 'development_games': len(games),
        'raw_feature_replay_tolerance': 1e-12, 'classes': classes, 'configurations': configurations,
        'folds': folds, 'aggregate': aggregate,
        'promising': extra['accuracy'] > baseline['accuracy'] and extra['log_loss'] < baseline['log_loss']
            and extra['brier_score'] < baseline['brier_score']
            and sum(f['models']['efficiency']['accuracy'] > f['models']['history']['accuracy'] for f in folds) >= 2,
        'settlement': 'INCLUDING_OVERTIME_TIES_VOID', 'probability_basis': 'CONDITIONAL_ON_NO_FINAL_TIE',
        'source_sha256': {name: sha(Path(name)) for name in ['models/nfl_accuracy_research.py',
            'models/gridiron_efficiency.py', 'models/gridiron_sources.py', 'models/train_sports.py']},
        'limitations': ['Development selection evidence, not fresh confirmation or a production-model comparison.',
            'Historical postgame/PBP availability delay is assumed, without archived observation receipts.',
            'Only three recent seasons; no historical market odds or profitability evaluation.'],
        'production_changed': False, 'active': False}
    output.mkdir(parents=True, exist_ok=False)
    predictions.to_csv(output/'predictions.csv', index=False)
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'aggregate': {name: {key: value[key] for key in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for name, value in aggregate.items()}, 'promising': report['promising']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.bundle, args.capture, args.output)
