"""Check collection provenance and reject unsuitable football prices."""

from copy import deepcopy
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock
from tempfile import TemporaryDirectory
import json
import requests

from etl.scrape_sportsbooks import collect_target, get_public_source, normalize_provider_events, request_primary_source
from etl.sportsbook_parsers import normalize_bovada


class SportsbookScrapingTests(unittest.TestCase):
    def test_betpawa_fetches_discovered_competitions_in_separate_queries(self):
        directory = {'withRegions': [{'regions': [
            {'region': {'name': region}, 'competitions': [{'competition': {'name': league, 'id': identifier}}]}
            for region, league, identifier in [('England', 'Premier League', 'pl'),
                ('International', 'UEFA Champions League', 'cl'), ('International', 'AFC Champions League', 'afc')]
        ]}]}
        metadata = Mock(status_code=200, content=json.dumps(directory).encode())
        metadata.json.return_value = directory
        response = Mock(status_code=200, ok=True, url='https://www.betpawa.ug/api/sportsbook/v4/events/lists/by-queries',
            content=b'{"responses":[]}', text='{"responses":[]}', headers={'Content-Type':'application/json'})
        with TemporaryDirectory() as temporary, patch('etl.scrape_sportsbooks.requests.get', side_effect=[metadata, response]) as request:
            output = Path(temporary)
            (output / 'raw').mkdir()
            get_public_source('betpawa', response.url, output)
            queries = json.loads(request.call_args.kwargs['params']['q'])['queries']
            self.assertEqual([q['query']['zones']['competitions'] for q in queries], [['pl'], ['cl']])
            self.assertEqual([q['take'] for q in queries], [100, 100])

    def test_primary_feed_retries_transport_failure_but_not_access_denial(self):
        denied = Mock(status_code=403)
        request = Mock(side_effect=[requests.ConnectTimeout(), denied])
        with patch('etl.scrape_sportsbooks.time.sleep'):
            self.assertIs(request_primary_source(request, 'https://example.org'), denied)
        self.assertEqual(request.call_count, 2)
        request = Mock(return_value=denied)
        self.assertIs(request_primary_source(request, 'https://example.org'), denied)
        request.assert_called_once()

    def test_primary_feed_transport_retry_is_bounded(self):
        request = Mock(side_effect=requests.ConnectTimeout())
        with patch('etl.scrape_sportsbooks.time.sleep'), self.assertRaises(requests.ConnectTimeout):
            request_primary_source(request, 'https://example.org')
        self.assertEqual(request.call_count, 3)

    def test_regional_inventory_source_keeps_region(self):
        target = {"bookmaker": "betika", "region": "UG", "source_url": "https://www.betika.com/en-ug/s/home.bet"}
        with patch("etl.scrape_sportsbooks.get_public_source", return_value={"snapshots": 0}) as collect:
            row = collect_target(target, Path("capture"))
        collect.assert_called_once_with("betika", "https://api-ug.betika.com/v1/uo/matches", Path("capture"))
        self.assertEqual(row["region"], "UG")

    def test_unresolved_brand_is_reported_without_network(self):
        with patch("etl.scrape_sportsbooks.get_public_source") as collect:
            row = collect_target({"bookmaker": "betvita", "source_url": None}, Path("capture"))
        collect.assert_not_called()
        self.assertEqual(row["status"], "source_verification_pending")
        self.assertEqual(row["snapshots"], 0)

    def test_rejects_unsafe_slug_and_credential_url(self):
        for target in [{"bookmaker": "../raw"},
                       {"bookmaker": "newbook", "source_url": "https://user:password@example.com/"},
                       {"bookmaker": "newbook", "source_url": "http://example.com/"}]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                collect_target(target, Path("capture"))

    def setUp(self):
        self.observed = "2026-10-08T12:00:00Z"
        self.event = {"id": "e1", "type": "GAMEEVENT", "sport": "SOCC", "live": False, "status": "U",
            "startTime": 1791547200000, "competitors": [{"id": "h", "name": "Home", "home": True}, {"id": "a", "name": "Away", "home": False}],
            "displayGroups": [{"markets": [{"id": "m1", "key": "3W-1X2", "status": "O", "period": {"id": "100", "description": "Regulation Time"},
                "outcomes": [{"type": "H", "competitorId": "h", "status": "O", "price": {"decimal": "2.1"}},
                    {"type": "D", "status": "O", "price": {"decimal": "3.2"}},
                    {"type": "A", "competitorId": "a", "status": "O", "price": {"decimal": "3.4"}}]}]}]}

    def parse(self, event):
        return normalize_bovada([{"path": [{"type": "LEAGUE", "id": "l1", "description": "League"}], "events": [event]}], self.observed, "raw/bovada.json", "run1")

    def test_direct_capture_retains_provenance(self):
        record = self.parse(self.event)[0]
        self.assertEqual(record["observed_at"], self.observed)
        self.assertEqual(record["collection_route"], "direct_public_feed")
        self.assertEqual(record["provider_competition_id"], "l1")
        self.assertEqual(record["market_status"], "OPEN")
        self.assertEqual([x["selection"] for x in record["outcomes"]], ["HOME", "DRAW", "AWAY"])

    def test_live_started_and_non_game_events_are_rejected(self):
        for field, value in [("live", True), ("startTime", 1), ("type", "FUTURE")]:
            with self.subTest(field=field):
                event = deepcopy(self.event)
                event[field] = value
                self.assertEqual(self.parse(event), [])

    def test_wrong_period_suspended_or_mismatched_outcomes_are_rejected(self):
        for change in ["period", "suspended", "competitor", "price", "duplicate"]:
            with self.subTest(change=change):
                event = deepcopy(self.event)
                market = event["displayGroups"][0]["markets"][0]
                if change == "period": market["period"]["id"] = "1"
                if change == "suspended": market["outcomes"][0]["status"] = "S"
                if change == "competitor": market["outcomes"][0]["competitorId"] = "wrong"
                if change == "price": market["outcomes"][0]["price"]["decimal"] = "NaN"
                if change == "duplicate": market["outcomes"].append(deepcopy(market["outcomes"][0]))
                self.assertEqual(self.parse(event), [])

    def test_provider_availability_is_unknown_and_incomplete_prices_rejected(self):
        event = {"id": "p1", "sport_key": "soccer_epl", "commence_time": "2026-10-10T12:00:00Z", "home_team": "Home", "away_team": "Away",
            "bookmakers": [{"key": "bovada", "markets": [{"key": "h2h", "outcomes": [{"name": "Home", "price": 2.1}, {"name": "Draw", "price": 3.2}, {"name": "Away", "price": 3.4}]}]}]}
        targets = [{"bookmaker": "bovada", "oddsapi": {"key": "bovada"}}]
        records = normalize_provider_events([event], targets, self.observed, "raw/provider.json", "run1")
        self.assertEqual(records[0]["market_status"], "UNKNOWN")
        self.assertEqual(records[0]["collection_route"], "provider_feed")
        event["bookmakers"][0]["markets"][0]["outcomes"].pop()
        self.assertEqual(normalize_provider_events([event], targets, self.observed, "raw/provider.json", "run1"), [])


if __name__ == "__main__":
    unittest.main()
