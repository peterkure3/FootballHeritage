from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from scripts.export_market_report import analyze, explicit_ev, write_report
from scripts.report_soccer_markets import render


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, 22, 0, tzinfo=timezone.utc)
        self.snapshot = {'snapshot_at': self.now.isoformat(), 'fixtures': [], 'source_errors': []}

    def test_timezone_date_and_empty_market_render(self):
        result = analyze(self.snapshot, self.now)
        self.assertEqual(result['date'], '2026-11-05')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'report'
            write_report(result, output)
            self.assertIn('No eligible', (output / 'report.md').read_text())
            self.assertEqual(len((output / 'picks.csv').read_text().splitlines()), 1)
            self.assertEqual(json.loads((output / 'analysis.json').read_text())['source_errors'], [])
            with self.assertRaises(FileExistsError):
                write_report(result, output)

    def test_stale_and_future_snapshots_are_rejected(self):
        for delta in (-1801, 1):
            self.snapshot['snapshot_at'] = (self.now + timedelta(seconds=delta)).isoformat()
            with self.assertRaises(ValueError):
                analyze(self.snapshot, self.now)

    def test_ev_fraction_has_explicit_units(self):
        market = {'ev_bets': [{'probability': .6, 'decimal_odds': 2, 'ev_pct': .2}], 'ai_picks': []}
        explicit_ev(market)
        self.assertEqual(market['ev_bets'][0]['gross_ev_pct'], 20)
        self.assertNotIn('ev_pct', market['ev_bets'][0])
        with self.assertRaises(ValueError):
            explicit_ev({'ev_bets': [{'probability': .6, 'decimal_odds': 2, 'ev_pct': 20}], 'ai_picks': []})

    def test_partial_source_failures_remain_visible(self):
        self.snapshot['source_errors'] = [{'source': 'provider', 'reason': 'unavailable'}]
        self.assertEqual(analyze(self.snapshot, self.now)['source_errors'], self.snapshot['source_errors'])

    def test_soccer_renderer_handles_empty_days_without_dated_claims(self):
        payload = {'fixtures': [], 'date_eat': '2026-11-05', 'generated_at': self.now.isoformat(),
                   'policy': {'max_quote_age_seconds': 900}, 'capture': 'capture',
                   'capture_sha256': 'hash', 'form_capture': 'form', 'form_sha256': 'hash', 'exclusions': {}}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'analysis.json').write_text(json.dumps(payload))
            render(directory)
            text = (directory / 'report.md').read_text(encoding='utf-8')
            self.assertIn('0 of 0 fixtures', text)
            self.assertNotIn('Liverpool', text)
            self.assertNotIn('20261101', text)
            self.assertEqual(len((directory / 'markets.csv').read_text().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
