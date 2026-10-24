"""Behavioral checks for missing-market routing and chronological model selection."""

import tempfile
from pathlib import Path
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.preprocessing import LabelEncoder
from threadpoolctl import threadpool_limits

from models.features import build_feature_frame
from models.selection import fit_odds_aware, selection_sample, expert_candidates
from models.training_resources import training_threads
from models.validation import chronological_split
from models.backtest import rolling_evaluation
from test_model_pipeline import history


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Prediction also uses native threads; bound the whole fixture, not only fitting.
        limits = training_threads(2)
        limits.__enter__()
        cls.addClassCleanup(limits.__exit__, None, None, None)
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

    def test_sampling_preserves_classes_order_and_training_boundary(self) -> None:
        train = self.splits["train"]
        sampled = selection_sample(train, self.y, 30)
        self.assertEqual(len(sampled), 30)
        self.assertEqual(len(np.unique(self.y[sampled])), 3)
        self.assertTrue(np.isin(sampled, train).all())
        self.assertTrue((np.diff(sampled) > 0).all())
        np.testing.assert_array_equal(sampled, selection_sample(train, self.y, 30))
        # A cap one below the period size must also work (unlike a stratified train/test split).
        self.assertEqual(len(selection_sample(train, self.y, len(train) - 1)), len(train) - 1)
        with self.assertRaisesRegex(ValueError, "every outcome"):
            selection_sample(train, self.y, 2)

    def test_capped_selection_keeps_full_refit_and_all_progress_stages(self) -> None:
        events = []

        class Recorder:
            @contextmanager
            def step(self, label, samples):
                events.append((label, samples))
                yield

        with threadpool_limits(limits=2):
            model, report = fit_odds_aware(self.X, self.y, self.splits, trees=10,
                                           selection_max_rows=30, progress=Recorder())
        self.assertEqual(len(events), 12)
        for name in ["market", "history"]:
            self.assertEqual(report[name]["selection_samples"], 30)
            self.assertEqual(report[name]["fit_samples"], len(self.splits["train"]) + len(self.splits["tune"]))
            self.assertEqual(report[name]["calibration_samples"], len(self.splits["calibration"]))
        self.assertEqual(sum("fit + tune" in label and samples == 30 for label, samples in events), 8)
        self.assertTrue(np.isfinite(model.predict_proba(self.X)).all())

    def test_solver_settings_apply_to_all_logistic_candidates(self) -> None:
        candidates = expert_candidates(list(self.X.columns), logistic_max_iter=300, logistic_solver="saga")
        for name, candidate in candidates.items():
            if name.startswith("logistic"):
                self.assertEqual(candidate[-1].max_iter, 300)
                self.assertEqual(candidate[-1].solver, "saga")

    def test_explicit_cpu_budget_does_not_launch_physical_core_probe(self) -> None:
        with patch("joblib.externals.loky.backend.context._count_physical_cores",
                   side_effect=AssertionError("Physical-core subprocess must not run")):
            fit_odds_aware(self.X, self.y, self.splits, trees=10, threads=2)


if __name__ == "__main__":
    unittest.main()
