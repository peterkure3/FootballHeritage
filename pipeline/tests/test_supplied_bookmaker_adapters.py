import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from etl.regional_sportsbooks import normalize_cloudbet, normalize_1xbet, normalize_22bet, normalize_betonline
from etl.scrape_sportsbooks import get_public_source

OBSERVED = '2026-10-14T03:00:00Z'


class SuppliedFeedTests(unittest.TestCase):
    def setUp(self):
        self.cloud = {'key': 'soccer-international-clubs-uefa-champions-league',
            'name': 'UEFA Champions League', 'sport': {'key': 'soccer'}, 'events': [{
                'id': 10, 'type': 'EVENT_TYPE_EVENT', 'status': 'TRADING',
                'metadata': {'eventStatus': 'not_started'}, 'startTime': '2026-10-14T16:45:00Z',
                'home': {'name': 'Home', 'key': 'home'}, 'away': {'name': 'Away', 'key': 'away'},
                'markets': {'soccer.match_odds': {'submarkets': {'period=ft': {'selections': [
                    {'outcome': name, 'params': '', 'marketUrl': 'soccer.match_odds/' + name,
                     'price': price, 'status': 'SELECTION_ENABLED', 'side': 'BACK'}
                    for name, price in [('home', 2.1), ('draw', 3.2), ('away', 4.3)]]}}}}}]}
        self.one = [{'id': 10, 'mainGameId': 10, 'sport': {'id': 1},
            'liga': {'id': 118587, 'name': 'UEFA Champions League'},
            'opponent1': {'fullName': 'Home Club'}, 'opponent2': {'fullName': 'Away Club'},
            'startTs': int(datetime(2026, 10, 14, 16, 45, tzinfo=timezone.utc).timestamp()),
            'eventGroups': [{'groupId': 1, 'shortGroupId': 1,
                'events': [[{'type': kind, 'cf': price}] for kind, price in [(1, 2.1), (2, 3.2), (3, 4.3)]]}]}]

    def parse_cloud(self, payload):
        return normalize_cloudbet(payload, OBSERVED, 'raw/cloud.json', 'test')

    def parse_one(self, payload):
        return normalize_1xbet(payload, OBSERVED, 'raw/one.json', 'test')

    def test_valid_full_match_prices_and_utc_kickoff(self):
        for parser, payload, region in [(self.parse_cloud, self.cloud, 'GLOBAL'),
                                        (self.parse_one, self.one, None)]:
            rows = parser(payload)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['region'], region)
            self.assertEqual(rows[0]['commence_time'], '2026-10-14T16:45:00+00:00')
            self.assertEqual([(o['selection'], o['odds_decimal']) for o in rows[0]['outcomes']],
                             [('HOME', 2.1), ('DRAW', 3.2), ('AWAY', 4.3)])

    def test_cloudbet_rejects_live_outright_wrong_league_and_half_time(self):
        for case in ['live', 'outright', 'league', 'half', 'naive', 'started']:
            p = deepcopy(self.cloud)
            e = p['events'][0]
            if case == 'live': e['metadata']['eventStatus'] = 'live'
            if case == 'outright': e['type'] = 'EVENT_TYPE_OUTRIGHT'
            if case == 'league': p['key'] = 'other-champions-league'
            if case == 'half': e['markets']['soccer.match_odds']['submarkets'] = {'period=1h': {}}
            if case == 'naive': e['startTime'] = '2026-10-14T16:45:00'
            if case == 'started': e['startTime'] = OBSERVED
            self.assertEqual(self.parse_cloud(p), [], case)

    def test_cloudbet_rejects_lay_disabled_duplicate_missing_and_invalid_prices(self):
        for case in ['lay', 'disabled', 'duplicate', 'missing', 'nan', 'one', 'params']:
            p = deepcopy(self.cloud)
            selections = p['events'][0]['markets']['soccer.match_odds']['submarkets']['period=ft']['selections']
            if case == 'lay': selections[0]['side'] = 'LAY'
            if case == 'disabled': selections[0]['status'] = 'SELECTION_DISABLED'
            if case == 'duplicate': selections.append(selections[0].copy())
            if case == 'missing': selections.pop()
            if case == 'nan': selections[0]['price'] = float('nan')
            if case == 'one': selections[0]['price'] = 1
            if case == 'params': selections[0]['params'] = 'handicap=1'
            self.assertEqual(self.parse_cloud(p), [], case)

    def test_1xbet_rejects_subgames_live_wrong_league_and_other_markets(self):
        for name in ['Home', 'Away', 'Home (Special bets)', 'Away (Special bets)']:
            p = deepcopy(self.one)
            p[0]['opponent1']['fullName'] = name
            self.assertEqual(self.parse_one(p), [], name)
        for field, value in [('mainGameId', 11), ('periodName', '1st half'), ('gameTypeName', 'Corners'),
                             ('isLive', True), ('blocked', True), ('startTs', 0)]:
            p = deepcopy(self.one)
            p[0][field] = value
            self.assertEqual(self.parse_one(p), [], field)
        for case in ['league', 'sport', 'market', 'duplicate', 'missing', 'disabled', 'line', 'nan']:
            p = deepcopy(self.one)
            e = p[0]
            group = e['eventGroups'][0]
            if case == 'league': e['liga']['id'] = 1
            if case == 'sport': e['sport']['id'] = 2
            if case == 'market': group['groupId'] = 8
            if case == 'duplicate': group['events'].append(group['events'][0])
            if case == 'missing': group['events'].pop()
            if case == 'disabled': group['events'][0][0]['isBlocked'] = True
            if case == 'line': group['events'][0][0]['param'] = 1
            if case == 'nan': group['events'][0][0]['cf'] = float('nan')
            self.assertEqual(self.parse_one(p), [], case)

    def test_collectors_omit_cookies_and_conditional_headers(self):
        for book in ['cloudbet', '1xbet', '22bet']:
            response = Mock(ok=True, status_code=200, headers={'Content-Type': 'application/json'},
                            url='https://example.test/events', content=b'[]', text='[]')
            with TemporaryDirectory() as directory, patch('etl.scrape_sportsbooks.requests.get', return_value=response) as get:
                root = Path(directory)
                (root / 'raw').mkdir()
                get_public_source(book, response.url, root)
                headers = get.call_args.kwargs['headers']
                for name in ['Cookie', 'Authorization', 'if-modified-since', 'x-hd']:
                    self.assertNotIn(name, headers)
                self.assertIn('params', get.call_args.kwargs)

    def test_22bet_preserves_operator_and_uganda_region(self):
        rows = normalize_22bet(self.one, OBSERVED, 'raw/22bet.json', 'run')
        self.assertEqual(rows[0]['bookmaker'], '22bet')
        self.assertEqual(rows[0]['region'], 'UG')
        self.assertIn('22bet.ug', rows[0]['source_url'])
        self.one[0]['opponent1']['fullName'] = 'Home (Special bets)'
        self.assertEqual(normalize_22bet(self.one, OBSERVED, 'raw/22bet.json', 'run'), [])

    def bol(self):
        return {'IsError': False, 'IsValidModel': True, 'GameOffering': {
            'Sport': 'Soccer', 'League': 'UEFA CL', 'PeriodMin': 0,
            'Periods': [{'Number': 0, 'Name': 'Game'}], 'GamesDescription': [{'Game': {
                'GameId': 1, 'SportCastFixtureId': 2, 'DrawRotaion': 3,
                'HomeRotation': 4, 'AwayRotation': 5,
                'HomeTeam': 'Away Club', 'AwayTeam': 'Home Club',
                'WagerCutOff': '2026-10-14T16:45:00', 'ScheduleText': 'UEFA Champions League',
                'HomeLine': {'MoneyLine': {'DecimalLine': 4.3}},
                'AwayLine': {'MoneyLine': {'DecimalLine': 2.1}},
                'DrawLine': {'MoneyLine': {'DecimalLine': 3.2}}}}]}}

    def test_betonline_preserves_team_prices_and_utc(self):
        rows = normalize_betonline(self.bol(), OBSERVED, 'raw/bol.json', 'run')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['commence_time'], '2026-10-14T16:45:00+00:00')
        self.assertEqual(rows[0]['home_team'], 'Away Club')
        self.assertEqual(rows[0]['outcomes'][0]['odds_decimal'], 4.3)
        import pandas as pd
        from scripts.sync_bookmaker_grid import matched_grid_quotes
        fixtures = pd.DataFrame([{'match_id': 1, 'date': '2026-10-14T16:45:00Z',
            'home_team': 'Home Club', 'away_team': 'Away Club', 'competition': 'UEFA Champions League'}])
        matched = matched_grid_quotes(fixtures, rows)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched.iloc[0].home_win, 2.1)
        self.assertEqual(matched.iloc[0].away_win, 4.3)
        self.assertEqual(matched.iloc[0].draw, 3.2)
        self.assertTrue(matched_grid_quotes(fixtures.assign(date='2026-10-14T17:45:00Z'), rows).empty)
        self.assertTrue(matched_grid_quotes(pd.concat([fixtures, fixtures.assign(match_id=2)]), rows).empty)

    def test_betonline_rejects_alternate_incomplete_wrong_period_and_live(self):
        for case in ['child', 'draw', 'live', 'started', 'fixture', 'period', 'error', 'invalid']:
            p = self.bol()
            g = p['GameOffering']['GamesDescription'][0]['Game']
            if case == 'child': g['ParentLinkEvent'] = 99
            if case == 'draw': g['DrawLine']['MoneyLine']['DecimalLine'] = 0
            if case == 'live': g['LiveBettingID'] = 1
            if case == 'started': g['WagerCutOff'] = OBSERVED
            if case == 'fixture': g['SportCastFixtureId'] = None
            if case == 'period': p['GameOffering']['PeriodMin'] = 1
            if case == 'error': p['IsError'] = True
            if case == 'invalid': g['HomeLine']['MoneyLine']['DecimalLine'] = float('nan')
            self.assertEqual(normalize_betonline(p, OBSERVED, 'raw/bol.json', 'run'), [], case)

    def test_betonline_requests_utc_public_fixture_post(self):
        response = Mock(ok=True, status_code=200, headers={'Content-Type': 'application/json'},
                        url='https://example.test/events', content=b'{}', text='{}')
        with TemporaryDirectory() as directory, patch('etl.scrape_sportsbooks.requests.post', return_value=response) as post:
            root = Path(directory)
            (root / 'raw').mkdir()
            get_public_source('betonlineag', response.url, root)
            self.assertEqual(post.call_args.kwargs['headers']['utc-offset'], '0')
            self.assertEqual(post.call_args.kwargs['json']['League'], 'uefa-cl')
            self.assertNotIn('Cookie', post.call_args.kwargs['headers'])
