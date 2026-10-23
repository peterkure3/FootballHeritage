"""Independent WNBA and college datasets, historical provenance and neutral sites."""

from copy import deepcopy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from etl.fetch_basketball_history import normalize_events, normalize_schedule
from models.sport_data import canonical_games, load_games
from models.sport_features import SportState, build_features


def espn_event():
    return {"id": "e1", "season": {"year": 2024, "type": 2}, "competitions": [{"date": "2024-06-01T20:00:00Z",
        "neutralSite": True, "status": {"type": {"completed": True}}, "competitors": [
            {"homeAway": "home", "score": "80", "team": {"id": "1", "displayName": "Home"}},
            {"homeAway": "away", "score": "70", "team": {"id": "2", "displayName": "Away"}}]}]}


class BasketballLeagueTests(unittest.TestCase):
    def test_completed_regular_season_only_and_retrieval_is_not_availability(self):
        event = espn_event()
        rows = normalize_events([event], "basketball_wnba", "raw.json")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["result_available_at"], "2024-06-03T00:00:00+00:00")
        self.assertTrue(rows[0]["neutral_site"])
        event["season"]["type"] = 1
        self.assertEqual(normalize_events([event], "basketball_wnba", "raw.json"), [])
        event["season"]["type"] = 2
        event["competitions"][0]["status"]["type"]["completed"] = False
        self.assertEqual(normalize_events([event], "basketball_wnba", "raw.json"), [])

    def test_basketball_league_profiles_reject_cross_gender_or_nba_rows(self):
        rows = normalize_events([espn_event()], "basketball_wnba", "raw.json")
        for model in ["ncaab", "ncaabw", "basketball"]:
            with self.subTest(model=model):
                with self.assertRaises(ValueError): canonical_games(rows, model)
        self.assertEqual(len(canonical_games(rows, "wnba")), 1)

    def test_regular_season_all_star_status_is_not_a_franchise_game(self):
        event = espn_event()
        event["competitions"][0]["type"] = {"abbreviation": "ALLSTAR"}
        self.assertEqual(normalize_events([event], "basketball_wnba", "raw.json"), [])

    def test_neutral_sites_remove_home_advantage(self):
        row = normalize_events([espn_event()], "basketball_wnba", "raw.json")[0]
        frame = canonical_games([row], "wnba")
        X = build_features(frame, "wnba")
        self.assertEqual(X.iloc[0].elo_diff, 0.)
        self.assertEqual(X.iloc[0].home_expected, .5)
        normal = dict(row, neutral_site=False)
        self.assertEqual(SportState("wnba").vector(normal)["elo_diff"], 55.)

    def test_college_release_parser_preserves_season_and_completed_status(self):
        frame = pd.DataFrame([{ "id": 1, "date": "2024-01-01T20:00:00Z", "season": 2024, "season_type": 2,
            "status_type_completed": True, "home_display_name": "Home", "away_display_name": "Away",
            "home_id": 1, "away_id": 2, "home_score": 80, "away_score": 70, "neutral_site": True}])
        rows = normalize_schedule(frame, "basketball_ncaab", "raw.parquet")
        self.assertEqual(rows[0]["collection_scope"], "SEASON_RELEASE")
        self.assertEqual(rows[0]["season"], 2024)
        self.assertTrue(rows[0]["neutral_site"])
        frame.loc[0, "status_type_completed"] = False
        self.assertEqual(normalize_schedule(frame, "basketball_ncaab", "raw.parquet"), [])

    def test_historical_import_checksum_is_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "historical/basketball_leagues/run"
            run.mkdir(parents=True)
            (run / "normalized.jsonl").write_text(json.dumps(normalize_events([espn_event()], "basketball_wnba", "raw.json")[0]), encoding="utf-8")
            (run / "manifest.json").write_text(json.dumps({"normalized_sha256": "invalid"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_games("wnba", root)

    def test_legacy_all_star_capture_is_excluded_from_wnba_loader(self):
        rows = normalize_events([espn_event()], "basketball_wnba", "raw.json")
        exhibition = dict(rows[0], provider_event_id="allstar", home_team="Team USA", away_team="Team WNBA")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_capture(root, "run", rows + [exhibition])
            games = load_games("wnba", root)
            self.assertEqual(len(games), 1)
            self.assertEqual(games.attrs["data_quality"]["all_star_games_excluded"], 1)

    def test_full_college_releases_replace_truncated_annual_samples(self):
        rows = normalize_events([espn_event()], "basketball_ncaab", "raw.json")
        release = dict(rows[0], provider_event_id="release", collection_scope="SEASON_RELEASE")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_capture(root, "sample", rows)
            self.write_capture(root, "season", [release])
            games = load_games("ncaab", root)
            self.assertEqual(games.provider_event_id.tolist(), ["release"])

    @staticmethod
    def write_capture(root, name, rows):
        run = root / "historical/basketball_leagues" / name
        run.mkdir(parents=True)
        path = run / "normalized.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        (run / "manifest.json").write_text(json.dumps({"normalized_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8")
