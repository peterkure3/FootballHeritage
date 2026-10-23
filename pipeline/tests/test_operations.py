"""Operational coverage excludes stale/invalid evidence and duplicate observations."""
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy import text

from api import operations
from api.db import get_db_connection
from config import MODEL_VERSION


class CollectionReceiptTests(unittest.TestCase):
    def test_receipt_exposes_counts_without_local_paths_or_credentials(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / 'run'
            capture.mkdir()
            (capture / 'source_report.json').write_text(json.dumps({
                'run_id': 'run', 'completed_at': '2026-10-15T00:00:00Z', 'snapshot_count': 10,
                'output': 'private-path', 'direct_sources': [{'bookmaker': 'test', 'status': 'collected',
                    'snapshots': 10, 'source_url': 'https://example.org?apiKey=secret'}]}), encoding='utf-8')
            report = operations.collection_receipt(root)
            self.assertEqual(report['sources_with_quotes'], 1)
            self.assertEqual(report['transport'], 'requests')
            self.assertNotIn('private-path', json.dumps(report))
            self.assertNotIn('secret', json.dumps(report))
            (capture / 'source_report.json').write_bytes(b'\x00' * 20)
            self.assertEqual(operations.collection_receipt(root), {'state': 'unavailable'})
        self.assertEqual(operations.collection_receipt(Path(temporary)), {'state': 'missing'})


@unittest.skipUnless(os.environ.get('RUN_PREDICTION_DB_TESTS') == '1', 'Rollback-only PostgreSQL coverage test')
class OperationsDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = get_db_connection().connect()
        self.transaction = self.connection.begin()
        for query in [
            'CREATE TEMP TABLE matches (match_id INT PRIMARY KEY,competition TEXT,date TIMESTAMP,status TEXT,result TEXT) ON COMMIT DROP',
            'CREATE TEMP TABLE predictions (id SERIAL,match_id INT,model_version TEXT,winner TEXT,home_prob FLOAT,draw_prob FLOAT,away_prob FLOAT,created_at TIMESTAMP) ON COMMIT DROP',
            'CREATE TEMP TABLE odds (id SERIAL,match_id INT,bookmaker TEXT,home_win FLOAT,draw FLOAT,away_win FLOAT,updated_at TIMESTAMP) ON COMMIT DROP',
        ]:
            self.connection.execute(text(query))
        self.now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.patches = [
            patch.object(operations, 'get_db_connection', return_value=self),
            patch.object(operations, 'bookmaker_catalog', return_value=[
                {'bookmaker': name, 'name': name} for name in ['A', 'B', 'C']]),
            patch.object(operations, 'load_status_json', return_value={'outcome': 'success', 'recovery_evidence': 'private-path'}),
            patch.object(operations, 'collection_receipt', return_value={'state': 'missing'}),
        ]
        for item in self.patches:
            item.start()

    def connect(self):
        return nullcontext(self.connection)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.transaction.rollback()
        self.connection.close()

    def fixture(self, identifier, status='TIMED', days=2):
        self.connection.execute(text('INSERT INTO matches VALUES (:id,:league,:date,:status,NULL)'),
            {'id': identifier, 'league': 'League ' + str(identifier), 'date': self.now + timedelta(days=days), 'status': status})

    def prediction(self, identifier, age=1, probabilities=(.6, .25, .15), version=MODEL_VERSION):
        self.connection.execute(text('''INSERT INTO predictions
            (match_id,model_version,winner,home_prob,draw_prob,away_prob,created_at)
            VALUES (:id,:version,'home_win',:home,:draw,:away,:created)'''),
            {'id': identifier, 'version': version, 'home': probabilities[0], 'draw': probabilities[1],
             'away': probabilities[2], 'created': self.now - timedelta(hours=age)})

    def quote(self, identifier, bookmaker, age=1, prices=(2., 3., 5.)):
        self.connection.execute(text('''INSERT INTO odds (match_id,bookmaker,home_win,draw,away_win,updated_at)
            VALUES (:id,:book,:home,:draw,:away,:observed)'''),
            {'id': identifier, 'book': bookmaker, 'home': prices[0], 'draw': prices[1], 'away': prices[2],
             'observed': self.now - timedelta(hours=age)})

    def test_coverage_and_ev_use_latest_fresh_valid_evidence(self):
        self.fixture(1)
        self.fixture(2)
        self.fixture(3, status='LIVE')
        self.fixture(4, days=-1)
        self.prediction(1)
        self.prediction(1, version='inactive')
        self.prediction(2, age=25)
        self.quote(1, 'A', age=2, prices=(9., 9., 9.))
        self.quote(1, 'A', age=1)
        self.quote(1, 'B', prices=(2.5, 3.1, 4.))
        self.quote(2, 'A', age=25)
        self.quote(3, 'A')
        self.quote(4, 'A')
        for name, prices, age in [('future', (2., 3., 5.), -1),
                                  ('invalid', (1., 3., 5.), 1),
                                  ('nan', (float('nan'), 3., 5.), 1),
                                  ('infinite', (float('inf'), 3., 5.), 1),
                                  ('incomplete', (2., None, 5.), 1)]:
            self.quote(1, name, age, prices)
        result = operations.overview()
        summary = result['summary']
        self.assertEqual(summary['upcoming_fixtures'], 2)
        self.assertEqual(summary['fresh_quotes'], 2)
        self.assertEqual(summary['priced_fixtures'], 1)
        self.assertEqual(summary['current_forecasts'], 1)
        self.assertEqual(summary['compared_outcomes'], 3)
        self.assertEqual(summary['positive_ev_outcomes'], 1)
        self.assertEqual(result['covered_bookmakers'], 2)
        self.assertEqual(result['configured_bookmakers'], 3)
        self.assertNotIn('private-path', json.dumps(result))
        self.assertEqual(len(result['bookmakers']), 3)

    def test_latest_invalid_prediction_and_future_quote_do_not_fall_back_to_older_values(self):
        self.fixture(1)
        self.prediction(1, age=2)
        self.prediction(1, age=1, probabilities=(.8, .8, .8))
        self.quote(1, 'A')
        self.quote(1, 'A', age=-1)
        summary = operations.overview()['summary']
        self.assertEqual(summary['current_forecasts'], 0)
        self.assertEqual(summary['fresh_quotes'], 0)
        self.assertEqual(summary['compared_outcomes'], 0)

    def test_empty_store_is_zero_coverage_with_no_invented_timestamps(self):
        result = operations.overview()
        self.assertEqual(result['summary']['upcoming_fixtures'], 0)
        self.assertEqual(result['summary']['positive_ev_outcomes'], 0)
        self.assertIsNone(result['summary']['latest_forecast_at'])
        self.assertIsNone(result['summary']['latest_quote_at'])
        self.assertEqual(result['covered_bookmakers'], 0)


if __name__ == '__main__':
    unittest.main()
