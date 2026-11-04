"""Evaluate NFL refitting through historical replicas and freeze prospective probes."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.gridiron_sources import normalize_nfl, NFL_NAMES, NFL_RENAMES
from models.nfl_history import sha, verified_sources
from models.nfl_season_validation import load_data, season_splits, fit_expert, CLASSES
from models.sport_features import HISTORY_FEATURES, FEATURES, live_features
from models.sport_model import SportWinnerModel
from models.train_nfl_asof import training_splits
from models.training_resources import training_threads
from models.validation import probability_metrics


def inputs(features):
    frame = features[HISTORY_FEATURES].copy()
    frame['fair_home_prob'] = .5; frame['fair_away_prob'] = .5
    frame['overround'] = 0.; frame['odds_missing'] = 1.
    return frame[FEATURES]


def cutoff_for_season(games, year):
    days = games.loc[games.season.eq(year) & games.week.eq(8), 'date'].dt.normalize().unique()
    sundays = sorted(day for day in days if pd.Timestamp(day).dayofweek==6)
    if not sundays:
        raise ValueError('No Sunday kickoff date for NFL week 8')
    return pd.Timestamp(sundays[0])+pd.Timedelta(hours=6, minutes=15)


def evaluation_splits(games, year):
    cutoff = cutoff_for_season(games, year)
    splits, excluded = training_splits(games, cutoff, year)
    test = np.flatnonzero(games.season.eq(year) & games.date.gt(cutoff) & games.result.isin(CLASSES))
    if not len(test) or (set(test) & (set(splits['train'])|set(splits['calibration']))):
        raise ValueError('Invalid NFL forward evaluation targets')
    return cutoff, splits, test, excluded


def season_intervals(labels, baseline, candidate, seasons):
    one_hot = np.eye(2)[labels]
    differences = {'accuracy': (candidate.argmax(axis=1)==labels).astype(float)-(baseline.argmax(axis=1)==labels),
        'log_loss': -np.log(np.clip(candidate[np.arange(len(labels)), labels], 1e-15, 1))
                    +np.log(np.clip(baseline[np.arange(len(labels)), labels], 1e-15, 1)),
        'brier_score': ((candidate-one_hot)**2).sum(axis=1)-((baseline-one_hot)**2).sum(axis=1)}
    blocks = [np.flatnonzero(seasons==year) for year in sorted(set(seasons))]
    rng = np.random.default_rng(42); samples = {key: [] for key in differences}
    for _ in range(2000):
        draw = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        for key, values in differences.items():
            samples[key].append(float(values[draw].mean()))
    return {key: {'mean': float(values.mean()), 'season_block_bootstrap_95_percent_interval':
        np.quantile(samples[key], [.025, .975]).tolist()} for key, values in differences.items()}


def scheduled_fixture(row):
    if row['game_type'] not in {'REG', 'WC', 'DIV', 'CON', 'SB'} or pd.isna(row.get('gametime')):
        return None
    if pd.notna(row.get('home_score')) or pd.notna(row.get('away_score')):
        return None
    if row.get('location') not in {'Home', 'Neutral'}:
        return None
    h, a = [NFL_RENAMES.get(row[side+'_team'], row[side+'_team']) for side in ['home', 'away']]
    if h not in NFL_NAMES or a not in NFL_NAMES or h==a:
        return None
    kickoff = pd.Timestamp(f"{row['gameday']} {row['gametime']}").tz_localize('America/New_York').tz_convert('UTC')
    return {'id': str(row['game_id']), 'home': NFL_NAMES[h], 'away': NFL_NAMES[a], 'kickoff': kickoff.isoformat(),
            'neutral_site': row['location']=='Neutral'}


def run(model_dir, capture, output):
    metadata = json.loads((model_dir/'metadata.json').read_text())
    if sha(model_dir/'model.pkl') != metadata['model_sha256']:
        raise ValueError('Trained NFL model checksum mismatch')
    games, features, data_report = load_data(Path(metadata['data_directory']))
    if data_report['dataset_sha256'] != metadata['dataset_sha256']:
        raise ValueError('Trained NFL input snapshot mismatch')
    verified_sources(capture)
    raw = pd.read_csv(capture/'nfl_games.csv', low_memory=False)
    results = normalize_nfl(raw, str((capture/'nfl_games.csv').resolve()))
    new_results = results[results.date.gt(pd.Timestamp(metadata['created_at']))
                         & ~results.provider_event_id.isin(set(games.provider_event_id))]
    # Once unseen outcomes exist, require an explicit paired/frozen-forecast assessment.
    if len(new_results):
        raise ValueError('New independent outcomes are available; assess them against frozen predictions before rerunning replica research')
    output.mkdir(parents=True, exist_ok=False); (output/'replicas').mkdir()
    X = features[HISTORY_FEATURES]; runtime_X = inputs(features)
    y = games.result.map({'away_win': 0, 'home_win': 1}).fillna(-1).to_numpy(dtype=int)
    names = ['refit', 'preseason', 'training_prior', 'season_prior']; records = []; folds = []
    with training_threads(2):
        for year in range(2020, 2026):
            cutoff, splits, test, excluded = evaluation_splits(games, year)
            historical, selection = fit_expert(X, y, season_splits(games, year)[0])
            train, calibration = splits['train'], splits['calibration']
            if min(len(train), len(calibration))<60 or any(len(np.unique(y[ix]))!=2 for ix in [train, calibration]):
                raise ValueError('Insufficient historical refit partitions')
            base = make_pipeline(StandardScaler(), LogisticRegression(C=float(selection['C']), max_iter=1000, random_state=42))
            base.fit(X.iloc[train], y[train])
            calibrated = CalibratedClassifierCV(FrozenEstimator(base), method='sigmoid')
            calibrated.fit(X.iloc[calibration], y[calibration])
            model = SportWinnerModel(calibrated)
            p = {'refit': model.predict_proba(runtime_X.iloc[test]), 'preseason': historical.predict_proba(X.iloc[test])}
            for name, index in [('training_prior', train), ('season_prior', calibration)]:
                counts = np.bincount(y[index], minlength=2)
                p[name] = np.tile(counts/counts.sum(), (len(test), 1))
            metrics = {name: probability_metrics(y[test], values, CLASSES) for name, values in p.items()}
            path = output/'replicas'/f'{year}.pkl'; joblib.dump(model, path)
            np.testing.assert_allclose(joblib.load(path).predict_proba(runtime_X.iloc[test]), p['refit'], rtol=0, atol=1e-12)
            folds.append({'season': year, 'as_of': cutoff.isoformat(), 'C': selection['C'],
                'training_samples': len(train), 'calibration_samples': len(calibration), 'test_samples': len(test),
                'training_label_end': games.iloc[train].result_available_at.max().isoformat(),
                'calibration_label_end': games.iloc[calibration].result_available_at.max().isoformat(),
                'first_test_kickoff': games.iloc[test].date.min().isoformat(), 'excluded': excluded,
                'model_sha256': sha(path), 'metrics': metrics})
            for position, index in enumerate(test):
                row = {'id': str(games.iloc[index].provider_event_id), 'row': int(index), 'season': year,
                    'week': int(games.iloc[index].week), 'actual': int(y[index])}
                for name, values in p.items():
                    row.update({name+'_'+label: float(values[position, i]) for i, label in enumerate(CLASSES)})
                records.append(row)
            print(f'NFL {year}: refit {metrics["refit"]["accuracy"]:.3%}, preseason {metrics["preseason"]["accuracy"]:.3%}, n={len(test)}', flush=True)
    predictions = pd.DataFrame(records); labels = predictions.actual.to_numpy()
    probabilities = {name: predictions[[name+'_'+label for label in CLASSES]].to_numpy() for name in names}
    aggregate = {name: probability_metrics(labels, values, CLASSES) for name, values in probabilities.items()}
    predictions.to_csv(output/'historical_predictions.csv', index=False)
    model = joblib.load(model_dir/'model.pkl'); generated = pd.Timestamp.now(tz='UTC'); upcoming = []; seen = set()
    with training_threads(2):
        for raw_row in raw.to_dict('records'):
            fixture = scheduled_fixture(raw_row)
            if fixture is None or not generated < pd.Timestamp(fixture['kickoff']) <= generated+pd.Timedelta(days=7):
                continue
            if fixture['id'] in seen:
                raise ValueError('Duplicate upcoming NFL provider ID')
            seen.add(fixture['id'])
            frame = live_features(games, 'nfl', {'date': fixture['kickoff'], 'league': 'americanfootball_nfl',
                'home_team': fixture['home'], 'away_team': fixture['away'], 'neutral_site': fixture['neutral_site']}, as_of=generated)
            values = model.predict_proba(frame)[0]
            recorded = pd.Timestamp.now(tz='UTC')
            if recorded >= pd.Timestamp(fixture['kickoff']):
                continue
            if not np.isfinite(values).all() or (values<0).any() or not np.isclose(values.sum(), 1):
                raise ValueError('Invalid prospective NFL probabilities')
            upcoming.append({**fixture, 'generated_at': recorded.isoformat(), 'feature_cutoff': generated.normalize().isoformat(),
                'probabilities': values.tolist(), 'features': frame.iloc[0].to_dict()})
    trial = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': 'prospective_NFL_refit_evaluation',
        'model_sha256': metadata['model_sha256'], 'model_directory': str(model_dir), 'trained_at': metadata['created_at'],
        'dataset_sha256': metadata['dataset_sha256'], 'classes': CLASSES, 'fixtures': upcoming,
        'schedule_source': {'directory': str(capture), 'file': 'nfl_games.csv', 'sha256': sha(capture/'nfl_games.csv')},
        'settlement': 'INCLUDING_OVERTIME_TIES_VOID', 'production_changed': False}
    (output/'trial.json').write_text(json.dumps(trial, indent=2, allow_nan=False))
    (output/'trial.sha256').write_text(sha(output/'trial.json')+'\n')
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'actual_model_sha256': metadata['model_sha256'],
        'actual_model_independent_results': {'samples': 0, 'metrics': None, 'status': 'awaiting_post_training_results'},
        'historical_procedure_evaluation': {'aggregate': aggregate, 'folds': folds,
            'refit_minus_preseason': season_intervals(labels, probabilities['preseason'], probabilities['refit'], predictions.season.to_numpy())},
        'prospective_forecasts_frozen': len(upcoming), 'historical_prediction_sha256': sha(output/'historical_predictions.csv'),
        'source_code_sha256': sha(Path(__file__)), 'production_changed': False,
        'limitations': ['Historical procedure replicas do not independently evaluate the current artifact.',
            'Previously inspected historical seasons and feature-family choices imply selection uncertainty.',
            'Historical availability/revision timing assumed; features update causally while replica weights stay fixed.',
            'Six season bootstrap clusters; no guarantee of future accuracy or profitability.']}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'historical': {name: {key: values[key] for key in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for name, values in aggregate.items()}, 'refit_minus_preseason': report['historical_procedure_evaluation']['refit_minus_preseason'],
        'actual_model_independent_samples': 0, 'prospective_forecasts_frozen': len(upcoming)}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['model', 'capture', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); run(args.model, args.capture, args.output)
