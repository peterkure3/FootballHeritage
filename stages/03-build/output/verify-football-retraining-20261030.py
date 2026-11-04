"""Replay the isolated football candidates; never alter serving artifacts."""
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from models.features import build_feature_frame
from models.training_resources import training_threads
from models.validation import chronological_split, probability_metrics

STORE = ROOT / 'pipeline/models/model_store'
RUNS = {
    'global': (STORE / 'candidates/20261030T200921372082Z', 'metrics_v2.1.0.json', 'model_v2.1.0.pkl'),
    'premier_league': (STORE / 'league_models/20261030T204820117364Z/PL', 'metrics.json', 'model.pkl'),
}
report = {}
for name, (directory, metrics_file, model_file) in RUNS.items():
    metrics = json.loads((directory / metrics_file).read_text(encoding='utf-8'))
    dataset = directory / 'dataset.parquet'
    checksum = hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert checksum == metrics.get('dataset_sha256', metrics.get('dataset_parquet_sha256'))
    X, fixtures = build_feature_frame(pd.read_parquet(dataset))
    splits = chronological_split(fixtures.date)
    classes = metrics['classes']
    y = np.array([classes.index(value) for value in fixtures.result])
    with training_threads(2):
        probabilities = joblib.load(directory / model_file).predict_proba(X.iloc[splits['test']])
    actual = probability_metrics(y[splits['test']], probabilities, classes)
    for score in ['accuracy', 'log_loss', 'brier_score']:
        np.testing.assert_allclose(actual[score], metrics['test'][score], atol=1e-12, rtol=0)
    development = np.concatenate([splits['train'], splits['tune']])
    counts = np.bincount(y[development], minlength=3) + 1
    baseline = probability_metrics(y[splits['test']], np.tile(counts / counts.sum(), (len(splits['test']), 1)), classes)
    report[name] = {
        'directory': str(directory.relative_to(ROOT)),
        'completed_matches': len(fixtures), 'dataset_sha256': checksum,
        'artifact_replay_passed': True,
        'test': {key: actual[key] for key in ['samples', 'accuracy', 'log_loss', 'brier_score']},
        'development_prior': {key: baseline[key] for key in ['samples', 'accuracy', 'log_loss', 'brier_score']},
        'selected': metrics.get('selected'),
        'market_comparison': metrics.get('market_comparison'),
        'model_sha256': hashlib.sha256((directory / model_file).read_bytes()).hexdigest(),
    }
target = Path(__file__).with_name('football-retraining-20261030-verification.json')
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
for name, result in report.items():
    print(name, json.dumps({key: result[key] for key in ['completed_matches', 'artifact_replay_passed', 'test', 'development_prior']}))
