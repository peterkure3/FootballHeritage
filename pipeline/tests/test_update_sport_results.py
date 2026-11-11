"""Recent-score collection, safe publication and consumer integration."""
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import requests

from etl.update_sport_results import SPORTS, check_results, load_recent_results, normalize, update_results
from models.sport_data import load_games
from api.sport_performance import evaluate

OBSERVED = datetime(2020, 1, 3, tzinfo=timezone.utc)


def event(home=110, away=100):
    return {'id': 'game-1', 'season': {'year': 2020, 'type': 2}, 'competitions': [{
        'date': '2020-01-01T20:00:00Z', 'neutralSite': False,
        'status': {'type': {'completed': True, 'state': 'post', 'name': 'STATUS_FINAL'}},
        'competitors': [{'homeAway': 'home', 'score': str(home), 'team': {'id': 'h', 'displayName': 'Home'}},
                        {'homeAway': 'away', 'score': str(away), 'team': {'id': 'a', 'displayName': 'Away'}}]}]}


def response(events):
    result = Mock()
    result.content = json.dumps({'events': events}).encode()
    return result


class ResultUpdaterTests(unittest.TestCase):
    def test_each_sport_preserves_scope_final_score_and_capture_time(self):
        for sport, spec in SPORTS.items():
            with self.subTest(sport=sport):
                row = normalize({'events': [event()]}, sport, OBSERVED, 'raw.json')[0]
                self.assertEqual(row['league'], spec['league'])
                self.assertEqual(row['result_available_at'], OBSERVED.isoformat())
                self.assertEqual(row['home_score'], 110)
                self.assertEqual(row['date_precision'], 'TIMESTAMP')
        self.assertEqual(normalize({'events': [event(10, 10)]}, 'nfl', OBSERVED, 'raw.json')[0]['home_score'], 10)
        for sport in ['nba', 'wnba', 'ncaab', 'ncaaf']:
            with self.assertRaisesRegex(ValueError, 'tied'):
                normalize({'events': [event(10, 10)]}, sport, OBSERVED, 'raw.json')

    def test_live_preseason_allstar_and_bad_scores_never_publish(self):
        live = event()
        live['competitions'][0]['status']['type']['completed'] = False
        preseason = event()
        preseason['season']['type'] = 1
        allstar = event()
        allstar['competitions'][0]['type'] = {'abbreviation': 'ALLSTAR'}
        self.assertEqual(normalize({'events': [live, preseason, allstar]}, 'nba', OBSERVED, 'raw.json'), [])
        with self.assertRaisesRegex(ValueError, 'Invalid final score'):
            normalize({'events': [event('110.5')]}, 'nba', OBSERVED, 'raw.json')
        with self.assertRaisesRegex(ValueError, 'events list'):
            normalize({'error': 'bad source'}, 'nba', OBSERVED, 'raw.json')
        with self.assertRaisesRegex(ValueError, 'league does not match'):
            normalize({'leagues': [{'slug': 'nba'}], 'events': [event()]}, 'wnba', OBSERVED, 'raw.json')

    @patch('etl.update_sport_results.time.sleep')
    @patch('etl.update_sport_results.requests.get')
    def test_capture_load_and_ncaab_settlement_are_connected(self, get, _sleep):
        get.return_value = response([event()])
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report = update_results('ncaab', start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), root=root)
            self.assertEqual(report['completed_games'], 1)
            self.assertEqual(get.call_args.kwargs['params']['groups'], 50)
            rows = load_recent_results(['basketball_ncaab'], root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(load_recent_results(['basketball_wnba'], root), [])
            self.assertEqual(len(load_games('ncaab', root)), 1)
            forecast = {'fixture_id': 'f', 'sport': 'ncaab', 'home_team': 'Home', 'away_team': 'Away',
                        'kickoff': rows[0]['date'], 'recorded_at': '2020-01-01T18:00:00Z',
                        'settlement_rule': 'INCLUDING_OVERTIME', 'prediction': {
                            'generated_at': '2020-01-01T17:00:00Z', 'model_version': 'test', 'winner': 'home_win',
                            'probabilities': {'home_win': .6, 'away_win': .4}}}
            data = evaluate('ncaab', [forecast], rows, datetime.now(timezone.utc))
            self.assertEqual(data['summary']['total_predictions'], 1)
            update_results('ncaab', start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), root=root)
            self.assertEqual(len(load_games('ncaab', root)), 1)
            path = Path(report['output']) / 'normalized.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_recent_results(['basketball_ncaab'], root)

    @patch('etl.update_sport_results.time.sleep')
    @patch('etl.update_sport_results.requests.get')
    def test_recent_results_survive_historical_season_release_preference(self, get, _sleep):
        get.return_value = response([event()])
        with TemporaryDirectory() as folder:
            root = Path(folder)
            historical = event()
            historical['id'] = 'older-game'
            historical['competitions'][0]['date'] = '2019-12-01T20:00:00Z'
            row = normalize({'events': [historical]}, 'ncaab', OBSERVED, 'historical.json')[0]
            row['collection_scope'] = 'SEASON_RELEASE'
            directory = root / 'historical/basketball_leagues/old'
            directory.mkdir(parents=True)
            raw = (json.dumps(row) + '\n').encode()
            (directory / 'normalized.jsonl').write_bytes(raw)
            (directory / 'manifest.json').write_text(json.dumps({'normalized_sha256': hashlib.sha256(raw).hexdigest()}))
            update_results('ncaab', start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), root=root)
            self.assertEqual(len(load_games('ncaab', root)), 2)

    @patch('etl.update_sport_results.time.sleep')
    @patch('etl.update_sport_results.requests.get')
    def test_partial_update_does_not_replace_prior_capture(self, get, _sleep):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            get.return_value = response([event()])
            update_results('nba', start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), root=root)
            get.side_effect = [response([event()]), requests.ConnectionError('offline'), requests.ConnectionError('offline'), requests.ConnectionError('offline')]
            with self.assertRaises(requests.ConnectionError):
                update_results('nba', start_date=date(2020, 1, 1), end_date=date(2020, 1, 2), root=root)
            self.assertEqual(len(list((root / 'results/nba').glob('*/manifest.json'))), 1)
            self.assertEqual(len(load_recent_results(['basketball_nba'], root)), 1)

    def test_invalid_range_fails_before_any_network_request(self):
        with patch('etl.update_sport_results.requests.get') as get:
            with self.assertRaises(ValueError):
                update_results('nba', start_date=date(2020, 2, 1), end_date=date(2020, 1, 1))
            get.assert_not_called()

    def test_wrappers_work_as_paths_from_outside_pipeline(self):
        root = Path(__file__).resolve().parents[2]
        for sport in SPORTS:
            result = subprocess.run([sys.executable, str(root / f'pipeline/etl/update_{sport}_results.py'), '--help'],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--check', result.stdout)

    @patch('etl.update_sport_results.requests.get')
    def test_check_is_read_only(self, get):
        with TemporaryDirectory() as folder:
            self.assertEqual(check_results('nfl', Path(folder))['stored_final_rows'], 0)
            self.assertEqual(list(Path(folder).iterdir()), [])
            get.assert_not_called()
