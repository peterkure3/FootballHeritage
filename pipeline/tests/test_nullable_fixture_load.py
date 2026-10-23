"""Upcoming-only batches must load SQL NULL scores into integer columns."""
from contextlib import nullcontext
import os
from types import SimpleNamespace
import unittest

import pandas as pd
from sqlalchemy import text

from api.db import get_db_connection
from etl.load_to_db import upsert_matches


@unittest.skipUnless(os.environ.get('RUN_PREDICTION_DB_TESTS') == '1', 'Rollback-only PostgreSQL regression')
class NullableFixtureLoadTests(unittest.TestCase):
    def test_null_only_batch_then_completed_result_then_null_batch(self):
        with get_db_connection().connect() as connection:
            transaction = connection.begin()
            try:
                # A private schema isolates the loader's staging tables as well.
                connection.execute(text('CREATE SCHEMA nullable_fixture_regression'))
                connection.execute(text('SET LOCAL search_path TO nullable_fixture_regression'))
                connection.execute(text('''CREATE TABLE matches (match_id INTEGER PRIMARY KEY,
                    competition TEXT, date TIMESTAMP, home_team TEXT, away_team TEXT,
                    home_score INTEGER, away_score INTEGER, result TEXT, status TEXT)'''))
                engine = SimpleNamespace(begin=lambda: nullcontext(connection))
                frame = pd.DataFrame([{'match_id': 1, 'competition': 'Premier League',
                    'date': '2026-10-17T14:00:00Z', 'home_team': 'Home', 'away_team': 'Away',
                    'home_score': None, 'away_score': None, 'result': None, 'status': 'TIMED'}])
                upsert_matches(frame, engine)
                row = connection.execute(text('SELECT home_score,away_score,result FROM matches')).one()
                self.assertEqual(tuple(row), (None, None, None))
                upsert_matches(frame.assign(home_score=2, away_score=0, result='home_win', status='FINISHED'), engine)
                self.assertEqual(tuple(connection.execute(text('SELECT home_score,away_score,result FROM matches')).one()),
                                 (2, 0, 'home_win'))
                upsert_matches(frame.assign(match_id=2), engine)
                self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM matches')).scalar_one(), 2)
            finally:
                transaction.rollback()


if __name__ == '__main__':
    unittest.main()
