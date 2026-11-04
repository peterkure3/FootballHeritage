"""Frozen NFL candidate selection and season/week validation outside serving."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.gridiron_efficiency import build_efficiency_features
from models.nfl_history import sha
from models.sport_features import HISTORY_FEATURES
from models.training_resources import training_threads
from models.validation import probability_metrics

CLASSES = ['away_win', 'home_win']
CONFIGURATIONS = ['history', 'efficiency', 'compact', 'compact_efficiency']


def feature_sets(features):
    compact = pd.DataFrame({'elo_diff': features.elo_diff,
        'margin_diff': features.home_margin-features.away_margin,
        'win_rate_diff': features.home_win_rate-features.away_win_rate,
        'rest_diff': features.home_rest-features.away_rest,
        'load_diff': features.home_recent_load-features.away_recent_load})
    extra = pd.DataFrame({name+'_diff': features['home_'+name]-features['away_'+name]
                         for name in ['offense_epa', 'defense_epa', 'offense_success', 'defense_success']})
    extra['pbp_coverage'] = np.minimum(features.home_pbp_games, features.away_pbp_games)
    return {'history': features[HISTORY_FEATURES], 'efficiency': features,
            'compact': compact, 'compact_efficiency': pd.concat([compact, extra], axis=1)}


def season_splits(games, year):
    masks = {'train': games.season.lt(year-1),
        'tune': games.season.eq(year-1) & games.week.le(9),
        'calibration': games.season.eq(year-1) & games.week.gt(9), 'test': games.season.eq(year)}
    if any(not mask.any() for mask in masks.values()):
        raise ValueError('Empty NFL season partition')
    boundaries = {name: games.loc[masks[next_name], 'date'].min().normalize()
        for name, next_name in [('train', 'tune'), ('tune', 'calibration'), ('calibration', 'test')]}
    splits = {}; excluded = {}
    for name, mask in masks.items():
        tied = games.result.eq('draw') & mask
        unavailable = (games.result_available_at.ge(boundaries[name]) & mask) if name in boundaries else pd.Series(False, index=games.index)
        splits[name] = np.flatnonzero(mask & ~tied & ~unavailable)
        excluded[name] = {'ties': int(tied.sum()), 'unavailable_labels': int(unavailable.sum())}
    return splits, excluded


def fit_expert(X, y, splits):
    train, tune, calibration = [splits[name] for name in ['train', 'tune', 'calibration']]
    if any(len(index)<30 or len(np.unique(y[index]))!=2 for index in [train, tune, calibration]):
        raise ValueError('Insufficient NFL seasonal fitting coverage')
    # Reuse train-only scaling across C values; do not share it across folds.
    scaler = StandardScaler().fit(X.iloc[train])
    a, b = scaler.transform(X.iloc[train]), scaler.transform(X.iloc[tune])
    scores = {}
    for C in [.01, .1, 1.]:
        model = LogisticRegression(C=C, max_iter=1000, random_state=42).fit(a, y[train])
        scores[str(C)] = probability_metrics(y[tune], model.predict_proba(b), CLASSES)['log_loss']
    selected = min(scores, key=scores.get)
    development = np.r_[train, tune]
    scaler = StandardScaler().fit(X.iloc[development])
    learner = LogisticRegression(C=float(selected), max_iter=1000, random_state=42).fit(
        scaler.transform(X.iloc[development]), y[development])
    fitted = make_pipeline(scaler, learner)
    calibrated = CalibratedClassifierCV(FrozenEstimator(fitted), method='sigmoid')
    calibrated.fit(X.iloc[calibration], y[calibration])
    return calibrated, {'C': selected, 'tuning_log_loss': scores}


def load_data(directory):
    report = json.loads((directory/'report.json').read_text())
    for file, key in [('dataset.parquet', 'dataset_sha256'), ('features.parquet', 'features_sha256')]:
        if sha(directory/file) != report[key]:
            raise ValueError('Prepared NFL artifact changed')
    return pd.read_parquet(directory/'dataset.parquet'), pd.read_parquet(directory/'features.parquet'), report


def choose(aggregate, folds):
    baseline = aggregate['history']; eligible = []
    for name in CONFIGURATIONS[1:]:
        value = aggregate[name]
        if (value['log_loss'] < baseline['log_loss'] and value['accuracy'] >= baseline['accuracy']
                and value['brier_score'] <= baseline['brier_score']
                and sum(f['metrics'][name]['log_loss'] < f['metrics']['history']['log_loss'] for f in folds) >= 4):
            eligible.append(name)
    return min(eligible, key=lambda name: aggregate[name]['log_loss']) if eligible else 'history'


def train(directory, output):
    games, features, data_report = load_data(directory); matrices = feature_sets(features)
    y = games.result.map({'away_win': 0, 'home_win': 1}).fillna(-1).to_numpy(dtype=int)
    rows = []; folds = []
    with training_threads(2):
        for year in range(2020, 2026):
            splits, excluded = season_splits(games, year)
            fold = {'year': year, 'metrics': {}, 'selection': {}, 'fit_seconds': {}, 'excluded': excluded,
                'partitions': {name: {'samples': len(index), 'start': games.iloc[index].date.min().isoformat(),
                    'end': games.iloc[index].date.max().isoformat()} for name, index in splits.items()}}
            for name in CONFIGURATIONS:
                print(f'NFL season {year}: {name}', flush=True)
                started = perf_counter(); model, selection = fit_expert(matrices[name], y, splits)
                fold['fit_seconds'][name] = perf_counter()-started
                p = model.predict_proba(matrices[name].iloc[splits['test']])
                fold['metrics'][name] = probability_metrics(y[splits['test']], p, CLASSES)
                fold['selection'][name] = selection
                for index, values in zip(splits['test'], p):
                    game = games.iloc[index]
                    rows.append({'row': int(index), 'season': year, 'week': int(game.week), 'model': name,
                        'id': str(game.provider_event_id), 'actual': int(y[index]),
                        **dict(zip(CLASSES, values.tolist()))})
            folds.append(fold)
    predictions = pd.DataFrame(rows); aggregate = {}
    for name in CONFIGURATIONS:
        arm = predictions[predictions.model.eq(name)]
        aggregate[name] = probability_metrics(arm.actual.to_numpy(), arm[CLASSES].to_numpy(), CLASSES)
    selected = choose(aggregate, folds)
    output.mkdir(parents=True, exist_ok=False)
    predictions.to_csv(output/'development_predictions.csv', index=False)
    final_splits, excluded = season_splits(games, 2026)
    models = {}
    with training_threads(2):
        for name in dict.fromkeys(['history', selected]):
            model, selection = fit_expert(matrices[name], y, final_splits)
            path = output/f'{name}.pkl'; joblib.dump(model, path)
            models[name] = {'file': path.name, 'sha256': sha(path), 'features': list(matrices[name].columns),
                            'selection': selection, 'bytes': path.stat().st_size}
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'selected': selected, 'classes': CLASSES,
        'data_directory': str(directory), 'data_report_sha256': sha(directory/'report.json'),
        'aggregate': aggregate, 'folds': folds, 'models': models, 'heldout_season': 2026,
        'final_split_exclusions': excluded, 'feature_contract': 'nfl-season-differences-v1',
        'availability_policy': data_report['availability_policy'],
        'source_sha256': {file: sha(Path(file)) for file in ['models/nfl_season_validation.py',
            'models/nfl_history.py', 'models/gridiron_efficiency.py', 'models/sport_features.py']},
        'limitations': ['2026 excluded from this selection; prior broad aggregate reports included some 2026 data.',
            'Historical observation/revision timing is assumed, not verified.',
            'Conditional winner probabilities exclude final ties; no profitability claim.'],
        'production_changed': False, 'active': False, 'promotion_authorized': False}
    (output/'selection.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'selected': selected, 'development': {name: {key: value[key] for key in
        ['samples', 'accuracy', 'log_loss', 'brier_score']} for name, value in aggregate.items()}}, indent=2))
    return report


def paired_week_intervals(labels, baseline, candidate, games):
    one_hot = np.eye(2)[labels]
    differences = {'accuracy': (candidate.argmax(axis=1)==labels).astype(float)-(baseline.argmax(axis=1)==labels),
        'log_loss': -np.log(np.clip(candidate[np.arange(len(labels)), labels], 1e-15, 1))
                    +np.log(np.clip(baseline[np.arange(len(labels)), labels], 1e-15, 1)),
        'brier_score': ((candidate-one_hot)**2).sum(axis=1)-((baseline-one_hot)**2).sum(axis=1)}
    keys = list(zip(games.season, games.week)); unique = sorted(set(keys))
    blocks = [np.array([i for i, key in enumerate(keys) if key==value]) for value in unique]
    rng = np.random.default_rng(42); samples = {name: [] for name in differences}
    for _ in range(2000):
        draw = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        for name, values in differences.items():
            samples[name].append(float(values[draw].mean()))
    return {name: {'mean': float(values.mean()), 'season_week_bootstrap_95_percent_interval':
        np.quantile(samples[name], [.025, .975]).tolist()} for name, values in differences.items()}


def validate(bundle):
    selection_path = bundle/'selection.json'; selection = json.loads(selection_path.read_text())
    for file, digest in selection['source_sha256'].items():
        if sha(Path(file)) != digest:
            raise ValueError('Frozen NFL selection/feature code changed')
    directory = Path(selection['data_directory'])
    if sha(directory/'report.json') != selection['data_report_sha256']:
        raise ValueError('Frozen NFL dataset report changed')
    games, features, data_report = load_data(directory); matrices = feature_sets(features)
    y = games.result.map({'away_win': 0, 'home_win': 1}).fillna(-1).to_numpy(dtype=int)
    test = np.flatnonzero(games.season.eq(2026) & games.result.ne('draw'))
    if len(test)<30 or not games.iloc[test].pbp_complete.all():
        raise ValueError('Insufficient or incomplete 2026 holdout inputs')
    selected = selection['selected']; probabilities = {}; timings = {}; models = {}
    with training_threads(2):
        for name in dict.fromkeys(['history', selected]):
            metadata = selection['models'][name]
            if sha(bundle/metadata['file']) != metadata['sha256']:
                raise ValueError('Frozen NFL candidate changed')
            model = joblib.load(bundle/metadata['file']); models[name] = model
            X = matrices[name].iloc[test]; probabilities[name] = model.predict_proba(X)
            elapsed = []
            for _ in range(10):
                started = perf_counter(); model.predict_proba(X); elapsed.append(perf_counter()-started)
            timings[name] = {'median_prediction_seconds': median(elapsed), 'batch_samples': len(test),
                             'features': len(X.columns), 'artifact_bytes': metadata['bytes']}
    baseline = probabilities['history']; candidate = probabilities[selected]
    metrics = {name: probability_metrics(y[test], p, CLASSES) for name, p in probabilities.items()}
    sensitivity_games = games.copy()
    sensitivity_games['result_available_at'] = pd.concat([games.result_available_at,
        games.date.dt.normalize()+pd.Timedelta(days=7)], axis=1).max(axis=1)
    cache = directory/'cache'; cache_metadata = json.loads((cache/'manifest.json').read_text())
    expected = {name: digest for name, digest in data_report['source_sha256'].items() if name.startswith('nfl_pbp_')}
    if (sha(cache/'team_games.parquet') != cache_metadata['aggregate_sha256']
            or cache_metadata['raw_sha256'] != expected):
        raise ValueError('Frozen NFL efficiency aggregate cache changed')
    delayed = feature_sets(build_efficiency_features(sensitivity_games, pd.read_parquet(cache/'team_games.parquet')))
    with training_threads(2):
        stress = {name: probability_metrics(y[test], models[name].predict_proba(delayed[name].iloc[test]), CLASSES)
                  for name in probabilities}
    output = bundle/'validation'; output.mkdir(exist_ok=False)
    frame = games.iloc[test][['provider_event_id', 'season', 'week', 'season_type', 'date', 'result']].copy()
    for name, p in probabilities.items():
        for i, label in enumerate(CLASSES):
            frame[name+'_'+label] = p[:, i]
    frame.to_csv(output/'predictions.csv', index=False)
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'selection_sha256': sha(selection_path),
        'selected': selected, 'metrics': metrics, 'paired_differences': paired_week_intervals(
            y[test], baseline, candidate, games.iloc[test]), 'weeks': int(games.iloc[test].week.nunique()),
        'by_week': {str(week): {name: probability_metrics(y[test][games.iloc[test].week.eq(week).to_numpy()],
            p[games.iloc[test].week.eq(week).to_numpy()], CLASSES) for name, p in probabilities.items()}
            for week in sorted(games.iloc[test].week.unique())},
        'by_season_type': {str(kind): {name: probability_metrics(y[test][games.iloc[test].season_type.eq(kind).to_numpy()],
            p[games.iloc[test].season_type.eq(kind).to_numpy()], CLASSES) for name, p in probabilities.items()}
            for kind in games.iloc[test].season_type.unique()},
        'benchmark': timings, 'seven_day_availability_fixed_model_stress': stress,
        'limitations': selection['limitations']+['Partial-season retrospective holdout; weekly bootstrap omits model-selection uncertainty.',
            'Seven-day stress changes inputs of frozen two-day models, without refitting or retuning.'],
        'production_changed': False, 'active': False, 'promotion_authorized': False}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'selected': selected, 'holdout': {name: {key: value[key] for key in
        ['samples', 'accuracy', 'log_loss', 'brier_score']} for name, value in metrics.items()},
        'paired_differences': report['paired_differences'], 'benchmark': timings}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['train', 'validate'])
    parser.add_argument('--data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode=='train':
        if args.data is None:
            parser.error('train requires --data')
        train(args.data, args.output)
    else:
        validate(args.output)
