import unittest

import pandas as pd

from models.sport_data import canonical_games
from scripts.validate_nfl_2026_reference import reference_history


class NflReferenceValidationTests(unittest.TestCase):
    def frame(self, seasons):
        return canonical_games([{'provider_event_id': str(season)+'_01_A_B', 'league': 'americanfootball_nfl',
            'home_team': 'Atlanta Falcons', 'away_team': 'Buffalo Bills', 'home_score': 30, 'away_score': 20,
            'neutral_site': False, 'date': f'{season}-09-01T18:00:00Z',
            'result_available_at': f'{season}-09-03T00:00:00Z', 'completed': True}
            for season in seasons], 'nfl')

    def test_original_history_is_preserved_and_only_later_games_append(self):
        old = self.frame([2014, 2015]); new = self.frame([2015, 2016])
        actual = reference_history(old, new)
        self.assertEqual(len(actual), 3)
        self.assertEqual(actual.iloc[:2].provider_event_id.tolist(), old.provider_event_id.tolist())

    def test_changed_overlap_or_missing_older_game_requires_audit(self):
        old = self.frame([2014, 2016]); new = self.frame([2015, 2016])
        with self.assertRaisesRegex(ValueError, 'older'):
            reference_history(old, new)
        changed = self.frame([2016]); changed.loc[0, 'home_score'] = 31
        with self.assertRaisesRegex(ValueError, 'disagreement'):
            reference_history(old, changed)
