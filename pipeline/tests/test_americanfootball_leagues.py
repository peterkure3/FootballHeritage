"""NFL tie handling, college scope, historical provenance and causal partitions."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from etl.fetch_americanfootball_history import canonical_team_names, normalize_college_schedule, nfl_coverage_audit
from etl.fetch_basketball_history import normalize_events
from models.sport_data import canonical_games, load_games
from models.sport_features import build_features, live_features
from models.train_sports import supervised_splits, train_sport


def nfl_event() -> dict:
    return {"id": "n1", "season": {"year": 2024, "type": 2}, "competitions": [
        {"date": "2024-09-01T20:00:00Z", "type": {"abbreviation": "STD"}, "neutralSite": False,
         "status": {"type": {"completed": True}}, "competitors": [
            {"homeAway": "home", "score": "24", "team": {"id": "1", "displayName": "Home"}},
            {"homeAway": "away", "score": "24", "team": {"id": "2", "displayName": "Away"}}]}]}


def college_record() -> dict:
    return {"game_id": 123, "season": 2024, "season_type_id": 2, "completed": True, "fbs_participant": True,
            "start_date": "2024-09-01T20:00:00Z", "start_time_tbd": False, "home_id": 1, "away_id": 2,
            "home_team": "Home", "away_team": "Away", "home_points": 28., "away_points": 21., "neutral_site": True}


class AmericanFootballLeagueTests(unittest.TestCase):
    def test_independent_nfl_coverage_check_rejects_missing_games(self):
        row = normalize_events([nfl_event()], "americanfootball_nfl", "raw.json", allow_ties=True)[0]
        reference = pd.DataFrame([{"gameday": "2024-09-01", "espn": "n1", "home_score": 24, "away_score": 24}])
        self.assertEqual(nfl_coverage_audit([row], reference, [2024])["missing_games"], 0)
        with self.assertRaisesRegex(ValueError, "missing 1"):
            nfl_coverage_audit([], reference, [2024])

    def test_nfl_training_calibration_and_reload_work_with_ties_in_history(self):
        row = normalize_events([nfl_event()], "americanfootball_nfl", "raw.json", allow_ties=True)[0]
        rows = []
        for i in range(400):
            date = pd.Timestamp("2000-01-01", tz="UTC") + pd.Timedelta(days=7 * i)
            rows.append(row | {"date": date, "result_available_at": date + pd.Timedelta(days=2),
                               "provider_event_id": str(i), "home_score": 24 if i % 10 == 0 else 28 if i % 2 else 14})
        frame = canonical_games(rows, "nfl")
        frame["home_win"], frame["away_win"] = np.nan, np.nan
        with tempfile.TemporaryDirectory() as temp, patch("models.train_sports.load_games", return_value=frame), \
                patch("models.train_sports.attach_moneylines", side_effect=lambda games, sport: games):
            directory = Path(temp) / "nfl"
            report = train_sport("nfl", directory, min_games=200)
            self.assertEqual(report["status"], "candidate")
            self.assertEqual(report["ties_in_history_not_fitted"], 40)
            self.assertEqual(report["probability_basis"], "CONDITIONAL_ON_NO_FINAL_TIE")
            model = joblib.load(directory / "model.pkl")
            probabilities = model.predict_proba(build_features(frame, "nfl"))
            self.assertEqual(probabilities.shape, (400, 2))
            np.testing.assert_allclose(probabilities.sum(axis=1), 1)

    def test_nfl_ties_are_preserved_only_with_explicit_tie_permission(self):
        event = nfl_event()
        self.assertEqual(normalize_events([event], "americanfootball_nfl", "raw.json"), [])
        rows = normalize_events([event], "americanfootball_nfl", "raw.json", allow_ties=True)
        self.assertEqual(canonical_games(rows, "nfl").result.tolist(), ["draw"])
        self.assertEqual(rows[0]["result_available_at"], "2024-09-03T00:00:00+00:00")
        with self.assertRaises(ValueError):
            canonical_games(rows, "ncaaf")
        event["competitions"][0]["type"]["abbreviation"] = "ALLSTAR"
        self.assertEqual(normalize_events([event], "americanfootball_nfl", "raw.json", allow_ties=True), [])

    def test_college_parser_excludes_unfinished_lower_division_and_exhibitions(self):
        row = college_record()
        parsed = normalize_college_schedule(pd.DataFrame([row]), "raw.parquet")
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0]["neutral_site"])
        for changes in [{"completed": False}, {"fbs_participant": False}, {"season_type_id": 1},
                        {"season_type_id": 4}, {"home_points": np.nan}, {"home_points": -1}, {"home_points": 1.5}]:
            self.assertEqual(normalize_college_schedule(pd.DataFrame([row | changes]), "raw.parquet"), [])
        with self.assertRaisesRegex(ValueError, "tied final"):
            normalize_college_schedule(pd.DataFrame([row | {"home_points": 21.}]), "raw.parquet")

    def test_team_renames_follow_identity_without_merging_other_teams(self):
        rows = normalize_events([nfl_event()], "americanfootball_nfl", "raw.json", allow_ties=True)
        newer = deepcopy(rows[0])
        newer.update(date="2025-09-01T20:00:00+00:00", home_team="Renamed Home")
        result = canonical_team_names(rows + [newer])
        self.assertEqual(result[0]["home_team"], "Renamed Home")
        self.assertEqual(result[0]["source_home_team"], "Home")
        self.assertEqual(result[0]["away_team"], "Away")

    def test_nfl_and_college_histories_cannot_mix(self):
        rows = normalize_college_schedule(pd.DataFrame([college_record()]), "raw.parquet")
        with self.assertRaises(ValueError):
            canonical_games(rows, "nfl")
        self.assertEqual(len(canonical_games(rows, "ncaaf")), 1)

    def test_ties_update_history_but_never_receive_winner_labels(self):
        rows = []
        for i in range(60):
            row = normalize_events([nfl_event()], "americanfootball_nfl", "raw.json", allow_ties=True)[0]
            date = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=i * 7)
            row.update(date=date, result_available_at=date + pd.Timedelta(days=2), provider_event_id=str(i),
                       home_score=24 if i % 10 == 0 else 28 if i % 2 else 14)
            rows.append(row)
        frame = canonical_games(rows, "nfl")
        features = build_features(frame, "nfl")
        self.assertEqual(features.iloc[1].home_games, 1)
        splits, exclusions = supervised_splits(frame, "nfl")
        self.assertTrue(all(frame.iloc[index].result.ne("draw").all() for index in splits.values()))
        self.assertEqual(sum(value["unmodeled_outcomes"] for value in exclusions.values()), 6)
        np.testing.assert_allclose(features.iloc[20], live_features(frame, "nfl", frame.iloc[20].to_dict()).iloc[0])
        changed = frame.copy()
        changed.loc[30:, "home_score"] = 100
        np.testing.assert_allclose(features.iloc[:31], build_features(changed, "nfl").iloc[:31])

    def test_training_labels_available_only_before_next_partition(self):
        rows = []
        for i in range(100):
            row = normalize_college_schedule(pd.DataFrame([college_record()]), "raw.parquet")[0]
            date = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=i)
            row.update(date=date, result_available_at=date + pd.Timedelta(days=2), provider_event_id=str(i))
            rows.append(row)
        frame = canonical_games(rows, "ncaaf")
        splits, exclusions = supervised_splits(frame, "ncaaf")
        for name, boundary in [("train", 60), ("tune", 75), ("calibration", 85)]:
            self.assertTrue(frame.iloc[splits[name]].result_available_at.lt(frame.iloc[boundary].date).all())
            self.assertEqual(exclusions[name]["labels_unavailable_at_next_partition"], 2)

    def test_loader_requires_checksums_and_excludes_future_available_results(self):
        rows = normalize_college_schedule(pd.DataFrame([college_record()]), "raw.parquet")
        future = dict(rows[0], provider_event_id="future", result_available_at="2099-01-01T00:00:00Z")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "historical/americanfootball_leagues/run"
            run.mkdir(parents=True)
            path = run / "normalized.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows + [future]), encoding="utf-8")
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps({"normalized_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))
            self.assertEqual(len(load_games("ncaaf", root)), 1)
            path.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_games("ncaaf", root)
