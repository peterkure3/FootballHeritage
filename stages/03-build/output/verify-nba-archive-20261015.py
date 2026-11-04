"""Behavioral checks for archive normalization and research model routing."""
import json
from pathlib import Path
import runpy
import unittest

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
module = runpy.run_path(str(HERE / 'train-nba-archive-20261015.py'))
normalize = module['normalize_archive']
price = module['decimal_price']
raw = pd.read_csv(module['ARCHIVE'] / 'nba_adv_complete.csv')
pair = raw.loc[raw.idGame.eq(raw.iloc[0].idGame)].copy()


class ArchiveChecks(unittest.TestCase):
    def test_american_conversion(self):
        self.assertAlmostEqual(price(150), 2.5)
        self.assertAlmostEqual(price(-200), 1.5)
        self.assertEqual(price(100), 2.)
        self.assertEqual(price(-100), 2.)
        self.assertTrue(np.isnan(price(np.nan)))
        for invalid in [0, 99, -99, float('inf')]:
            with self.assertRaises(ValueError):
                price(invalid)

    def test_pair_has_correct_home_scores_and_no_invented_quote_time(self):
        game = normalize(pair).iloc[0]
        self.assertEqual(game.home_team, 'Los Angeles Lakers')
        self.assertEqual(game.home_score, 93)
        self.assertEqual(game.away_score, 95)
        self.assertAlmostEqual(game.home_win, 2.9)
        self.assertEqual(game.result, 'away_win')
        self.assertIsNone(game.odds_observed_at)
        self.assertEqual(game.date_precision, 'DAY')
        self.assertEqual(game.result_available_at - game.date, pd.Timedelta(days=2))

    def test_conflicting_pairs_are_excluded(self):
        changed = pair.copy()
        changed.loc[changed.locationGame.eq('A'), 'ptsTeam.own'] += 1
        self.assertTrue(normalize(changed).empty)

    def test_unpaired_game_is_excluded(self):
        self.assertTrue(normalize(pair.iloc[:1]).empty)

    def test_missing_prices_are_preserved_for_history_only_routing(self):
        changed = pair.copy()
        changed[['teamML', 'oppML']] = np.nan
        game = normalize(changed).iloc[0]
        self.assertTrue(pd.isna(game.home_win) and pd.isna(game.away_win))

    def test_fresh_saved_model_market_and_history_routing(self):
        evidence = json.loads((HERE / 'nba-archive-training-20261015.json').read_text())
        directory = Path(evidence['directory'])
        self.assertIn('research', directory.parts)
        self.assertTrue(evidence['research_only'])
        self.assertFalse(evidence['odds_observation_verified'])
        self.assertFalse(evidence['active'])
        model = joblib.load(directory / 'model.pkl')
        frame = pd.read_parquet(directory / 'dataset.parquet')
        X = module['build_features'](frame, 'basketball').tail(20).copy()
        with module['threadpool_limits'](limits=2):
            actual = model.predict_proba(X)
            market = model.market_model.predict_proba(X[module['train_sports'].FEATURES[:-1]])
            np.testing.assert_allclose(actual, market)
            X['odds_missing'] = 1.
            history = model.history_model.predict_proba(X[module['HISTORY_FEATURES']])
            np.testing.assert_allclose(model.predict_proba(X), history)
        self.assertTrue(np.isfinite(actual).all())
        np.testing.assert_allclose(actual.sum(axis=1), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
