from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from models.nfl_history import cached_pbp, verified_sources
from models.nfl_season_validation import season_splits, fit_expert, choose, paired_week_intervals, CONFIGURATIONS
from models.train_sports import select_expert
from models.training_resources import training_threads


class NflSeasonValidationTests(unittest.TestCase):
    def test_season_and_week_boundaries_purge_unavailable_labels_and_ties(self):
        rows = []
        for season in [2018, 2019, 2020]:
            for week in [1, 9, 10, 18]:
                date = pd.Timestamp(f'{season}-09-01', tz='UTC')+pd.Timedelta(days=7*(week-1))
                rows.append({'season': season, 'week': week, 'date': date,
                             'result_available_at': date+pd.Timedelta(days=2), 'result': 'home_win'})
        games = pd.DataFrame(rows)
        games.loc[0, 'result'] = 'draw'
        games.loc[5, 'result_available_at'] = games.loc[6, 'date']+pd.Timedelta(days=1)
        splits, excluded = season_splits(games, 2020)
        self.assertNotIn(0, splits['train']); self.assertNotIn(5, splits['tune'])
        self.assertEqual(excluded['tune']['unavailable_labels'], 1)
        for name in ['train', 'tune', 'calibration']:
            self.assertTrue(games.iloc[splits[name]].season.lt(2020).all())
        self.assertTrue(games.iloc[splits['tune']].week.le(9).all())
        self.assertTrue(games.iloc[splits['calibration']].week.gt(9).all())

    def test_scaler_reuse_matches_existing_estimator_and_excludes_calibration(self):
        rng = np.random.default_rng(42); X = pd.DataFrame(rng.normal(size=(240, 3)), columns=list('abc'))
        y = np.tile([0, 1], 120)
        splits = {'train': np.arange(120), 'tune': np.arange(120, 180), 'calibration': np.arange(180, 240)}
        X.iloc[180:] += 100
        with training_threads(2):
            actual, selection = fit_expert(X, y, splits)
            reference, old = select_expert(X, y, splits, list(X.columns), np.ones(len(X), dtype=bool))
            self.assertEqual(selection['C'], old['selected_C'])
            np.testing.assert_allclose(actual.predict_proba(X), reference.predict_proba(X), rtol=0, atol=1e-12)
        scaler = actual.estimator.estimator.named_steps['standardscaler']
        np.testing.assert_allclose(scaler.mean_, X.iloc[:180].mean().to_numpy(), rtol=0, atol=1e-12)

    def test_selection_does_not_accept_worse_accuracy_or_inconsistent_seasons(self):
        baseline = {'accuracy': .6, 'log_loss': .65, 'brier_score': .45}
        aggregate = {name: deepcopy(baseline) for name in CONFIGURATIONS}
        aggregate['compact'] = {'accuracy': .61, 'log_loss': .64, 'brier_score': .44}
        folds = [{'metrics': deepcopy(aggregate)} for _ in range(6)]
        self.assertEqual(choose(aggregate, folds), 'compact')
        aggregate['compact']['accuracy'] = .59
        self.assertEqual(choose(aggregate, folds), 'history')
        aggregate['compact']['accuracy'] = .61
        for fold in folds[:3]:
            fold['metrics']['compact']['log_loss'] = .66
        self.assertEqual(choose(aggregate, folds), 'history')

    def test_week_bootstrap_preserves_correlated_week_blocks(self):
        labels = np.zeros(6, dtype=int)
        baseline = np.array([[0., 1.]]*3+[[1., 0.]]*3)
        candidate = 1-baseline
        games = pd.DataFrame({'season': [2026]*6, 'week': [1]*3+[2]*3})
        report = paired_week_intervals(labels, baseline, candidate, games)
        interval = report['accuracy']['season_week_bootstrap_95_percent_interval']
        self.assertEqual(interval, [-1., 1.])

    def test_cache_reuse_invalidation_and_modified_cache_detection(self):
        stats = pd.DataFrame({'game_id': ['g'], 'posteam': ['A'], 'defteam': ['B'], 'source_file': ['raw'],
                              'plays': [10], 'epa_per_play': [.1], 'success_rate': [.5]})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); cache = root/'cache'; hashes = {'nfl_pbp_2020.parquet': 'a'}
            with patch('models.nfl_history.summarize_pbp', return_value=stats) as build:
                first, cold = cached_pbp(root, cache, hashes)
                second, warm = cached_pbp(root, cache, hashes)
                pd.testing.assert_frame_equal(first, second)
                self.assertFalse(cold['cache_hit']); self.assertTrue(warm['cache_hit'])
                self.assertEqual(build.call_count, 1)
                cached_pbp(root, cache, {'nfl_pbp_2020.parquet': 'changed'})
                self.assertEqual(build.call_count, 2)
            (cache/'team_games.parquet').write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                cached_pbp(root, cache, {'nfl_pbp_2020.parquet': 'changed'})

    def test_source_hashes_are_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); raw = root/'nfl_games.csv'; raw.write_text('initial')
            (root/'manifest.json').write_text(json.dumps({'captures': {'nfl_games.csv': {
                'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}}}))
            verified_sources(root)
            raw.write_text('modified')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verified_sources(root)
