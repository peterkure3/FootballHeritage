"""Sport isolation, causal replay and persisted winner model behavior."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from models.sport_data import canonical_games, capture_time
from models.sport_features import FEATURES, HISTORY_FEATURES, build_features, live_features
from models.sport_model import SportWinnerModel
from models.sport_predict import candidate_directory
from models.train_sports import train_sport


def games():
    rows = []
    for i in range(40):
        date = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(days=i)
        rows.append({"date": date, "result_available_at": date + pd.Timedelta(days=1), "completed": True,
            "home_team": "Home", "away_team": "Away", "home_score": 110 if i % 2 else 90,
            "away_score": 100, "league": "basketball_nba"})
    return canonical_games(rows, "basketball")


class SportModelTests(unittest.TestCase):
    def test_cross_sport_and_unfinished_data_are_rejected(self):
        rows = games().to_dict("records")
        rows[0]["league"] = "americanfootball_nfl"
        with self.assertRaises(ValueError): canonical_games(rows, "basketball")
        rows = games().to_dict("records")
        rows[0]["completed"] = False
        with self.assertRaises(ValueError): canonical_games(rows, "basketball")

    def test_final_ties_and_conflicting_scores_are_rejected(self):
        rows = games().to_dict("records")
        rows[0]["home_score"] = 100
        with self.assertRaises(ValueError): canonical_games(rows, "basketball")
        rows = games().to_dict("records")
        duplicate = dict(rows[0], home_score=101)
        with self.assertRaises(ValueError): canonical_games(rows + [duplicate], "basketball")

    def test_future_scores_do_not_change_earlier_vectors_and_live_replays(self):
        frame = games()
        before = build_features(frame, "basketball")
        changed = frame.copy()
        changed.loc[30:, "home_score"] = 200
        after = build_features(changed, "basketball")
        np.testing.assert_allclose(before.iloc[:31], after.iloc[:31])
        live = live_features(frame, "basketball", frame.iloc[20].to_dict())
        np.testing.assert_allclose(live.iloc[0], before.iloc[20])

    def test_delayed_results_and_same_day_games_cannot_update_features(self):
        frame = games()
        frame.loc[0, "result_available_at"] = frame.loc[5, "date"]
        X = build_features(frame, "basketball")
        self.assertEqual(X.iloc[1].home_games, 0)
        self.assertEqual(X.iloc[5].home_games, 5)
        rows = games().iloc[:2].to_dict("records")
        rows[1]["date"] = rows[0]["date"]
        rows[1]["home_team"] = "Third"
        same_day = canonical_games(rows, "basketball")
        self.assertTrue(build_features(same_day, "basketball").away_games.eq(0).all())

    def test_league_history_is_isolated(self):
        rows = games().iloc[:2].to_dict("records")
        rows[1]["league"] = "basketball_ncaab"
        X = build_features(canonical_games(rows, "basketball"), "basketball")
        self.assertEqual(X.iloc[1].home_games, 0)
        self.assertEqual(X.iloc[1].home_scored, 1.)

    def test_baseball_doubleheaders_keep_distinct_provider_ids(self):
        rows = games().iloc[:2].to_dict("records")
        for i, row in enumerate(rows):
            row.update(league="baseball_mlb", date=rows[0]["date"], provider_event_id=str(i))
        self.assertEqual(len(canonical_games(rows, "baseball")), 2)

    def test_legacy_capture_time_waits_for_timezone_uncertainty(self):
        self.assertEqual(capture_time("20260127_121827"), pd.Timestamp("2026-01-29", tz="UTC"))
        with self.assertRaises(ValueError): capture_time("2026-01-27T12:18:27")

    def test_many_games_on_one_day_cannot_pass_readiness(self):
        frame = pd.concat([games().iloc[:1]] * 600, ignore_index=True)
        with patch("models.train_sports.load_games", return_value=frame):
            report = train_sport("basketball", Path("unused"))
        self.assertEqual(report["status"], "insufficient_data")
        self.assertIn("20 distinct", report["reason"])

    def test_candidate_paths_cannot_escape_model_store(self):
        for candidate, sport in [("../outside", "basketball"), ("20261009T100528981075Z", "../../outside")]:
            with self.subTest(candidate=candidate, sport=sport):
                with self.assertRaises(ValueError): candidate_directory(candidate, sport)

    def test_persisted_history_model_ignores_missing_market_fields(self):
        X = build_features(games(), "basketball")
        y = np.arange(len(X)) % 2
        estimator = LogisticRegression(max_iter=1000).fit(X[HISTORY_FEATURES], y)
        model = SportWinnerModel(estimator)
        expected = model.predict_proba(X)
        changed = X.copy()
        changed.loc[:, ["fair_home_prob", "fair_away_prob", "overround"]] = 1000
        np.testing.assert_allclose(expected, model.predict_proba(changed))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.pkl"
            joblib.dump(model, path)
            loaded = joblib.load(path)
            np.testing.assert_allclose(expected, loaded.predict_proba(X))
        with self.assertRaises(ValueError): model.predict_proba(X[FEATURES[::-1]])
