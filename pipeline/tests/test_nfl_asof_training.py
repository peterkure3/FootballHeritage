import unittest

import pandas as pd

from models.train_nfl_asof import training_splits


class NflAsOfTrainingTests(unittest.TestCase):
    def test_calibration_is_separate_and_unavailable_labels_never_fit(self):
        games = pd.DataFrame([
            {'season': 2025, 'date': '2025-12-01T00:00:00Z', 'result_available_at': '2025-12-03T00:00:00Z', 'result': 'home_win'},
            {'season': 2025, 'date': '2025-12-02T00:00:00Z', 'result_available_at': '2026-09-05T00:00:00Z', 'result': 'away_win'},
            {'season': 2026, 'date': '2026-09-01T00:00:00Z', 'result_available_at': '2026-09-03T00:00:00Z', 'result': 'home_win'},
            {'season': 2026, 'date': '2026-09-02T00:00:00Z', 'result_available_at': '2026-09-04T00:00:00Z', 'result': 'draw'},
            {'season': 2026, 'date': '2026-11-01T00:00:00Z', 'result_available_at': '2026-11-03T00:00:00Z', 'result': 'away_win'}])
        for column in ['date', 'result_available_at']:
            games[column] = pd.to_datetime(games[column], utc=True)
        splits, excluded = training_splits(games, pd.Timestamp('2026-11-01T12:00:00Z'), 2026)
        self.assertEqual(splits['train'].tolist(), [0])
        self.assertEqual(splits['calibration'].tolist(), [2])
        self.assertEqual(excluded['ties_retained_in_history'], 1)
        self.assertEqual(excluded['late_training_labels_purged'], 1)
        self.assertEqual(excluded['unavailable_rows'], 1)
        with self.assertRaisesRegex(ValueError, 'timezone'):
            training_splits(games, pd.Timestamp('2026-11-01'), 2026)
