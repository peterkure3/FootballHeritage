"""Matched scoring uncertainty and paper settlement checks."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from models.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_feature_frame
from models.market_demo import paired_comparison, paper_policy, paper_roi_interval, make_report
from test_model_pipeline import history


class MarketDemoTests(unittest.TestCase):
    def test_identical_forecasts_have_zero_paired_advantage(self) -> None:
        y = np.array([0, 1, 2])
        probabilities = np.full((3, 3), 1 / 3)
        result = paired_comparison(y, probabilities, probabilities,
                                   pd.Series(pd.date_range("2024-01-01", periods=3)), samples=100)
        for name in ["accuracy", "log_loss", "brier_score"]:
            self.assertEqual(result[name]["advantage"], 0)
            self.assertEqual(result[name]["ci95"], [0, 0])
            self.assertFalse(result[name]["positive_ci"])

    def test_paired_scoring_direction_and_day_clusters(self) -> None:
        y = np.array([0, 1, 2])
        model = np.eye(3) * 0.6 + 0.4 / 3
        market = np.full((3, 3), 1 / 3)
        days = pd.Series(["2024-01-01", "2024-01-01", "2024-01-02"])
        result = paired_comparison(y, model, market, days, samples=100)
        self.assertEqual(result["fixture_days"], 2)
        self.assertTrue(result["log_loss"]["positive_ci"])
        self.assertTrue(result["brier_score"]["positive_ci"])
        reversed_result = paired_comparison(y, market, model, days, samples=100)
        self.assertAlmostEqual(reversed_result["log_loss"]["advantage"], -result["log_loss"]["advantage"])

    def test_flat_stake_settlement_and_one_selection_per_fixture(self) -> None:
        probabilities = np.array([[0.6, 0.25, 0.15], [0.15, 0.15, 0.7], [0.25, 0.5, 0.25]])
        odds = np.array([[2, 3, 5], [5, 5, 2], [3, 3, 3]], dtype=float)
        y = np.array([0, 2, 1])
        summary, bets = paper_policy(y, probabilities, odds)
        self.assertEqual(summary["bets"], 3)
        self.assertEqual(summary["profit_units"], 4)
        self.assertAlmostEqual(summary["roi"], 4 / 3)
        losing, changed = paper_policy((y + 1) % 3, probabilities, odds)
        self.assertEqual(losing["profit_units"], -3)
        np.testing.assert_array_equal(bets["picks"], changed["picks"])
        np.testing.assert_array_equal(bets["bet"], changed["bet"])
        interval = paper_roi_interval(bets, pd.Series(pd.date_range("2024-01-01", periods=3)), samples=100)
        self.assertGreater(interval[0], 0)

    def test_margin_adjusted_bookmaker_policy_does_not_invent_positive_ev(self) -> None:
        odds = np.array([[2, 3, 4]], dtype=float)
        market = (1 / odds) / (1 / odds).sum(axis=1)[:, None]
        summary, _ = paper_policy(np.array([0]), market, odds)
        self.assertEqual(summary["bets"], 0)
        self.assertIsNone(summary["roi"])
        with self.assertRaises(ValueError):
            paper_policy(np.array([0]), market, odds, minimum_ev=float("nan"))

    def test_export_retains_all_matched_fixtures_and_checks_frozen_dataset(self) -> None:
        X, fixtures = build_feature_frame(history(90))
        encoder = LabelEncoder().fit(["away_win", "draw", "home_win"])
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500))
        model.fit(X.iloc[:60], encoder.transform(fixtures.iloc[:60].result))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            bundle.mkdir()
            fixtures.to_parquet(bundle / "dataset.parquet", index=False)
            manifest = {"model_version": "2.1.0", "feature_schema_version": FEATURE_SCHEMA_VERSION,
                        "features": FEATURE_NAMES, "classes": list(encoder.classes_),
                        "dataset_sha256": hashlib.sha256((bundle / "dataset.parquet").read_bytes()).hexdigest()}
            (bundle / "metrics_v2.1.0.json").write_text(json.dumps(manifest))
            joblib.dump(model, bundle / "model_v2.1.0.pkl")
            joblib.dump(encoder, bundle / "label_encoder_v2.1.0.pkl")
            result = make_report(bundle, root / "report", samples=100)
            ledger = pd.read_csv(root / "report" / "fixtures.csv")
            self.assertEqual(len(ledger), result["matched_fixtures"])
            self.assertEqual(len(ledger), result["test_fixtures"])
            self.assertTrue((root / "report" / "demo.html").exists())
            with self.assertRaises(FileExistsError):
                make_report(bundle, root / "report", samples=100)
            (bundle / "dataset.parquet").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                make_report(bundle, root / "tampered-report", samples=100)


if __name__ == "__main__":
    unittest.main()
