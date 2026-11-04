from copy import deepcopy
import unittest

import numpy as np
import pandas as pd

from models.sport_data import canonical_games
from scripts.evaluate_nba_freshness_shadow import assess
from scripts.record_nba_freshness_shadow import observed_features
from scripts.reconcile_nba_research_results import normalize_event


class NbaFreshnessTests(unittest.TestCase):
    def event(self):
        return {'id': 'espn1', 'date': '2026-11-01T22:00:00Z', 'season': {'type': 2},
                'status': {'period': 5, 'type': {'completed': True}}, 'competitions': [{'competitors': [
                    {'homeAway': 'away', 'team': {'displayName': 'Charlotte Hornets'}, 'score': '99'},
                    {'homeAway': 'home', 'team': {'displayName': 'Washington Wizards'}, 'score': '103'}]}]}

    def trial(self):
        return {'status': 'prospective_NBA_freshness_shadow', 'classes': ['away_win', 'home_win'],
                'policy': {'settlement': 'INCLUDING_OVERTIME', 'minimum_settled': 200, 'minimum_match_days': 20},
                'fixtures': [{'id': 'bdl1', 'home': 'Washington Wizards', 'away': 'Charlotte Hornets',
                    'kickoff': '2026-11-01T22:00:00Z', 'generated_at': '2026-10-31T21:00:00Z',
                    'feature_cutoff': '2026-10-31T20:59:00Z',
                    'probabilities': {'stale': [.6, .4], 'fresh': [.3, .7]}}]}

    def test_uses_only_observed_past_scores(self):
        rows = [{'date': '2026-11-01T01:00:00Z', 'result_available_at': '2026-11-01T06:00:00Z',
                 'league': 'basketball_nba', 'home_team': 'Washington Wizards', 'away_team': 'Charlotte Hornets',
                 'home_score': 103, 'away_score': 99, 'completed': True}]
        history = canonical_games(rows, 'basketball')
        game = {'date': '2026-11-01T22:00:00Z', 'league': 'basketball_nba',
                'home_team': 'Washington Wizards', 'away_team': 'Charlotte Hornets'}
        before = observed_features(history, game, pd.Timestamp('2026-11-01T05:00:00Z'))
        after = observed_features(history, game, pd.Timestamp('2026-11-01T07:00:00Z'))
        self.assertEqual(before.home_games.iloc[0], 0)
        self.assertEqual(after.home_games.iloc[0], 1)
        changed = history.copy(); changed['home_score'] = 250
        np.testing.assert_array_equal(before, observed_features(changed, game, pd.Timestamp('2026-11-01T05:00:00Z')))
        for cutoff in ['2026-11-01T07:00:00', game['date']]:
            with self.assertRaises(ValueError):
                observed_features(history, game, pd.Timestamp(cutoff))

    def test_independent_finals_require_valid_period_and_score(self):
        self.assertEqual(normalize_event(self.event())['home_score'], 103)
        for changes in [{'period': 3}, {'type': {'completed': False}}]:
            event = self.event(); event['status'].update(changes)
            self.assertIsNone(normalize_event(event))
        event = self.event(); event['competitions'][0]['competitors'][0]['score'] = '103'
        with self.assertRaisesRegex(ValueError, 'Tied'):
            normalize_event(event)

    def test_overtime_settlement_and_paired_metrics(self):
        report = assess(self.trial(), [self.event()], pd.Timestamp('2026-11-02T07:00:00Z'))
        self.assertEqual(report['settled'], 1)
        self.assertEqual(report['metrics']['stale']['accuracy'], 0)
        self.assertEqual(report['metrics']['fresh']['accuracy'], 1)
        self.assertFalse(report['promotion_authorized'])

    def test_exact_fixture_matching_and_duplicate_results(self):
        now = pd.Timestamp('2026-11-02T07:00:00Z')
        event = self.event(); event['date'] = '2026-11-01T23:00:00Z'
        self.assertEqual(assess(self.trial(), [event], now)['settled'], 0)
        event = self.event(); event['status']['type']['completed'] = False
        self.assertEqual(assess(self.trial(), [event], now)['settled'], 0)
        self.assertEqual(assess(self.trial(), [self.event(), self.event()], now)['fixtures'][0]['status'], 'ambiguous_result')

    def test_invalid_frozen_forecasts_fail(self):
        now = pd.Timestamp('2026-11-02T07:00:00Z')
        for field, value in [('generated_at', '2026-11-01T22:01:00Z'),
                             ('feature_cutoff', '2026-11-01T21:00:00Z')]:
            trial = self.trial(); trial['fixtures'][0][field] = value
            with self.assertRaises(ValueError):
                assess(trial, [], now)
        trial = self.trial(); trial['fixtures'].append(deepcopy(trial['fixtures'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            assess(trial, [], now)
        trial = self.trial(); trial['fixtures'][0]['probabilities']['fresh'] = [float('nan'), .7]
        with self.assertRaisesRegex(ValueError, 'probabilities'):
            assess(trial, [], now)
