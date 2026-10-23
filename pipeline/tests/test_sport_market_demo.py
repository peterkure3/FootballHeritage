"""Quote-time causality, exact identities and two-way comparison behavior."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from models.market_demo import paired_comparison, paper_policy
from models.sport_data import canonical_games
from models.sport_features import live_features
from models.sport_market_demo import matched_offers, observation_bounds, team_aliases


class SportMarketDemoTests(unittest.TestCase):
    def test_unknown_capture_timezone_is_bounded_without_backdating_quote(self):
        earliest, latest, precision = observation_bounds("20260910_153226")
        self.assertEqual(earliest, pd.Timestamp("2026-09-10T01:32:26Z"))
        self.assertEqual(latest, pd.Timestamp("2026-09-11T03:32:26Z"))
        self.assertEqual(precision, "UNKNOWN_TIMEZONE_BOUNDED")
        exact = observation_bounds("2026-09-10T15:32:26+03:00")
        self.assertEqual(exact[0], exact[1])
        with self.assertRaises(ValueError):
            observation_bounds("2026-09-10T15:32:26")

    def test_two_way_probability_scoring_and_paper_policy(self):
        y = np.array([0, 1])
        model = np.array([[.8, .2], [.2, .8]])
        market = np.full((2, 2), .5)
        comparison = paired_comparison(y, model, market, pd.Series(["2025-01-01", "2025-01-02"]), samples=100, classes=["away_win", "home_win"])
        self.assertGreater(comparison["log_loss"]["advantage"], 0)
        summary, bets = paper_policy(y, model, np.full((2, 2), 1.9), classes=["away_win", "home_win"])
        self.assertAlmostEqual(summary["profit_units"], 1.8)
        self.assertEqual(bets["picks"].tolist(), [0, 1])

    def test_prediction_history_stops_at_quote_observation(self):
        rows = []
        for i in range(5):
            date = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(days=i)
            rows.append({"date": date, "result_available_at": date + pd.Timedelta(days=1), "league": "basketball_nba",
                         "home_team": "Home", "away_team": "Away", "home_score": 100, "away_score": 90, "completed": True})
        history = canonical_games(rows, "basketball")
        game = dict(rows[-1], date="2025-01-10T20:00:00Z")
        earlier = live_features(history, "basketball", game, as_of="2025-01-03T12:00:00Z")
        self.assertEqual(earlier.iloc[0].home_games, 2)
        changed = history.copy()
        changed.loc[2:, "home_score"] = 500
        np.testing.assert_allclose(earlier, live_features(changed, "basketball", game, as_of="2025-01-03T12:00:00Z"))

    def test_team_directory_requires_unambiguous_provider_id_mapping(self):
        frame = pd.DataFrame([{"home_key": "alabama", "away_key": "georgia", "provider_home_team_id": "1", "provider_away_team_id": "2"}])
        directory = {"sports": [{"leagues": [{"teams": [
            {"team": {"id": "1", "displayName": "Alabama Crimson Tide", "shortDisplayName": "Ambiguous"}},
            {"team": {"id": "2", "displayName": "Georgia Bulldogs", "shortDisplayName": "Ambiguous"}}]}]}]}
        aliases = team_aliases(frame, directory)
        self.assertEqual(aliases["alabama crimson tide"], "alabama")
        self.assertNotIn("ambiguous", aliases)

    def test_offers_keep_one_synchronized_capture_and_exact_fixture(self):
        games = pd.DataFrame([{"date": pd.Timestamp("2025-01-10T20:00:00Z"), "home_key": "home", "away_key": "away", "date_precision": "TIMESTAMP"}], index=[7])
        event = {"id": "p1", "sport_key": "basketball_nba", "commence_time": "2025-01-10T20:00:00Z",
                 "home_team": "Home", "away_team": "Away", "bookmakers": [
                     {"key": "book1", "last_update": "2025-01-01T00:00:00Z", "markets": [
                         {"key": "h2h", "outcomes": [{"name": "Home", "price": 2}, {"name": "Away", "price": 2.1}]}]}]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "the_odds_api"
            folder.mkdir()
            for capture, timestamp in [("a", "2025-01-01T12:00:00Z"), ("b", "2025-01-02T12:00:00Z"), ("c", "2025-01-10T21:00:00Z")]:
                (folder / f"odds_basketball_nba_{capture}.json").write_text(json.dumps({"fetched_at": timestamp, "events": [event]}))
            offers, audit = matched_offers(games, "basketball_nba", {"home": "home", "away": "away"}, root)
            self.assertEqual(len(offers), 1)
            self.assertEqual(offers.fixture_index.iloc[0], 7)
            self.assertTrue(offers.source_file.iloc[0].endswith("_b.json"))
            self.assertEqual(audit["counts"]["not_certainly_pregame"], 1)
            uncertain = games.copy()
            uncertain.loc[7, "date_precision"] = "DAY"
            self.assertTrue(matched_offers(uncertain, "basketball_nba", {"home": "home", "away": "away"}, root)[0].empty)

    def test_stable_provider_id_handles_tipoff_change_with_exact_teams(self):
        provider_id = "a" * 32
        games = pd.DataFrame([{"date": pd.Timestamp("2025-01-10T20:12:00Z"), "home_key": "home", "away_key": "away",
                               "date_precision": "TIMESTAMP", "provider_event_id": provider_id}])
        event = {"id": provider_id, "sport_key": "basketball_nba", "commence_time": "2025-01-10T20:10:00Z",
                 "home_team": "Home", "away_team": "Away", "bookmakers": [
                     {"key": "book1", "last_update": "2025-01-01T00:00:00Z", "markets": [
                         {"key": "h2h", "outcomes": [{"name": "Home", "price": 2}, {"name": "Away", "price": 2.1}]}]}]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "the_odds_api"
            folder.mkdir()
            path = folder / "odds_basketball_nba_test.json"
            path.write_text(json.dumps({"fetched_at": "2025-01-09T12:00:00Z", "events": [event]}))
            offers, _ = matched_offers(games, "basketball_nba", {"home": "home", "away": "away"}, root)
            self.assertEqual(len(offers), 1)
            self.assertEqual(offers.identity_method.iloc[0], "EXACT_PROVIDER_EVENT_ID_AND_TEAMS")
            changed = games.copy()
            changed.loc[0, "home_key"] = "other"
            self.assertTrue(matched_offers(changed, "basketball_nba", {"home": "home", "away": "away"}, root)[0].empty)
