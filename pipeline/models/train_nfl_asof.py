"""Refit the selected NFL recipe using available history, without publishing it."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.nfl_history import sha
from models.nfl_season_validation import load_data, CLASSES
from models.sport_features import HISTORY_FEATURES, FEATURES, SCHEMA_VERSION
from models.sport_model import SportWinnerModel
from models.training_resources import training_threads


def training_splits(games, as_of, calibration_from):
    as_of = pd.Timestamp(as_of)
    if as_of.tzinfo is None:
        raise ValueError('Training cutoff requires timezone')
    available = games.date.lt(as_of) & games.result_available_at.le(as_of)
    decisive = games.result.isin(CLASSES)
    calibration = available & decisive & games.season.ge(calibration_from)
    if not calibration.any():
        raise ValueError('No available NFL calibration labels')
    boundary = games.loc[calibration, 'date'].min().normalize()
    before = games.season.lt(calibration_from)
    train = available & decisive & before & games.result_available_at.lt(boundary)
    return {'train': np.flatnonzero(train), 'calibration': np.flatnonzero(calibration)}, {
        'ties_retained_in_history': int((available & games.result.eq('draw')).sum()),
        'unavailable_rows': int((~available).sum()),
        'late_training_labels_purged': int((available & decisive & before & games.result_available_at.ge(boundary)).sum())}


def run(source, output, calibration_from=None):
    started = perf_counter(); as_of = pd.Timestamp.now(tz='UTC')
    selection = json.loads((source/'selection.json').read_text())
    if selection['selected'] != 'history':
        raise ValueError('This refitter requires the selected standard NFL history recipe')
    for file, digest in selection['source_sha256'].items():
        if sha(Path(file)) != digest:
            raise ValueError('Validated NFL recipe implementation changed')
    directory = Path(selection['data_directory'])
    if sha(directory/'report.json') != selection['data_report_sha256']:
        raise ValueError('Validated NFL snapshot changed')
    games, features, data = load_data(directory)
    if pd.Timestamp(data['created_at']) > as_of:
        raise ValueError('NFL snapshot was not available at training time')
    if calibration_from is None:
        calibration_from = int(games.loc[games.result_available_at.le(as_of), 'season'].max())
    splits, exclusions = training_splits(games, as_of, calibration_from)
    y = games.result.map({'away_win': 0, 'home_win': 1}).fillna(-1).to_numpy(dtype=int)
    if any(len(index)<60 or len(np.unique(y[index]))!=2 for index in splits.values()):
        raise ValueError('Training and calibration require 60 decisive games and both outcomes')
    C = float(selection['models']['history']['selection']['C'])
    X = features[HISTORY_FEATURES]
    with training_threads(2):
        base = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000, random_state=42))
        base.fit(X.iloc[splits['train']], y[splits['train']])
        history = CalibratedClassifierCV(FrozenEstimator(base), method='sigmoid')
        history.fit(X.iloc[splits['calibration']], y[splits['calibration']])
        model = SportWinnerModel(history)
        inputs = X.copy()
        inputs['fair_home_prob'] = .5; inputs['fair_away_prob'] = .5
        inputs['overround'] = 0.; inputs['odds_missing'] = 1.
        inputs = inputs[FEATURES]
        probe = inputs.iloc[np.r_[splits['train'][:3], splits['calibration'][-3:]]]
        probabilities = model.predict_proba(probe)
    if not np.isfinite(probabilities).all() or (probabilities<0).any() or not np.allclose(probabilities.sum(axis=1), 1):
        raise ValueError('Invalid refitted NFL probabilities')
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump(model, output/'model.pkl')
    with training_threads(2):
        np.testing.assert_allclose(joblib.load(output/'model.pkl').predict_proba(probe), probabilities, rtol=0, atol=1e-12)
    metadata = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'as_of': as_of.isoformat(),
        'status': 'trained_candidate', 'sport': 'nfl', 'active': False, 'production_changed': False,
        'model_version': 'nfl-history-asof-1', 'feature_schema_version': SCHEMA_VERSION,
        'features': FEATURES, 'history_features': HISTORY_FEATURES, 'classes': CLASSES,
        'C': C, 'calibration': 'sigmoid on separately reserved recent-season labels',
        'calibration_from_season': calibration_from, 'partitions': {
            name: {'samples': len(index), 'start': games.iloc[index].date.min().isoformat(),
                   'end': games.iloc[index].date.max().isoformat(),
                   'latest_label_available_at': games.iloc[index].result_available_at.max().isoformat()}
            for name, index in splits.items()}, 'exclusions': exclusions,
        'training_snapshot_games': len(games), 'data_directory': str(directory),
        'dataset_sha256': data['dataset_sha256'], 'features_sha256': data['features_sha256'],
        'recipe_selection_sha256': sha(source/'selection.json'), 'recipe_directory': str(source),
        'model_sha256': sha(output/'model.pkl'), 'model_bytes': (output/'model.pkl').stat().st_size,
        'training_seconds': perf_counter()-started, 'restore_probability_check_tolerance': 1e-12,
        'settlement_rule': 'INCLUDING_OVERTIME_TIES_VOID', 'probability_basis': 'CONDITIONAL_ON_NO_FINAL_TIE',
        'test': None, 'independent_test_status': 'not_yet_evaluated_after_latest_data_refit',
        'limitations': ['2026 labels are now calibration data; earlier holdout metrics do not evaluate this refit.',
            data['availability_policy'], 'No odds inputs, automatic promotion or profitability claim.'],
        'training_code_sha256': sha(Path(__file__))}
    (output/'metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False))
    print(json.dumps({'directory': str(output), 'model_sha256': metadata['model_sha256'],
        'C': C, 'partitions': metadata['partitions'], 'exclusions': exclusions,
        'training_seconds': metadata['training_seconds'], 'active': False,
        'independent_test_status': metadata['independent_test_status']}, indent=2))
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calibration-from-season', type=int)
    args = parser.parse_args(); run(args.recipe, args.output, args.calibration_from_season)
