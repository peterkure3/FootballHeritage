from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.analyze_champions_league import attach_quotes, match_team


class ChampionsLeagueTests(unittest.TestCase):
    def test_reviewed_identities(self):
        for a, b in [('Fenerbahçe SK', 'Fenerbahce Istanbul'), ('PAE AEK', 'AEK Athens'),
                     ('Real Betis Balompié', 'Real Betis Seville'), ('Sabah FK', 'Sabah Masazir'),
                     ('PSV', 'PSV Eindhoven'), ('Como Calcio', 'Como 1907')]:
            self.assertEqual(match_team(a), match_team(b), (a, b))

    def test_reversed_market_is_excluded_without_swapping_odds(self):
        self.check_market(reverse=True, expected=0)

    def test_fresh_ordinary_market_is_accepted(self):
        self.check_market(reverse=False, expected=3)

    def test_stale_market_is_excluded(self):
        self.check_market(reverse=False, expected=0, age=901)

    def check_market(self, reverse, expected, age=0):
        now = datetime(2026, 11, 4, 14, tzinfo=timezone.utc)
        kickoff = (now + timedelta(hours=3)).isoformat()
        official = [{'provider_match_id': '1', 'home_team': 'Fenerbahçe SK',
                     'away_team': 'Liverpool FC', 'kickoff': kickoff}]
        row = {'bookmaker': 'test', 'competition': 'UEFA Champions League', 'country': 'Europe',
               'home_team': 'Liverpool' if reverse else 'Fenerbahce Istanbul',
               'away_team': 'Fenerbahce Istanbul' if reverse else 'Liverpool',
               'commence_time': kickoff, 'observed_at': (now - timedelta(seconds=age)).isoformat(),
               'market': 'h2h', 'period': 'FULL_TIME_90_MIN', 'settlement_rule': 'REGULATION_TIME',
               'market_status': 'OPEN', 'is_live': False, 'snapshot_id': 'snapshot',
               'outcomes': [{'selection': side, 'status': 'OPEN', 'odds_decimal': price}
                            for side, price in [('HOME', 4), ('DRAW', 3), ('AWAY', 2)]]}
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.analyze_champions_league.capture_cache_rejections', return_value={}):
            path = Path(tmp)
            (path / 'source_report.json').write_text('{"direct_sources": []}')
            (path / 'odds_snapshots.jsonl').write_text(json.dumps(row))
            fixtures, audit = attach_quotes(path, official, now)
            self.assertEqual(len(fixtures[0]['offers']), expected)
            if reverse:
                self.assertEqual(audit['excluded'], {'test:reversed_home_away': 1})


if __name__ == '__main__':
    unittest.main()
