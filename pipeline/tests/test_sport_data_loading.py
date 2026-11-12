"""Batch timestamp parsing preserves historical eligibility and score quarantine."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from models.sport_data import load_games

NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def score_event(**changes):
    return {'id': 'game', 'sport_key': 'basketball_nba', 'completed': True,
            'commence_time': '2026-11-10T18:00:00Z', 'home_team': 'Home', 'away_team': 'Away',
            'scores': [{'name': 'Home', 'score': '110'}, {'name': 'Away', 'score': '100'}], **changes}


class BatchedSportDataTests(unittest.TestCase):
    @patch('models.sport_data.datetime')
    def test_nba_archive_mixed_timezones_invalid_dates_and_unfinished_scores(self, clock):
        clock.now.return_value = NOW
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base = {'home': 'Home', 'visitor': 'Away', 'home_pts': 110, 'visitor_pts': 100}
            write_json(root / 'historical/nba/games/nba_games_test.json', [
                {**base, 'date': '2026-11-01'},
                {**base, 'date': '2026-11-02T21:00:00+03:00'},
                {**base, 'date': 'invalid'},
                {**base, 'date': '2026-11-13T00:00:00Z'},
                {**base, 'date': '2026-11-03T00:00:00Z', 'home_pts': None},
            ])
            games = load_games('basketball', root)
            self.assertEqual(len(games), 2)
            self.assertEqual(games.date.iloc[1], pd.Timestamp('2026-11-02T18:00:00Z'))
            self.assertTrue(games.date_precision.eq('DAY').all())
            self.assertEqual(games.result_available_at.iloc[0], pd.Timestamp('2026-11-03T00:00:00Z'))

    @patch('models.sport_data.datetime')
    def test_historical_rows_wait_for_observed_result_availability(self, clock):
        clock.now.return_value = NOW
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'historical/basketball_leagues/capture'
            folder.mkdir(parents=True)
            base = {'league': 'basketball_ncaab', 'completed': True, 'home_team': 'Home', 'away_team': 'Away',
                    'home_score': 80, 'away_score': 70, 'date_precision': 'TIMESTAMP'}
            rows = [
                {**base, 'provider_event_id': 'ready', 'date': '2026-11-01T21:00:00+03:00', 'result_available_at': '2026-11-02'},
                {**base, 'provider_event_id': 'unobserved', 'date': '2026-11-02', 'result_available_at': '2026-11-13T00:00:00Z'},
                {**base, 'provider_event_id': 'future', 'date': '2026-11-13T00:00:00Z', 'result_available_at': 'not-yet-recorded'},
            ]
            data = '\n'.join(json.dumps(row) for row in rows).encode()
            (folder / 'normalized.jsonl').write_bytes(data)
            write_json(folder / 'manifest.json', {'normalized_sha256': hashlib.sha256(data).hexdigest()})
            games = load_games('ncaab', root)
            self.assertEqual(games.provider_event_id.tolist(), ['ready'])
            self.assertEqual(games.date.iloc[0], pd.Timestamp('2026-11-01T18:00:00Z'))
            (folder / 'normalized.jsonl').write_bytes(data + b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_games('ncaab', root)

    @patch('models.sport_data.datetime')
    def test_score_capture_scope_offsets_and_conservative_observation_time(self, clock):
        clock.now.return_value = NOW
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / 'the_odds_api/scores_basketball_nba_test.json', {
                'fetched_at': '2026-11-10T22:00:00Z', 'events': [
                    score_event(commence_time='2026-11-10T21:00:00+03:00'),
                    score_event(sport_key='basketball_wnba', commence_time='invalid'),
                    score_event(completed=False, commence_time='invalid'),
                ]})
            games = load_games('basketball', root)
            self.assertEqual(len(games), 1)
            self.assertEqual(games.date.iloc[0], pd.Timestamp('2026-11-10T18:00:00Z'))
            self.assertEqual(games.result_available_at.iloc[0], pd.Timestamp('2026-11-11T00:00:00Z'))
            self.assertEqual(games.home_score.iloc[0], 110)

    @patch('models.sport_data.datetime')
    def test_conflicting_snapshots_still_quarantine_the_entire_fixture(self, clock):
        clock.now.return_value = NOW
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, home_score in enumerate((110, 111)):
                write_json(root / f'the_odds_api/scores_basketball_nba_{index}.json', {
                    'fetched_at': '2026-11-11T00:00:00Z', 'events': [score_event(scores=[
                        {'name': 'Home', 'score': home_score}, {'name': 'Away', 'score': 100}])]})
            games = load_games('basketball', root)
            self.assertTrue(games.empty)
            self.assertEqual(games.attrs['data_quality']['conflicting_fixtures_quarantined'], 1)

    def test_empty_captures_remain_an_empty_dataset(self):
        with TemporaryDirectory() as directory:
            for sport in ('basketball', 'ncaab', 'wnba', 'nfl', 'ncaaf'):
                with self.subTest(sport=sport):
                    self.assertTrue(load_games(sport, Path(directory)).empty)
