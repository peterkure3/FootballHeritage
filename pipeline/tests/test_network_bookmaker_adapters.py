from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from etl.regional_sportsbooks import normalize_betika
from etl.scrape_sportsbooks import get_public_source
from scripts.replay_bookmaker_network import eligible


class BetikaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.event = {'match_id': '1', 'sport_id': '3', 'sport_name': 'Soccer',
            'home_team': 'LASK', 'away_team': 'LIVERPOOL', 'is_esport': False, 'is_srl': False,
            'start_time': '2026-10-14 16:45:00', 'competition_name': 'UEFA Champions League',
            'competition_id': '358', 'category': 'International Clubs',
            'home_odd': '5.0', 'neutral_odd': '4.0', 'away_odd': '1.6',
            'odds': [{'sub_type_id': '1', 'name': '1X2', 'odds': [
                {'display': label, 'odd_key': name, 'odd_value': price,
                 'outcome_id': str(index), 'special_bet_value': ''}
                for index, (label, name, price) in enumerate([
                    ('1', 'LASK', '5.0'), ('X', 'draw', '4.0'), ('2', 'LIVERPOOL', '1.6')], 1)]}]}

    def parse(self, event):
        return normalize_betika({'data': [event]}, '2026-10-13T20:00:00Z', 'raw/betika.json', 'test')

    def test_utc_db_time_and_regional_identity_are_preserved(self):
        row = self.parse(self.event)[0]
        self.assertEqual(row['commence_time'], '2026-10-14T16:45:00+00:00')
        self.assertEqual(row['region'], 'UG')
        self.assertEqual(row['provider_competition_id'], '358')
        self.assertEqual(row['market_status'], 'UNKNOWN')
        self.assertEqual([o['selection'] for o in row['outcomes']], ['HOME', 'DRAW', 'AWAY'])

    def test_started_simulated_and_other_sports_are_excluded(self):
        for field, value in [('start_time', '2026-10-13 19:00:00'), ('is_esport', True),
                             ('is_srl', True), ('sport_id', '12'), ('is_live', True)]:
            event = deepcopy(self.event)
            event[field] = value
            self.assertEqual(self.parse(event), [])

    def test_promotional_incomplete_mismatched_and_suspended_markets_are_excluded(self):
        for case in ['market', 'duplicate', 'incomplete', 'team', 'line', 'suspended', 'price']:
            event = deepcopy(self.event)
            market = event['odds'][0]
            if case == 'market': market['sub_type_id'] = '186'
            if case == 'duplicate': market['odds'].append(market['odds'][0].copy())
            if case == 'incomplete': market['odds'].pop()
            if case == 'team': market['odds'][0]['odd_key'] = 'Wrong team'
            if case == 'line': market['odds'][0]['special_bet_value'] = 'half=1'
            if case == 'suspended': market['odds'][0]['is_suspended'] = True
            if case == 'price': event['home_odd'] = '2.0'
            self.assertEqual(self.parse(event), [], case)


class PublicNetworkTests(unittest.TestCase):
    def response(self, payload):
        body = json.dumps(payload)
        response = Mock(ok=True, status_code=200, headers={'Content-Type': 'application/json'},
            url='https://api-ug.betika.com/v1/uo/matches', text=body, content=body.encode())
        response.json.return_value = payload
        return response

    def test_betika_collects_all_pages_and_keeps_original_page_evidence(self):
        first = self.response({'data': [{'match_id': str(i)} for i in range(1000)], 'meta': {'total': 1002}})
        second = self.response({'data': [{'match_id': '1000'}, {'match_id': '1001'}]})
        with TemporaryDirectory() as temporary, patch('etl.scrape_sportsbooks.requests.get', side_effect=[first, second]) as get:
            root = Path(temporary)
            (root / 'raw').mkdir()
            row = get_public_source('betika', first.url, root)
            self.assertEqual(len(row['raw_pages']), 2)
            self.assertEqual(len(json.loads((root / row['raw_capture_ref']).read_text())['data']), 1002)
            self.assertEqual(get.call_args.kwargs['params']['page'], 2)
            self.assertNotIn('Cookie', get.call_args.kwargs['headers'])

    def test_incomplete_pagination_is_reported_without_exporting_a_complete_feed(self):
        first = self.response({'data': [{'match_id': str(i)} for i in range(1000)], 'meta': {'total': 1002}})
        second = self.response({'data': []})
        with TemporaryDirectory() as temporary, patch('etl.scrape_sportsbooks.requests.get', side_effect=[first, second]):
            root = Path(temporary)
            (root / 'raw').mkdir()
            self.assertEqual(get_public_source('betika', first.url, root)['status'], 'pagination_incomplete')

    def test_curl_replay_uses_public_fixture_requests_only(self):
        request = {'url': 'https://example.test/api/matches', 'method': 'GET', 'capture': 'response.json'}
        self.assertTrue(eligible(request))
        for url in ['https://sportybet.test/i18n/en.json', 'https://example.test/api/orders/placeBet',
                    'https://example.test/api/profile', 'https://example.test/api/events?token=redacted']:
            self.assertFalse(eligible(request | {'url': url}))
        self.assertFalse(eligible(request | {'method': 'POST', 'body': {'session': '<redacted>'}}))
