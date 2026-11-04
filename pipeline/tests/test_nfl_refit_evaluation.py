from copy import deepcopy
import unittest

import numpy as np
import pandas as pd

from scripts.evaluate_nfl_refit import evaluation_splits, scheduled_fixture, season_intervals
from scripts.assess_nfl_refit import assess


class NflRefitEvaluationTests(unittest.TestCase):
    def test_forward_targets_are_not_training_or_calibration_labels(self):
        rows = [{'season': season, 'week': week, 'date': date, 'result_available_at': available, 'result': result}
            for season, week, date, available, result in [
                (2019, 1, '2019-09-01', '2019-09-03', 'home_win'),
                (2019, 2, '2019-09-08', '2020-10-31', 'away_win'),
                (2020, 1, '2020-09-10', '2020-09-12', 'home_win'),
                (2020, 8, '2020-10-30', '2020-11-01', 'away_win'),
                (2020, 8, '2020-11-01T18:00:00', '2020-11-03', 'home_win'),
                (2020, 8, '2020-11-01T21:00:00', '2020-11-03', 'draw'),
                (2020, 9, '2020-11-08', '2020-11-10', 'away_win')]]
        games = pd.DataFrame(rows)
        for name in ['date', 'result_available_at']:
            games[name] = pd.to_datetime(games[name], utc=True, format='mixed')
        cutoff, splits, test, _ = evaluation_splits(games, 2020)
        self.assertEqual(splits['train'].tolist(), [0])
        self.assertEqual(splits['calibration'].tolist(), [2, 3])
        self.assertEqual(test.tolist(), [4, 6])
        self.assertTrue(games.iloc[test].date.gt(cutoff).all())

    def test_dst_schedule_and_incomplete_score_exclusion(self):
        row = {'game_id': 'x', 'game_type': 'REG', 'gameday': '2026-11-01', 'gametime': '09:30',
            'home_team': 'LA', 'away_team': 'KC', 'location': 'Neutral', 'home_score': np.nan, 'away_score': np.nan}
        self.assertEqual(scheduled_fixture(row)['kickoff'], '2026-11-01T14:30:00+00:00')
        self.assertIsNone(scheduled_fixture({**row, 'home_score': 0}))

    def test_season_bootstrap_retains_correlated_clusters(self):
        y = np.zeros(6, dtype=int); p = np.array([[0., 1.]]*3+[[1., 0.]]*3)
        result = season_intervals(y, p, 1-p, np.array([2020]*3+[2021]*3))
        self.assertEqual(result['accuracy']['season_block_bootstrap_95_percent_interval'], [-1., 1.])

    def trial(self):
        return {'status': 'prospective_NFL_refit_evaluation', 'classes': ['away_win', 'home_win'],
            'settlement': 'INCLUDING_OVERTIME_TIES_VOID', 'trained_at': '2026-11-01T06:15:00Z',
            'fixtures': [{'id': 'x', 'home': 'Atlanta Falcons', 'away': 'Buffalo Bills',
                'kickoff': '2026-11-01T18:00:00Z', 'generated_at': '2026-11-01T07:00:00Z',
                'feature_cutoff': '2026-11-01T00:00:00Z', 'probabilities': [.3, .7]}]}

    def event(self, h=24, a=17):
        return {'id': 'espn-x', 'date': '2026-11-01T18:00:00Z', 'season': {'type': 2},
            'status': {'period': 5, 'type': {'completed': True}}, 'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'displayName': 'Atlanta Falcons'}, 'score': str(h)},
                {'homeAway': 'away', 'team': {'displayName': 'Buffalo Bills'}, 'score': str(a)}]}]}

    def test_final_overtime_tie_is_void_and_not_in_accuracy_denominator(self):
        now = pd.Timestamp('2026-11-02T00:00:00Z')
        result = assess(self.trial(), [self.event()], now)
        self.assertEqual(result['settled'], 1); self.assertEqual(result['metrics']['accuracy'], 1)
        result = assess(self.trial(), [self.event(21, 21)], now)
        self.assertEqual(result['void_ties'], 1); self.assertEqual(result['settled'], 0)
        self.assertIsNone(result['metrics'])

    def test_pending_wrong_time_and_postkickoff_forecasts_do_not_score(self):
        now = pd.Timestamp('2026-11-02T00:00:00Z'); event = self.event()
        event['status']['type']['completed'] = False
        self.assertEqual(assess(self.trial(), [event], now)['settled'], 0)
        event = self.event(); event['date'] = '2026-11-01T19:00:00Z'
        self.assertEqual(assess(self.trial(), [event], now)['settled'], 0)
        trial = deepcopy(self.trial()); trial['fixtures'][0]['generated_at'] = '2026-11-01T18:01:00Z'
        with self.assertRaises(ValueError):
            assess(trial, [], now)
