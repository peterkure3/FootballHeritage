import unittest
from unittest.mock import patch
import json
import tempfile
from pathlib import Path
import requests
from etl import march_madness as mm


def event(event_id="1", headline="NCAA Men's Basketball Championship - East Region - 1st Round", completed=True):
    return {"id": event_id, "date": "2026-03-19T12:00Z", "competitions": [{
        "notes": [{"headline": headline}], "status": {"type": {"completed": completed, "state": "post" if completed else "pre"}},
        "competitors": [{"team": {"id": str(i), "shortDisplayName": name}, "curatedRank": {"current": seed}, "score": score, "winner": i == 1}
                        for i, name, seed, score in [(1, "Team A", 1, "80"), (2, "Team B", 16, "70")]]}]}


class BracketTests(unittest.TestCase):
    def test_only_ncaa_championship_games(self):
        self.assertIsNone(mm.normalize_event(event(headline="NIT - 1st Round")))
        normalized = mm.normalize_event(event())
        self.assertEqual(normalized["region"], "East")
        self.assertEqual(normalized["round"], "Round of 64")
        self.assertEqual(normalized["teams"][0]["seed"], 1)
        self.assertEqual(normalized["teams"][0]["score"], 80)
        self.assertTrue(normalized["teams"][0]["winner"])

    def test_upcoming_has_no_score_or_winner(self):
        normalized = mm.normalize_event(event(completed=False))
        self.assertEqual(normalized["status"], "upcoming")
        self.assertIsNone(normalized["teams"][0]["score"])
        self.assertFalse(normalized["teams"][0]["winner"])

    def test_deduplication_champion_and_region_retention(self):
        final = event("2", "NCAA Men's Basketball Championship - National Championship")
        final["date"] = "2026-04-07T00:00Z"
        data = mm.build_bracket([event(), event(), final], 2026)
        self.assertEqual(len(data["games"]), 2)
        self.assertEqual(len(data["teams"]), 2)
        self.assertEqual(data["champion"]["name"], "Team A")
        self.assertEqual(data["teams"][0]["region"], "East")

    def test_unknown_round_rejected(self):
        with self.assertRaises(ValueError):
            mm.normalize_event(event(headline="NCAA Men's Basketball Championship - Mystery Round"))

    def test_failed_refresh_preserves_snapshot_time(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mm, "DATA_DIR", Path(folder)):
            cached = mm.build_bracket([event()], 2026)
            path = Path(folder) / "2026.json"
            path.write_text(json.dumps(cached), encoding="utf-8")
            with patch.object(mm, "fetch_bracket", side_effect=requests.RequestException("offline")):
                data = mm.get_bracket(2026, refresh=True)
            self.assertTrue(data["stale"])
            self.assertEqual(data["fetched_at"], cached["fetched_at"])
            self.assertEqual(json.loads(path.read_text())["fetched_at"], cached["fetched_at"])


if __name__ == "__main__":
    unittest.main()
