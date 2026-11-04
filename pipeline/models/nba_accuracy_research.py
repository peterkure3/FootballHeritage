"""Bounded NBA training comparison on development folds; never publishes models."""
import argparse
import hashlib
import heapq
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.sport_features import HISTORY_FEATURES, SportState, build_features
from models.training_resources import training_threads
from models.validation import forward_folds, probability_metrics

CONFIGURATIONS = ['baseline', 'recent_730', 'gradient']


class InactivityState(SportState):
    """Fixed 90-day inactivity policy; not a claim to know roster changes."""
    def vector(self, game):
        for side in ['home', 'away']:
            key = game['league'], game[side+'_team'].casefold().strip()
            history = self.games[key]
            if history and pd.Timestamp(game['date']) - history[-1][0] >= pd.Timedelta(days=90):
                self.elo[key] = 1500. + .5 * (self.elo[key] - 1500.)
                history.clear()
        return super().vector(game)


def inactivity_features(games: pd.DataFrame) -> pd.DataFrame:
    state = InactivityState('basketball'); pending = []; sequence = 0; rows = []
    for day, block in games.groupby(games.date.dt.normalize(), sort=True):
        while pending and pending[0][0] <= day:
            _, _, game = heapq.heappop(pending)
            state.update(game)
        for game in block.to_dict('records'):
            rows.append(state.vector(game))
            available = max(game['result_available_at'], day + pd.Timedelta(days=1))
            heapq.heappush(pending, (available, sequence, game)); sequence += 1
    return pd.DataFrame(rows)[HISTORY_FEATURES]


def recency_weights(dates: pd.Series) -> np.ndarray:
    days = (dates.max() - dates).dt.total_seconds().to_numpy() / 86400
    weights = np.exp2(-days / 730.)
    return weights / weights.mean()


def partition(games: pd.DataFrame, development: np.ndarray, test: np.ndarray):
    days = np.sort(games.iloc[development].date.dt.normalize().unique())
    calibration_start = pd.Timestamp(days[int(len(days) * .8)])
    test_start = games.iloc[test].date.min().normalize()
    dates = games.iloc[development].date.dt.normalize()
    available = games.iloc[development].result_available_at
    train = development[(dates.lt(calibration_start) & available.lt(calibration_start)).to_numpy()]
    calibration = development[(dates.ge(calibration_start) & available.lt(test_start)).to_numpy()]
    if not len(train) or not len(calibration):
        raise ValueError('Insufficient causal calibration partition')
    return train, calibration


def fit(name, X, y, dates, train, calibration):
    if name not in CONFIGURATIONS + ['inactivity_reset']:
        raise ValueError('Unknown NBA experiment')
    if name == 'gradient':
        model = HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15,
            min_samples_leaf=30, l2_regularization=10, early_stopping=False, random_state=42)
    else:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=1000, random_state=42))
    options = {'logisticregression__sample_weight': recency_weights(dates.iloc[train])} if name == 'recent_730' else {}
    model.fit(X.iloc[train], y[train], **options)
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method='sigmoid')
    calibrated.fit(X.iloc[calibration], y[calibration])
    return calibrated


def run(bundle: Path, output: Path, inactivity=False):
    metadata = json.loads((bundle/'metrics.json').read_text())
    source = bundle/'dataset.parquet'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != metadata['dataset_sha256']:
        raise ValueError('Frozen NBA dataset changed')
    boundary = pd.Timestamp(metadata['splits']['test']['start'])
    games = pd.read_parquet(source)
    if set(games.league) != {'basketball_nba'}:
        raise ValueError('NBA-only dataset required')
    games = games[games.date.lt(boundary)].reset_index(drop=True)
    classes = ['away_win', 'home_win']
    if not games.result.isin(classes).all():
        raise ValueError('Unexpected NBA outcome')
    X = build_features(games, 'basketball')[HISTORY_FEATURES]
    configurations = ['baseline', 'inactivity_reset'] if inactivity else CONFIGURATIONS
    matrices = {'baseline': X, 'inactivity_reset': inactivity_features(games)} if inactivity else {name: X for name in configurations}
    y = pd.Categorical(games.result, categories=classes).codes
    rows = []; folds = []
    for fold, (development, test) in enumerate(forward_folds(games.date, 3)):
        train, calibration = partition(games, development, test)
        summary = {'fold': fold, 'train_samples': len(train), 'calibration_samples': len(calibration),
            'test_samples': len(test), 'train_end': games.iloc[train].date.max().isoformat(),
            'calibration_start': games.iloc[calibration].date.min().isoformat(),
            'test_start': games.iloc[test].date.min().isoformat(), 'models': {}}
        for name in configurations:
            print(f'NBA fold {fold+1}/3: {name}', flush=True)
            with training_threads(2):
                features = matrices[name]
                model = fit(name, features, y, games.date, train, calibration)
                p = model.predict_proba(features.iloc[test])
            summary['models'][name] = probability_metrics(y[test], p, classes)
            for index, probability in zip(test, p):
                game = games.iloc[index]
                rows.append({'row': int(index), 'fold': fold, 'model': name, 'date': game.date.isoformat(),
                    'home': game.home_team, 'away': game.away_team, 'actual': int(y[index]),
                    **dict(zip(classes, probability.tolist()))})
        folds.append(summary)
    predictions = pd.DataFrame(rows); aggregate = {}
    for name in configurations:
        selected = predictions[predictions.model.eq(name)]
        aggregate[name] = probability_metrics(selected.actual.to_numpy(), selected[classes].to_numpy(), classes)
    baseline = aggregate['baseline']
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'dataset_sha256': digest,
        'excluded_final_test_start': boundary.isoformat(), 'development_samples': len(games),
        'configurations': configurations, 'classes': classes, 'features': HISTORY_FEATURES,
        'folds': folds, 'aggregate': aggregate,
        'promising': {name: aggregate[name]['accuracy'] > baseline['accuracy']
            and aggregate[name]['log_loss'] < baseline['log_loss']
            and aggregate[name]['brier_score'] < baseline['brier_score']
            and sum(f['models'][name]['accuracy'] > f['models']['baseline']['accuracy'] for f in folds) >= 2
            for name in configurations[1:]},
        'limitations': ['Development selection evidence only; no fresh holdout or prospective accuracy.',
            'Uneven source coverage and inherited historical result-availability assumptions.',
            'No odds or profitability evaluation.'], 'production_changed': False, 'active': False}
    output.mkdir(parents=True, exist_ok=False)
    predictions.to_csv(output/'predictions.csv', index=False)
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'aggregate': {name: {k: value[k] for k in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for name, value in aggregate.items()}, 'promising': report['promising']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inactivity', action='store_true')
    args = parser.parse_args(); run(args.bundle, args.output, args.inactivity)
