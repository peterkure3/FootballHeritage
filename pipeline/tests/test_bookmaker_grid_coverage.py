import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from api.bookmaker_catalog import bookmaker_catalog
from scripts.sync_bookmaker_grid import capture_cache_rejections, load_grid_snapshots, matched_grid_quotes
from etl.regional_sportsbooks import snapshot


class BookmakerCoverageTests(unittest.TestCase):
    def test_cache_evidence_does_not_make_an_old_response_fresh(self):
        with TemporaryDirectory() as directory:
            capture = Path(directory)
            rows = [
                {'bookmaker':'bovada','http_status':200,'http_audit':[{'observed_at':'2026-10-21T18:00:00Z','headers':{'Age':'500','Date':'Wed, 21 Oct 2026 18:00:00 GMT'}}]},
                {'bookmaker':'ababet','http_status':200,'http_audit':[{'observed_at':'2026-10-21T18:00:00Z','headers':{'Age':None,'Date':'Wed, 21 Oct 2026 18:00:00 GMT'}}]},
                {'bookmaker':'bookmaker','http_status':200,'http_audit':[{'observed_at':'2026-10-21T18:00:00Z','headers':{'Last-Modified':'Wed, 21 Oct 2026 17:30:00 GMT'}}]},
            ]
            (capture/'cache-audit.json').write_text(json.dumps(rows),encoding='utf-8')
            rejected = capture_cache_rejections(capture)
            self.assertEqual(set(rejected), {'bovada','bookmaker'})

    def test_expanded_capture_uses_manifest_dataset_without_losing_original_records(self):
        with TemporaryDirectory() as directory:
            capture = Path(directory)
            (capture / 'odds_snapshots.jsonl').write_text('', encoding='utf-8')
            (capture / 'odds_snapshots_complete.jsonl').write_text('{"snapshot_id":"expanded"}\n', encoding='utf-8')
            (capture / 'normalization_report.json').write_text(json.dumps({'dataset':'odds_snapshots_complete.jsonl'}), encoding='utf-8')
            path, records = load_grid_snapshots(capture)
            self.assertEqual(path.name, 'odds_snapshots_complete.jsonl')
            self.assertEqual(records, [{'snapshot_id':'expanded'}])
            (capture / 'normalization_report.json').write_text(json.dumps({'dataset':'../other.jsonl'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_grid_snapshots(capture)

    def test_reviewed_ucl_names_fill_missing_matches_without_cross_fixture_join(self):
        from datetime import datetime, timezone
        pairs = [
            ('Inter Milano','Shakhtar Donetsk','FC Internazionale Milano','FK Shakhtar Donetsk'),
            ('Bayern Munich','Arsenal','FC Bayern München','Arsenal FC'),
            ('Club Brugge','Lens','Club Brugge KV','Racing Club de Lens'),
            ('Sporting CP','LASK','Sporting Clube de Portugal','LASK Linz'),
            ('Aston Villa','Viking','Aston Villa FC','Viking FK'),
        ]
        fixtures, records = [], []
        for identifier, (home, away, official_home, official_away) in enumerate(pairs, 1):
            fixtures.append({'match_id':identifier,'date':'2026-10-21T19:00:00Z','home_team':official_home,'away_team':official_away,'competition':'UEFA Champions League'})
            records.append(snapshot('ababet', str(identifier), home, away,
                datetime(2026,10,21,19,tzinfo=timezone.utc), '2026-10-21T18:00:00Z',
                'raw/feed.html','run',{'HOME':(2,'1'),'DRAW':(3,'x'),'AWAY':(4,'2')},
                'UEFA Champions League','Europe','Match Result','https://ababet.ug/'))
        linked = matched_grid_quotes(pd.DataFrame(fixtures), records)
        self.assertEqual(set(linked.match_id), set(range(1,6)))
        self.assertEqual(len(linked), 5)
        self.assertTrue(matched_grid_quotes(pd.DataFrame(fixtures).assign(date='2026-10-21T20:00:00Z'), records).empty)
        self.assertEqual(records[0]['home_team'], 'Inter Milano')

    def test_catalog_retains_all_requested_sources_and_regions_without_prices(self):
        books = bookmaker_catalog()
        self.assertEqual(len(books), 46)
        self.assertEqual(len({book['bookmaker'] for book in books}), 46)
        self.assertIn('ababet:UG', {book['bookmaker'] for book in books})
        removed = {'admiralbet', 'betmgm', 'betlion', 'betking',
                   'ballybet', 'bangbet', 'betcoza', 'bet9ja', 'betrivers'}
        self.assertFalse(removed & {book['bookmaker'].split(':')[0] for book in books})
        self.assertIn('betpawa:UG', {book['bookmaker'] for book in books})
        self.assertIn('sportpesa:GLOBAL', {book['bookmaker'] for book in books})
        self.assertIn('cloudbet:GLOBAL', {book['bookmaker'] for book in books})
        self.assertIn('1xbet', {book['bookmaker'] for book in books})
        self.assertIn('goalkings', {book['bookmaker'] for book in books})

    def test_grid_links_champions_league_without_relaxing_identity(self):
        from datetime import datetime, timezone
        record = snapshot('betpawa', '1', 'Home FC', 'Away FC',
            datetime(2026, 10, 14, 19, tzinfo=timezone.utc), '2026-10-13T10:00:00Z',
            'raw/feed.json', 'run', {'HOME': (2, '1'), 'DRAW': (3, 'x'), 'AWAY': (4, '2')},
            'UEFA Champions League', 'International', '1', 'https://www.betpawa.ug/')
        fixtures = pd.DataFrame([{'match_id': 1, 'date': '2026-10-14T19:00:00Z',
            'home_team': 'Home FC', 'away_team': 'Away FC', 'competition': 'UEFA Champions League'}])
        self.assertEqual(len(matched_grid_quotes(fixtures, [record])), 1)
        for field, value in [('competition', 'Premier League'), ('date', '2026-10-14T20:00:00Z'),
                             ('away_team', 'Different FC')]:
            changed = fixtures.copy()
            changed[field] = value
            self.assertTrue(matched_grid_quotes(changed, [record]).empty)
        duplicate = pd.concat([fixtures, fixtures.assign(match_id=2)])
        self.assertTrue(matched_grid_quotes(duplicate, [record]).empty)
