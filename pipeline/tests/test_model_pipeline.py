"""Behavioral gates for fixture identity, causal features, and model validation."""

from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder

from models.data import canonical_matches, historical_frames, merge_prematch_odds, parse_dates, team_key
from models.features import FEATURE_NAMES, build_feature_frame, build_live_features
from models.ensemble import TemporalStackingClassifier
from models.validation import chronological_split, forward_folds, probability_metrics
from models.import_historical import import_historical
from models.backtest import rolling_evaluation


def history(count: int = 90) -> pd.DataFrame:
    records = []
    for i in range(count):
        hg, ag = [(2, 0), (1, 1), (0, 2)][i % 3]
        records.append(dict(date=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=i),
                            home_team="Arsenal", away_team="Chelsea", home_score=hg,
                            away_score=ag, result=["home_win", "draw", "away_win"][i % 3],
                            home_win=2.4, draw=3.1, away_win=2.9, status="FINISHED"))
    return pd.DataFrame(records)


class DataTests(unittest.TestCase):
    def test_mixed_source_columns_are_coalesced(self) -> None:
        data = history(1)
        data["Date"] = "01/01/2024"
        data["HomeTeam"] = "Arsenal"
        result = canonical_matches([data])
        self.assertEqual(len(result), 1)
        self.assertEqual(result.home_key.iloc[0], "arsenal")

    def test_completed_scores_are_not_replaced_by_partial_snapshots(self) -> None:
        final = history(1)
        partial = final.copy()
        partial["status"] = "IN_PLAY"
        partial[["home_score", "away_score"]] = [0, 0]
        result = canonical_matches([final, partial])
        self.assertEqual(result.home_score.iloc[0], 2)
        self.assertEqual(result.result.iloc[0], "home_win")
        self.assertEqual(result.status.iloc[0], "FINISHED")

    def test_dates_deduplicate_and_preserve_odds(self) -> None:
        raw = history(1)
        raw["date"] = "13/01/2024"
        other = raw.copy()
        other["date"] = "2024-01-13T20:00:00Z"
        other["home_team"] = "Arsenal FC"
        other["home_win"] = np.nan
        combined = canonical_matches([raw, other])
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined.home_win.iloc[0], 2.4)
        self.assertEqual(parse_dates(pd.Series(["03/04/2024", "2024-04-03"])).nunique(), 1)

    def test_invalid_labels_rejected(self) -> None:
        data = history(1)
        data["result"] = "away_win"
        with self.assertRaisesRegex(ValueError, "disagree"):
            canonical_matches([data])

    def test_samples_and_duplicate_source_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history(1).to_csv(root / "league_2324.csv", index=False)
            history(1).to_csv(root / "normalized_league_2324.csv", index=False)
            history(1).to_csv(root / "sample_matches.csv", index=False)
            self.assertEqual(len(historical_frames(root)), 1)

    def test_odds_do_not_cross_fixtures_or_use_postmatch_updates(self) -> None:
        matches = history(2)
        matches["date"] = ["2024-01-01T20:00:00Z", "2024-02-01T20:00:00Z"]
        matches[["home_win", "draw", "away_win"]] = np.nan
        offers = pd.DataFrame([
            dict(home_team="Arsenal FC", away_team="Chelsea", commence_time="2024-01-01T20:00:00Z",
                 updated_at="2024-01-01T18:00:00Z", bookmaker="a", home_win=2, draw=3, away_win=4),
            dict(home_team="Arsenal", away_team="Chelsea", commence_time="2024-01-01T20:00:00Z",
                 updated_at="2024-01-01T21:00:00Z", bookmaker="a", home_win=8, draw=9, away_win=10),
        ])
        result = merge_prematch_odds(matches, offers)
        self.assertEqual(result.home_win.iloc[0], 2)
        self.assertTrue(pd.isna(result.home_win.iloc[1]))

    def test_substring_names_remain_distinct(self) -> None:
        self.assertNotEqual(team_key("Manchester United"), team_key("Manchester"))
        self.assertEqual(team_key("Man City"), team_key("Manchester City FC"))

    def test_licensed_import_preserves_provenance_and_protects_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export.csv"
            history(2).to_csv(source, index=False)
            output = root / "historical"
            result = import_historical(source, "Premier League", "2324", "licensed-provider", output)
            data = canonical_matches(historical_frames(output))
            self.assertEqual(data.data_source.iloc[0], "licensed_import:licensed-provider")
            self.assertEqual(data.competition.iloc[0], "Premier League")
            self.assertTrue(result.exists())
            with self.assertRaises(FileExistsError):
                import_historical(source, "Premier League", "2324", "licensed-provider", output)

    def test_ambiguous_same_day_fixture_gets_no_joined_odds(self) -> None:
        data = history(2)
        data["date"] = "2024-01-01T20:00:00Z"
        data[["home_win", "draw", "away_win"]] = np.nan
        offers = pd.DataFrame([dict(home_team="Arsenal", away_team="Chelsea", bookmaker="a",
                                    commence_time="2024-01-01T20:00:00Z", updated_at="2024-01-01T18:00:00Z",
                                    home_win=2, draw=3, away_win=4)])
        result = merge_prematch_odds(data, offers)
        self.assertTrue(result.home_win.isna().all())


class FeatureTests(unittest.TestCase):
    def test_replay_equals_serving_and_future_does_not_change_features(self) -> None:
        data = history()
        X, fixtures = build_feature_frame(data)
        index = 25
        row = fixtures.iloc[index]
        live = build_live_features(data, row.home_team, row.away_team, row.date, row.to_dict())
        np.testing.assert_allclose(live.iloc[0], X.iloc[index])
        mutated = data.copy()
        mutated.loc[index:, ["home_score", "away_score"]] = [3, 0]
        mutated.loc[index:, "result"] = "home_win"
        changed, _ = build_feature_frame(mutated)
        np.testing.assert_allclose(changed.iloc[:index + 1], X.iloc[:index + 1])

    def test_same_day_results_unavailable(self) -> None:
        data = history(2)
        data["date"] = ["2024-01-01T12:00:00Z", "2024-01-01T20:00:00Z"]
        data.loc[1, "away_team"] = "Everton"
        X, _ = build_feature_frame(data)
        self.assertEqual(X.home_elo.tolist(), [1500, 1500])
        self.assertEqual(X.home_team_wins_last_n.tolist(), [0, 0])

    def test_missing_odds_are_explicit_and_finite(self) -> None:
        data = history(1)
        data["home_win"] = np.inf
        X, _ = build_feature_frame(data)
        self.assertEqual(X.odds_missing.iloc[0], 1)
        self.assertTrue(np.isfinite(X.to_numpy()).all())
        self.assertAlmostEqual(X[["fair_home_prob", "fair_draw_prob", "fair_away_prob"]].iloc[0].sum(), 1)

    def test_unfinished_scores_never_update_history(self) -> None:
        data = history(2)
        data.loc[0, "status"] = "IN_PLAY"
        X, fixtures = build_feature_frame(data)
        self.assertTrue(pd.isna(fixtures.result.iloc[0]))
        self.assertEqual(X.home_elo.iloc[1], 1500)


class EvaluationTests(unittest.TestCase):
    def test_full_rolling_evaluation_separates_fit_calibration_and_test(self) -> None:
        data = history(160)
        X, fixtures = build_feature_frame(data)
        encoder = LabelEncoder().fit(["away_win", "draw", "home_win"])
        factory = lambda: TemporalStackingClassifier([("lr", make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)))])
        windows = rolling_evaluation(X, fixtures, encoder, factory, folds=3)
        self.assertEqual(len(windows), 3)
        for window in windows:
            self.assertLess(window["development_end"], window["calibration_start"])
            self.assertLess(window["calibration_end"], window["test_start"])
            self.assertEqual(window["metrics"]["samples"], 40)

    def test_calibration_bins_cover_every_probability(self) -> None:
        probabilities = np.array([[0.6, 0.3, 0.1], [1, 0, 0], [0.1, 0.1, 0.8]])
        metrics = probability_metrics(np.array([0, 0, 2]), probabilities, ["home", "draw", "away"])
        for bins in metrics["calibration_bins"].values():
            self.assertEqual(sum(bucket["count"] for bucket in bins), 3)
    def test_splits_and_folds_are_strictly_chronological(self) -> None:
        dates = history().date
        splits = chronological_split(dates)
        previous = None
        for indices in splits.values():
            if previous is not None:
                self.assertLess(previous, dates.iloc[indices].min())
            previous = dates.iloc[indices].max()
        for train, valid in forward_folds(dates):
            self.assertLess(dates.iloc[train].max(), dates.iloc[valid].min())

    def test_temporal_estimator_and_frozen_calibration(self) -> None:
        X, fixtures = build_feature_frame(history())
        y = np.arange(len(X)) % 3
        model = TemporalStackingClassifier([("lr", make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)))])
        model.fit(X.iloc[:60], y[:60], fixtures.date.iloc[:60])
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid", cv=2)
        calibrated.fit(X.iloc[60:75], y[60:75])
        metrics = probability_metrics(y[75:], calibrated.predict_proba(X.iloc[75:]), ["away", "draw", "home"])
        self.assertEqual(metrics["samples"], 15)
        self.assertTrue(np.isfinite(metrics["log_loss"]))


if __name__ == "__main__":
    unittest.main()
