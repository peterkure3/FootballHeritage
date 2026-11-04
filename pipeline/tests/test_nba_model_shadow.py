import unittest

import numpy as np
import pandas as pd

from models.nba_accuracy_research import inactivity_features
from models.sport_data import canonical_games
from models.sport_features import build_features, HISTORY_FEATURES
from scripts.record_nba_model_shadow import replay_states, forecast_features
from scripts.evaluate_nba_freshness_shadow import assess


class NbaModelShadowTests(unittest.TestCase):
    def history(self):
        return canonical_games([{'date': date, 'result_available_at': (pd.Timestamp(date)+pd.Timedelta(days=1)).isoformat(),
            'league': 'basketball_nba', 'home_team': 'Washington Wizards', 'away_team': 'Charlotte Hornets',
            'home_score': 103+i, 'away_score': 99, 'completed': True}
            for i, date in enumerate(['2020-01-01T00:00:00Z', '2020-01-03T00:00:00Z',
                                     '2020-04-15T00:00:00Z', '2020-04-17T00:00:00Z'])], 'basketball')

    def test_replay_matches_training_feature_definitions(self):
        history = self.history()
        reference = {'baseline': build_features(history, 'basketball')[HISTORY_FEATURES],
                     'candidate': inactivity_features(history)}
        for i, game in enumerate(history.to_dict('records')):
            states, _ = replay_states(history, game['date'])
            inputs = forecast_features(states, game)
            for arm in reference:
                np.testing.assert_allclose(inputs[arm][HISTORY_FEATURES].iloc[0], reference[arm].iloc[i], rtol=0, atol=1e-12)

    def test_unobserved_results_and_future_scores_do_not_enter_forecasts(self):
        history = self.history(); history.loc[0, 'result_available_at'] = pd.Timestamp('2020-01-10T00:00:00Z')
        game = history.iloc[1].to_dict(); cutoff = pd.Timestamp('2020-01-02T12:00:00Z')
        states, effective = replay_states(history, cutoff)
        self.assertEqual(effective, 0)
        original = forecast_features(states, game)
        history['home_score'] = 999
        altered, _ = replay_states(history, cutoff)
        for arm, features in forecast_features(altered, game).items():
            np.testing.assert_array_equal(original[arm], features)

    def test_forecast_order_does_not_mutate_shared_states(self):
        history = self.history(); states, _ = replay_states(history, pd.Timestamp('2020-04-18T12:00:00Z'))
        game = history.iloc[-1].to_dict(); game['date'] = pd.Timestamp('2020-05-01T00:00:00Z')
        original = forecast_features(states, game)
        later = {**game, 'date': pd.Timestamp('2021-05-01T00:00:00Z')}
        forecast_features(states, later)
        for arm, features in forecast_features(states, game).items():
            np.testing.assert_array_equal(original[arm], features)

    def test_model_trial_uses_its_own_arm_metrics(self):
        trial = {'status': 'prospective_NBA_model_shadow', 'classes': ['away_win', 'home_win'],
            'policy': {'settlement': 'INCLUDING_OVERTIME', 'minimum_settled': 200, 'minimum_match_days': 20},
            'fixtures': [{'id': 'bdl1', 'home': 'Washington Wizards', 'away': 'Charlotte Hornets',
                'kickoff': '2026-11-01T22:00:00Z', 'generated_at': '2026-10-31T21:00:00Z',
                'feature_cutoff': '2026-10-31T20:59:00Z', 'probabilities': {'baseline': [.6, .4], 'candidate': [.3, .7]}}]}
        event = {'id': 'espn1', 'date': '2026-11-01T22:00:00Z', 'season': {'type': 2},
            'status': {'period': 4, 'type': {'completed': True}}, 'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'displayName': 'Washington Wizards'}, 'score': '103'},
                {'homeAway': 'away', 'team': {'displayName': 'Charlotte Hornets'}, 'score': '99'}]}]}
        report = assess(trial, [event], pd.Timestamp('2026-11-02T07:00:00Z'))
        self.assertEqual(report['metrics']['candidate']['accuracy'], 1)
        self.assertEqual(report['metrics']['baseline']['accuracy'], 0)
        self.assertNotIn('fresh', report['metrics'])
        self.assertFalse(report['promotion_authorized'])
