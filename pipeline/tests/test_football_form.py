"""Form must use dated completed games, preserve ordering and match model inputs."""
import unittest
from datetime import datetime, timezone

import pandas as pd

from etl.fetch_football_form import last_five, normalize_result
from models.data import canonical_matches
from models.features import build_live_features


class FormTests(unittest.TestCase):
    def test_form_matches_model_and_excludes_future_and_same_day(self):
        rows = [dict(date=f'2026-10-{i+1:02d}', home_team='Porto', away_team=f'Other {i}',
                     home_score=2 if i < 4 else 0, away_score=1) for i in range(7)]
        history = canonical_matches([pd.DataFrame(rows)])
        cutoff = datetime(2026, 10, 6, 20, tzinfo=timezone.utc)
        form = last_five(history, 'Porto', cutoff)
        features = build_live_features(history, 'Porto', 'PSV', pd.Timestamp(cutoff)).iloc[0]
        self.assertEqual(form['sequence'], 'WWWWL')
        self.assertEqual(form['wins'], features.home_team_wins_last_n)
        self.assertEqual(form['losses'], features.home_team_losses_last_n)
        self.assertEqual(form['matches'][-1]['opponent'], 'Other 4')

    def test_away_orientation_and_missing_history(self):
        history = canonical_matches([pd.DataFrame([dict(date='2026-10-01', home_team='A', away_team='B', home_score=0, away_score=1)])])
        cutoff = datetime(2026, 10, 5, tzinfo=timezone.utc)
        self.assertEqual(last_five(history, 'B', cutoff)['sequence'], 'W')
        self.assertEqual(last_five(history, 'B', cutoff)['status'], 'insufficient_history')
        self.assertEqual(last_five(history, 'Missing', cutoff)['games'], 0)

    def test_rejects_unfinished_future_and_nonregulation_scores(self):
        now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        match = dict(id=1, status='FINISHED', utcDate='2026-10-18T10:00:00Z',
                     homeTeam=dict(id=1, name='A'), awayTeam=dict(id=2, name='B'),
                     competition=dict(code='CL'), score=dict(duration='REGULAR', fullTime=dict(home=2, away=1)))
        self.assertEqual(normalize_result(match, now)['home_score'], 2)
        self.assertIsNone(normalize_result(match | dict(status='IN_PLAY'), now))
        self.assertIsNone(normalize_result(match | dict(utcDate='2026-10-20T10:00:00Z'), now))
        self.assertIsNone(normalize_result(match | dict(score=dict(duration='PENALTY_SHOOTOUT', fullTime=dict(home=5, away=4))), now))
        self.assertIsNone(normalize_result(match | dict(score=dict(duration='REGULAR', fullTime=dict(home=-1, away=0))), now))


if __name__ == '__main__':
    unittest.main()
