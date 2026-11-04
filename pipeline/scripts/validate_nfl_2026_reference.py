"""Compare the refreshed NFL candidate with the frozen reference on common targets."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter

import joblib
import numpy as np
import pandas as pd

from models.nfl_history import sha
from models.nfl_season_validation import load_data, feature_sets, paired_week_intervals, CLASSES
from models.sport_data import canonical_games
from models.sport_features import build_features
from models.train_sports import supervised_splits
from models.training_resources import training_threads
from models.validation import probability_metrics


def reference_history(original, updated):
    keys = ['home_key', 'away_key', 'home_score', 'away_score', 'date', 'neutral_site', 'league']
    old = original.set_index('provider_event_id'); new = updated.set_index('provider_event_id')
    if not old.index.is_unique or not new.index.is_unique:
        raise ValueError('Duplicate NFL native ID')
    common = old.index.intersection(new.index)
    for key in keys:
        if not np.array_equal(old.loc[common, key].to_numpy(), new.loc[common, key].to_numpy()):
            raise ValueError('NFL reference/history fixture disagreement')
    appended = updated[~updated.provider_event_id.isin(old.index)]
    if not appended.date.gt(original.date.max()).all():
        raise ValueError('Missing older reference fixture requires explicit audit')
    combined = canonical_games(original.to_dict('records')+appended.to_dict('records'), 'nfl')
    if combined.iloc[:len(original)].provider_event_id.tolist() != original.provider_event_id.tolist():
        raise ValueError('Reference historical state order changed')
    return combined


def run(reference, candidate):
    metadata = json.loads((reference/'metrics.json').read_text())
    selection = json.loads((candidate/'selection.json').read_text())
    for file, key in [('model.pkl', 'model_sha256'), ('dataset.parquet', 'dataset_sha256')]:
        if sha(reference/file) != metadata[key]:
            raise ValueError('Frozen NFL reference artifact changed')
    for file, digest in selection['source_sha256'].items():
        if sha(Path(file)) != digest:
            raise ValueError('Frozen NFL candidate implementation changed')
    data = Path(selection['data_directory'])
    if sha(data/'report.json') != selection['data_report_sha256']:
        raise ValueError('Frozen NFL prepared data changed')
    games, features, _ = load_data(data); name = selection['selected']; saved = selection['models'][name]
    if sha(candidate/saved['file']) != saved['sha256']:
        raise ValueError('Frozen selected NFL model changed')
    original = pd.read_parquet(reference/'dataset.parquet')
    combined = reference_history(original, games)
    original_splits, _ = supervised_splits(original, 'nfl')
    old_y = original.result.map({'away_win': 0, 'home_win': 1}).fillna(-1).to_numpy(dtype=int)
    test = np.flatnonzero(games.season.eq(2026) & games.result.ne('draw'))
    y = games.iloc[test].result.map({'away_win': 0, 'home_win': 1}).to_numpy(dtype=int)
    with training_threads(2):
        old_model = joblib.load(reference/'model.pkl'); new_model = joblib.load(candidate/saved['file'])
        original_X = build_features(original, 'nfl')
        replay = probability_metrics(old_y[original_splits['test']], old_model.predict_proba(original_X.iloc[original_splits['test']]), CLASSES)
        for key in ['accuracy', 'log_loss', 'brier_score']:
            if not np.isclose(replay[key], metadata['test'][key], rtol=0, atol=1e-12):
                raise ValueError('Frozen reference metric replay failed')
        extended_X = build_features(combined, 'nfl')
        np.testing.assert_allclose(extended_X.iloc[:len(original)], original_X, rtol=0, atol=1e-12)
        target_ids = games.iloc[test].provider_event_id.tolist()
        lookup = pd.Series(np.arange(len(combined)), index=combined.provider_event_id)
        target = lookup.loc[target_ids].to_numpy()
        reference_X = extended_X.iloc[target]
        candidate_X = feature_sets(features)[name].iloc[test]
        baseline = old_model.predict_proba(reference_X); refreshed = new_model.predict_proba(candidate_X)
        timings = {}
        for label, model, X, path in [('reference', old_model, reference_X, reference/'model.pkl'),
                                      ('refreshed', new_model, candidate_X, candidate/saved['file'])]:
            elapsed = []
            for _ in range(10):
                started = perf_counter(); model.predict_proba(X); elapsed.append(perf_counter()-started)
            timings[label] = {'median_prediction_seconds': median(elapsed), 'artifact_bytes': path.stat().st_size,
                              'batch_samples': len(test)}
        delayed = combined.copy()
        delayed['result_available_at'] = pd.concat([combined.result_available_at,
            combined.date.dt.normalize()+pd.Timedelta(days=7)], axis=1).max(axis=1)
        delayed_baseline = old_model.predict_proba(build_features(delayed, 'nfl').iloc[target])
    validation = json.loads((candidate/'validation/report.json').read_text())
    if (games.iloc[test].provider_event_id.astype(str).tolist()
            != pd.read_csv(candidate/'validation/predictions.csv').provider_event_id.astype(str).tolist()):
        raise ValueError('2026 validation target membership changed')
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'selected': name,
        'reference_model_sha256': metadata['model_sha256'], 'candidate_model_sha256': saved['sha256'],
        'selection_sha256': sha(candidate/'selection.json'), 'reference_original_test_replayed': True,
        'historical_reference_games_preserved': len(original), 'later_games_appended': len(combined)-len(original),
        'metrics': {'reference': probability_metrics(y, baseline, CLASSES),
                    'refreshed': probability_metrics(y, refreshed, CLASSES)},
        'paired_differences': paired_week_intervals(y, baseline, refreshed, games.iloc[test]),
        'seven_day_fixed_model_sensitivity': {'reference': probability_metrics(y, delayed_baseline, CLASSES),
            'refreshed': validation['seven_day_availability_fixed_model_stress'][name]},
        'benchmark': timings, 'probability_basis': 'CONDITIONAL_ON_NO_FINAL_TIE',
        'limitations': ['Retrospective partial-season comparison; earlier broad reference reports included 2026.',
            'Training/calibration freshness and dataset window both differ; not an isolated causal effect of more history.',
            'Historical observation/revision timing assumed; weekly bootstrap omits model-selection uncertainty.'],
        'production_changed': False, 'active': False, 'promotion_authorized': False}
    frame = games.iloc[test][['provider_event_id', 'season', 'week', 'date', 'result']].copy()
    for label, p in [('reference', baseline), ('refreshed', refreshed)]:
        for i, cls in enumerate(CLASSES):
            frame[label+'_'+cls] = p[:, i]
    output = candidate/'reference_validation'; output.mkdir(exist_ok=False)
    frame.to_csv(output/'predictions.csv', index=False)
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'metrics': {key: {m: value[m] for m in ['samples', 'accuracy', 'log_loss', 'brier_score']}
        for key, value in report['metrics'].items()}, 'paired_differences': report['paired_differences'],
        'benchmark': timings}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args(); run(args.reference, args.candidate)
