"""Native identities, untimestamped prices and causal nflfastR efficiency."""
from copy import deepcopy
import unittest

import numpy as np
import pandas as pd

from models.gridiron_sources import american_decimal, normalize_nfl, normalize_cfbd
from models.gridiron_efficiency import build_efficiency_features


def nfl_row():
    return {'game_id': '2024_01_KC_LA', 'season': 2024, 'game_type': 'REG', 'gameday': '2024-09-08',
        'gametime': '20:20', 'home_team': 'LA', 'away_team': 'KC', 'home_score': 21, 'away_score': 24,
        'location': 'Home', 'home_moneyline': 150, 'away_moneyline': -170,
        'spread_line': -3.5, 'total_line': 45.5, 'pfr': '202409080ram'}


def college_game():
    return {'id': 1, 'season': 2024, 'seasonType': 'regular', 'startDate': '2024-09-08T20:00:00Z',
        'completed': True, 'homeId': 10, 'awayId': 20, 'homeTeam': 'Alabama', 'awayTeam': 'Georgia',
        'homeClassification': 'fbs', 'awayClassification': 'fbs', 'homePoints': 24,
        'awayPoints': 21, 'neutralSite': True}


def college_line():
    return {'id': 1, 'startDate': '2024-09-08T20:00:00Z', 'homeTeamId': 10, 'awayTeamId': 20,
        'homeTeam': 'Alabama', 'awayTeam': 'Georgia', 'homeScore': 24, 'awayScore': 21,
        'lines': [{'provider': 'Book', 'homeMoneyline': -150, 'awayMoneyline': 130,
            'spread': -3.5, 'overUnder': 45.5, 'spreadOpen': -2.5, 'overUnderOpen': 44.5}]}


class GridironSourceTests(unittest.TestCase):
    def test_prices(self):
        self.assertEqual(american_decimal(150), 2.5)
        self.assertEqual(american_decimal(-200), 1.5)
        self.assertTrue(np.isnan(american_decimal(None)))
        for invalid in [0, 99, -99, float('inf')]:
            with self.assertRaises(ValueError):
                american_decimal(invalid)

    def test_nfl_eastern_time_and_identity(self):
        game = normalize_nfl(pd.DataFrame([nfl_row()]), 'source').iloc[0]
        self.assertEqual(game.date, pd.Timestamp('2024-09-09T00:20:00Z'))
        self.assertEqual(game.home_team, 'Los Angeles Rams')
        self.assertEqual(game.away_team, 'Kansas City Chiefs')
        self.assertEqual(game.result, 'away_win')
        self.assertIsNone(game.odds_observed_at)
        self.assertEqual(game.home_win, 2.5)

    def test_nfl_ties_and_relocations(self):
        row = nfl_row() | {'home_team': 'STL', 'home_score': 24, 'location': 'Neutral'}
        game = normalize_nfl(pd.DataFrame([row]), 'source').iloc[0]
        self.assertEqual(game.result, 'draw')
        self.assertEqual(game.home_team, 'Los Angeles Rams')
        self.assertTrue(game.neutral_site)

    def test_duplicate_nfl_ids_rejected(self):
        with self.assertRaises(ValueError):
            normalize_nfl(pd.DataFrame([nfl_row(), nfl_row()]), 'source')

    def test_unfinished_and_not_yet_available_results_excluded(self):
        rows = [nfl_row(), nfl_row() | {'game_id': 'future', 'home_score': np.nan}]
        self.assertEqual(len(normalize_nfl(pd.DataFrame(rows), 'source')), 1)
        with self.assertRaises(ValueError):
            normalize_nfl(pd.DataFrame([nfl_row()]), 'source', now='2024-09-09T00:30:00Z')

    def test_college_native_id_join_and_preserved_opening_lines(self):
        games, quotes = normalize_cfbd([college_game()], [college_line()], 'source')
        self.assertEqual(len(games), 1)
        self.assertEqual(games.iloc[0].provider_event_id, '1')
        self.assertEqual(games.iloc[0].odds_books, 1)
        self.assertTrue(games.iloc[0].neutral_site)
        self.assertIsNone(games.iloc[0].odds_observed_at)
        self.assertEqual(quotes[0]['spread_open'], -2.5)

    def test_wrong_college_team_score_or_time_never_joins(self):
        for field, wrong in [('homeTeam', 'Other'), ('homeTeamId', 99), ('homeScore', 99),
                              ('startDate', '2024-09-08T21:00:00Z')]:
            line = college_line() | {field: wrong}
            games, quotes = normalize_cfbd([college_game()], [line], 'source')
            self.assertTrue(pd.isna(games.iloc[0].home_win))
            self.assertEqual(quotes, [])

    def test_college_duplicate_provider_rejected(self):
        line = college_line()
        line['lines'].append(deepcopy(line['lines'][0]))
        with self.assertRaises(ValueError):
            normalize_cfbd([college_game()], [line], 'source')

    def test_college_lower_divisions_and_ties_excluded(self):
        with self.assertRaises(ValueError):
            normalize_cfbd([college_game() | {'homeClassification': 'fcs', 'awayClassification': 'fcs'}], [], 'source')
        with self.assertRaises(ValueError):
            normalize_cfbd([college_game() | {'awayPoints': 24}], [], 'source')

    def test_pbp_future_and_same_game_results_cannot_change_prior_features(self):
        rows, stats = [], []
        for i in range(40):
            date = pd.Timestamp('2024-01-07') + pd.Timedelta(days=7*i)
            rows.append(nfl_row() | {'game_id': str(i), 'gameday': str(date.date())})
            stats.extend([{'game_id': str(i), 'posteam': 'LA', 'defteam': 'KC', 'epa_per_play': .1,
                'success_rate': .55}, {'game_id': str(i), 'posteam': 'KC', 'defteam': 'LA',
                'epa_per_play': -.1, 'success_rate': .4}])
        games = normalize_nfl(pd.DataFrame(rows), 'source')
        stats = pd.DataFrame(stats)
        before = build_efficiency_features(games, stats)
        self.assertEqual(before.iloc[0].home_pbp_games, 0)
        self.assertEqual(before.iloc[1].home_pbp_games, 1)
        changed = stats.copy()
        changed.loc[changed.game_id.astype(int).ge(20), 'epa_per_play'] = 99
        after = build_efficiency_features(games, changed)
        np.testing.assert_allclose(before.iloc[:21], after.iloc[:21])
        self.assertNotEqual(before.iloc[21].home_offense_epa, after.iloc[21].home_offense_epa)
        duplicated = pd.concat([stats, stats.iloc[:1]])
        with self.assertRaises(ValueError):
            build_efficiency_features(games, duplicated)


if __name__ == '__main__':
    unittest.main()
