"""Sportsbook imports preserve observations and never manufacture training labels."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from models.data import merge_prematch_odds, normalize_matches
from models.import_sportsbook_odds import import_snapshots, load_imported_odds, normalize_snapshots


def snapshot():
    return {"snapshot_id": "s1", "schema_version": "1.0", "sport": "football", "market": "h2h",
        "period": "FULL_TIME_90_MIN", "settlement_rule": "REGULATION_TIME", "is_live": False,
        "event_status": "SCHEDULED", "market_status": "UNKNOWN", "provider": "oddsapi",
        "collection_route": "provider_feed", "bookmaker": "bovada", "provider_event_id": "e1",
        "home_team": "Home", "away_team": "Away", "raw_capture_ref": "raw/events.json",
        "commence_time": "2026-10-10T12:00:00Z", "observed_at": "2026-10-08T12:00:00Z",
        "source_updated_at": "2026-10-08T11:00:00Z",
        "outcomes": [{"selection": selection, "odds_decimal": price, "status": "UNKNOWN"}
                     for selection, price in [("HOME", 2.1), ("DRAW", 3.2), ("AWAY", 3.4)]]}


class SportsbookImportTests(unittest.TestCase):
    def test_import_is_idempotent_and_checks_stored_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "odds.jsonl"
            source.write_text(json.dumps(snapshot()) + "\n", encoding="utf-8")
            first = import_snapshots(source, root / "imports")
            second = import_snapshots(source, root / "imports")
            self.assertTrue(second["already_imported"])
            frame = load_imported_odds(root / "imports")
            self.assertEqual(len(frame), 1)
            self.assertEqual(frame.iloc[0].observed_at, snapshot()["observed_at"])
            self.assertNotIn("result", frame)
            self.assertNotIn("home_score", frame)
            Path(first["odds_file"]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_imported_odds(root / "imports")

    def test_postkickoff_suspended_and_duplicate_observations_are_rejected(self):
        for field, value in [("observed_at", "2026-10-10T12:00:00Z"), ("market_status", "SUSPENDED"), ("is_live", True)]:
            with self.subTest(field=field):
                record = snapshot()
                record[field] = value
                with self.assertRaises(ValueError):
                    normalize_snapshots([record])
        with self.assertRaises(ValueError):
            normalize_snapshots([snapshot(), deepcopy(snapshot())])

    def test_join_requires_exact_kickoff_and_keeps_unfinished_unlabeled(self):
        offers = normalize_snapshots([snapshot()])
        fixtures = pd.DataFrame([
            {"date": "2026-10-10T12:00:00Z", "home_team": "Home", "away_team": "Away"},
            {"date": "2026-10-09T12:00:00Z", "home_team": "Other", "away_team": "Away", "home_score": 1, "away_score": 0}])
        merged = merge_prematch_odds(fixtures, offers, exact_kickoff=True)
        upcoming = merged[merged.home_team.eq("Home")].iloc[0]
        self.assertTrue(pd.isna(upcoming.result))
        self.assertEqual(upcoming.home_win, 2.1)
        wrong = normalize_matches(fixtures.iloc[:1].assign(date="2026-10-10T13:00:00Z"))
        self.assertTrue(merge_prematch_odds(wrong, offers, exact_kickoff=True).home_win.isna().all())

    def test_source_update_time_cannot_backdate_observation(self):
        record = snapshot()
        record["observed_at"] = "2026-10-10T12:01:00Z"
        with self.assertRaises(ValueError):
            normalize_snapshots([record])


if __name__ == "__main__":
    unittest.main()
