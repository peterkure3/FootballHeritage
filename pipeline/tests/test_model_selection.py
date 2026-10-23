"""Behavioral checks for missing-market routing and chronological model selection."""

import tempfile
from pathlib import Path
import unittest

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.preprocessing import LabelEncoder
from threadpoolctl import threadpool_limits

from models.features import build_feature_frame
from models.selection import fit_odds_aware
from models.validation import chronological_split
from models.backtest import rolling_evaluation
from test_model_pipeline import history


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.X, cls.fixtures = build_feature_frame(history(240))
        cls.encoder = LabelEncoder().fit(["away_win", "draw", "home_win"])
        cls.y = cls.encoder.transform(cls.fixtures.result)
        cls.splits = chronological_split(cls.fixtures.date)
        with threadpool_limits(limits=2):
            cls.model, cls.report = fit_odds_aware(cls.X, cls.y, cls.splits, trees=10)

    def test_missing_market_predictions_ignore_every_odds_feature(self) -> None:
        before = self.X.iloc[self.splits["test"]].copy()
        before["odds_missing"] = 1
        after = before.copy()
        after.iloc[:, :11] = np.arange(11) + 100
        np.testing.assert_allclose(self.model.predict_proba(before), self.model.predict_proba(after))

    def test_each_row_uses_the_correct_calibrated_expert(self) -> None:
        X = self.X.iloc[self.splits["test"]].copy()
        X.loc[X.index[::2], "odds_missing"] = 1
        result = self.model.predict_proba(X)
        missing = X.odds_missing.eq(1)
        np.testing.assert_allclose(result[missing], self.model.history_.predict_proba(X.loc[missing]))
        np.testing.assert_allclose(result[~missing], self.model.market_.predict_proba(X.loc[~missing]))
        np.testing.assert_allclose(result.sum(axis=1), 1)

    def test_test_outcomes_do_not_change_selection_or_predictions(self) -> None:
        changed = self.y.copy()
        changed[self.splits["test"]] = (changed[self.splits["test"]] + 1) % 3
        with threadpool_limits(limits=2):
            model, report = fit_odds_aware(self.X, changed, self.splits, trees=10)
        self.assertEqual(report, self.report)
        np.testing.assert_allclose(model.predict_proba(self.X), self.model.predict_proba(self.X))

    def test_artifact_roundtrip_and_feature_order_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.pkl"
            joblib.dump(self.model, path)
            loaded = joblib.load(path)
            np.testing.assert_allclose(loaded.predict_proba(self.X), self.model.predict_proba(self.X))
        with self.assertRaisesRegex(ValueError, "feature columns"):
            self.model.predict_proba(self.X.iloc[:, ::-1])
        self.assertIsNotNone(clone(self.model))

    def test_market_expert_rejects_period_without_observed_odds(self) -> None:
        X = self.X.copy()
        X.loc[self.splits["tune"], "odds_missing"] = 1
        with self.assertRaisesRegex(ValueError, "observed odds"):
            fit_odds_aware(X, self.y, self.splits, trees=10)

    def test_rolling_selection_uses_separate_future_windows(self) -> None:
        with threadpool_limits(limits=2):
            windows = rolling_evaluation(self.X, self.fixtures, self.encoder, None,
                                         folds=2, strategy="odds-aware", trees=10)
        for window in windows:
            self.assertLess(window["calibration_end"], window["test_start"])
            self.assertIn(window["selection"]["history"]["selected"],
                          window["selection"]["history"]["tuning"])


if __name__ == "__main__":
    unittest.main()
