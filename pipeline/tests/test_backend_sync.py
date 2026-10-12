"""Sync regression checks; PostgreSQL checks use isolated disposable schemas."""
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_to_backend import connection_settings, sync_matches_to_backend


class ConnectionSettingsTests(unittest.TestCase):
    def test_pegasus_credentials_and_tunnel_override(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / 'source.env'
            path.write_text('POSTGRES_DB=football_betting\nPOSTGRES_USER=worker\nPOSTGRES_PASSWORD=test-only\n')
            settings = connection_settings(path, 'PIPELINE', 'unused', '127.0.0.1', 55433)
            self.assertEqual(settings['dbname'], 'football_betting')
            self.assertEqual(settings['user'], 'worker')
            self.assertEqual(settings['password'], 'test-only')
            self.assertEqual(settings['port'], '55433')

    def test_missing_configuration_fails_before_connecting(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                connection_settings(Path('missing-test-only.env'), 'PIPELINE', 'unused')


@unittest.skipUnless(os.getenv('SYNC_TEST_DATABASE_URL'), 'Set SYNC_TEST_DATABASE_URL for PostgreSQL tests')
class PostgreSQLSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = parse_dsn(os.environ['SYNC_TEST_DATABASE_URL'])
        cls.admin = psycopg2.connect(**cls.settings)
        cls.admin.autocommit = True
        stamp = uuid.uuid4().hex
        cls.source = f'sync_source_{stamp}'
        cls.target = f'sync_target_{stamp}'
        with cls.admin.cursor() as cursor:
            for name in (cls.source, cls.target):
                cursor.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
            cursor.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(cls.source)))
            cursor.execute('''CREATE TABLE matches (
                match_id integer PRIMARY KEY, competition text, season date, date timestamp,
                home_team text, away_team text, home_score integer, away_score integer,
                result text, status text)''')
            cursor.execute('''CREATE TABLE odds (
                id serial PRIMARY KEY, match_id integer, home_win double precision,
                draw double precision, away_win double precision, updated_at timestamp)''')
            cursor.execute('''CREATE TABLE nba_games (
                game_id text, sport_title text, commence_time timestamp, home_team text,
                away_team text, home_score integer, away_score integer, completed boolean)''')
            cursor.execute(sql.SQL('CREATE TABLE {}.events (LIKE public.events INCLUDING ALL)').format(
                sql.Identifier(cls.target)))

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.admin.cursor() as cursor:
            for name in (cls.source, cls.target):
                cursor.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))
        cls.admin.close()

    def setUp(self) -> None:
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.source)))
            cursor.execute('TRUNCATE matches, odds, nba_games RESTART IDENTITY')
            cursor.execute(sql.SQL('TRUNCATE {}.events').format(sql.Identifier(self.target)))

    def fixture(self, match_id: int = 1, home: str = 'Home', day: int = 12) -> None:
        with self.admin.cursor() as cursor:
            cursor.execute('''INSERT INTO matches VALUES
                (%s, 'Premier League', '2026-08-01', %s, %s, 'Away', NULL, NULL, NULL, 'TIMED')''',
                (match_id, datetime(2026, 10, day, 15), home))

    def sync(self, dry_run: bool = False) -> dict:
        source = {**self.settings, 'options': f'-c search_path={self.source}'}
        target = {**self.settings, 'options': f'-c search_path={self.target}'}
        with self.assertLogs(level='INFO'):
            return sync_matches_to_backend(source, target, dry_run)

    def events(self) -> list:
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL('SELECT id, event_date, status, moneyline_home, moneyline_away '
                                   'FROM {}.events ORDER BY id').format(sql.Identifier(self.target)))
            return cursor.fetchall()

    def test_preview_is_read_only(self) -> None:
        self.fixture()
        self.assertEqual(self.sync(True)['total'], 1)
        self.assertEqual(self.events(), [])

    def test_reschedule_keeps_event_id_and_missing_odds_keep_prices(self) -> None:
        self.fixture()
        self.sync()
        original_id = self.events()[0][0]
        with self.admin.cursor() as cursor:
            cursor.execute(sql.SQL('UPDATE {}.events SET moneyline_home=150, moneyline_away=-120').format(
                sql.Identifier(self.target)))
            cursor.execute("UPDATE matches SET date='2026-10-13 16:00:00', status='IN_PLAY', home_score=1")
        self.sync()
        rows = self.events()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], original_id)
        self.assertEqual(rows[0][1], datetime(2026, 10, 13, 16, tzinfo=timezone.utc))
        self.assertEqual(rows[0][2], 'LIVE')
        self.assertEqual(tuple(rows[0][3:]), (150, -120))

    def test_only_latest_odds_snapshot_is_used(self) -> None:
        self.fixture()
        with self.admin.cursor() as cursor:
            cursor.execute("INSERT INTO odds (match_id,home_win,away_win,updated_at) VALUES "
                           "(1,2.0,2.0,'2026-10-11'),(1,2.5,1.5,'2026-10-12')")
        self.assertEqual(self.sync()['total'], 1)
        self.assertEqual(tuple(self.events()[0][3:]), (150, -200))

    def test_record_failure_rolls_back_entire_batch(self) -> None:
        self.fixture(1, day=13)
        self.fixture(2, home='X' * 1000, day=12)
        with self.assertRaises(psycopg2.Error):
            self.sync()
        self.assertEqual(self.events(), [])


if __name__ == '__main__':
    unittest.main()
