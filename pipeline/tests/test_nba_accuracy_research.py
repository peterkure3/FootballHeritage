import unittest

import numpy as np
import pandas as pd

from models.nba_accuracy_research import fit, partition, recency_weights, inactivity_features
from models.sport_data import canonical_games
from models.sport_features import HISTORY_FEATURES, build_features


class NbaAccuracyResearchTests(unittest.TestCase):
    def games(self, dates):
        return canonical_games([{'date': date, 'result_available_at': (pd.Timestamp(date) + pd.Timedelta(days=1)).isoformat(),
            'home_team': 'A', 'away_team': 'B', 'league': 'basketball_nba',
            'home_score': 110, 'away_score': 100, 'completed': True} for date in dates], 'basketball')

    def test_inactivity_reset_does_not_use_same_day_or_future_scores(self):
        games = self.games(['2020-01-01T00:00:00Z', '2020-04-15T00:00:00Z'])
        extra = games.iloc[[-1]].copy()
        extra['date'] += pd.Timedelta(hours=12)
        extra['away_team'] = 'C'; extra['away_key'] = 'c'
        games = pd.concat([games, extra], ignore_index=True)
        original = inactivity_features(games)
        self.assertEqual(original.home_games.iloc[1], 0)
        self.assertEqual(original.home_games.iloc[2], 0)
        altered = games.copy(); altered.loc[1:, 'home_score'] = 300
        np.testing.assert_array_equal(original, inactivity_features(altered))

    def test_active_teams_preserve_original_features(self):
        games = self.games(['2020-01-01T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-05T00:00:00Z'])
        np.testing.assert_array_equal(inactivity_features(games), build_features(games, 'basketball')[HISTORY_FEATURES])

    def test_delayed_labels_are_purged_at_each_boundary(self):
        dates = pd.date_range('2020-01-01', periods=30, tz='UTC')
        games = pd.DataFrame({'date': dates, 'result_available_at': dates + pd.Timedelta(days=1)})
        games.loc[0, 'result_available_at'] = dates[25]
        games.loc[17, 'result_available_at'] = dates[25]
        train, calibration = partition(games, np.arange(20), np.arange(20, 30))
        self.assertNotIn(0, train)
        self.assertNotIn(17, calibration)
        self.assertTrue((games.iloc[train].result_available_at < games.iloc[calibration].date.min()).all())
        self.assertTrue((games.iloc[calibration].result_available_at < games.iloc[20].date).all())
        self.assertFalse(set(train) & set(calibration))
        self.assertFalse((set(train) | set(calibration)) & set(range(20, 30)))

    def test_fixed_recency_weights_are_date_translation_invariant(self):
        dates = pd.Series(pd.to_datetime(['2020-01-01', '2021-12-31'], utc=True))
        weights = recency_weights(dates)
        self.assertAlmostEqual(weights.mean(), 1)
        self.assertAlmostEqual(weights[1] / weights[0], 2)
        np.testing.assert_allclose(weights, recency_weights(dates + pd.Timedelta(days=2000)))

    def test_calibration_features_do_not_fit_preprocessing(self):
        X = pd.DataFrame({'x': np.r_[np.arange(20), np.arange(10) + 10000]})
        y = np.tile([0, 1], 15)
        dates = pd.Series(pd.date_range('2020-01-01', periods=30, tz='UTC'))
        for name in ['baseline', 'recent_730']:
            model = fit(name, X, y, dates, np.arange(20), np.arange(20, 30))
            scaler = model.estimator.estimator.named_steps['standardscaler']
            self.assertAlmostEqual(scaler.mean_[0], 9.5)
