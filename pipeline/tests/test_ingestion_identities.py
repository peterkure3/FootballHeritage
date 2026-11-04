import unittest
import pandas as pd
from etl.identities import latest_fixtures
from sync_to_backend import standardize_sport_name


class IngestionIdentityTests(unittest.TestCase):
    def test_sport_aliases(self):
        for raw, expected in [('football', 'SOCCER'), ('Soccer', 'SOCCER'),
                              ('NFL', 'NFL'), ('americanfootball_nfl', 'NFL'),
                              ('college football', 'NFL'), ('basketball_nba', 'BASKETBALL'),
                              ('NBA_CUP', 'BASKETBALL')]:
            self.assertEqual(standardize_sport_name(raw), expected)

    def test_latest_observation_wins(self):
        frame = pd.DataFrame(dict(game_id=['a', 'a'], home_team=['A', 'A'],
            last_update=['2026-10-31T12:00:00Z', '2026-10-30T12:00:00Z'], completed=[True, False]))
        result = latest_fixtures(frame, 'game_id')
        self.assertEqual(len(result), 1)
        self.assertTrue(result.iloc[0].completed)

    def test_postponed_fixture_keeps_one_id(self):
        frame = pd.DataFrame(dict(match_id=[1, 1], home_team=['A', 'A'],
            date=['2026-10-30', '2026-10-31'], last_update=['2026-10-29', '2026-10-30']))
        result = latest_fixtures(frame, 'match_id')
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['date'], '2026-10-31')

    def test_collision_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting teams'):
            latest_fixtures(pd.DataFrame({'game_id': ['1', '1'], 'home_team': ['A', 'C']}), 'game_id')
