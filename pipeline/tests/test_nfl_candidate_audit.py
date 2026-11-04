import unittest

import pandas as pd

from scripts.audit_nfl_candidate import training_prior


class NflCandidateAuditTests(unittest.TestCase):
    def games(self):
        rows = []
        for season in [2024, 2025, 2026]:
            for week in [1, 9, 10, 18]:
                date = pd.Timestamp(f'{season}-09-01', tz='UTC')+pd.Timedelta(days=7*(week-1))
                rows.append({'season': season, 'week': week, 'date': date, 'result_available_at': date+pd.Timedelta(days=2),
                             'result': 'home_win' if week%2 else 'away_win'})
        return pd.DataFrame(rows)

    def test_prior_does_not_fit_calibration_or_heldout_outcomes(self):
        games = self.games(); original = training_prior(games, 2026)
        games.loc[games.season.eq(2026) | (games.season.eq(2025) & games.week.gt(9)), 'result'] = 'away_win'
        self.assertEqual(original.tolist(), training_prior(games, 2026).tolist())

    def test_empty_binary_training_set_is_explicitly_rejected(self):
        games = self.games(); games['result'] = 'draw'
        with self.assertRaisesRegex(ValueError, 'non-tied'):
            training_prior(games, 2026)
