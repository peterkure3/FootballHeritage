"""Select and calibrate separate market and history experts without test labels."""

from contextlib import nullcontext

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from models.features import FEATURE_NAMES
from models.validation import probability_metrics
from models.training_resources import training_threads


class OddsAwareClassifier(ClassifierMixin, BaseEstimator):
    """Route missing markets to an expert trained without any odds features."""

    def __init__(self, market: BaseEstimator, history: BaseEstimator) -> None:
        self.market = market
        self.history = history

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "OddsAwareClassifier":
        self.market_ = clone(self.market).fit(X, y)
        self.history_ = clone(self.history).fit(X, y)
        self._set_contract(X)
        return self

    def _set_contract(self, X: pd.DataFrame) -> None:
        if not np.array_equal(self.market_.classes_, self.history_.classes_):
            raise ValueError("Expert outcome classes differ")
        self.classes_ = self.history_.classes_
        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        check_is_fitted(self, "history_")
        if list(X.columns) != list(self.feature_names_in_):
            raise ValueError("Prediction feature columns differ from training")
        available = X.odds_missing.eq(0).to_numpy()
        result = np.empty((len(X), len(self.classes_)))
        for mask, expert in [(available, self.market_), (~available, self.history_)]:
            if mask.any():
                result[mask] = expert.predict_proba(X.iloc[np.flatnonzero(mask)])
        return result

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def expert_candidates(columns: list[str], trees: int = 200,
                      logistic_max_iter: int = 2000, logistic_solver: str = "lbfgs") -> dict[str, BaseEstimator]:
    candidates = {
        f"logistic_C_{strength}": make_pipeline(
            ColumnTransformer([("features", StandardScaler(), columns)]),
            LogisticRegression(C=strength, max_iter=logistic_max_iter,
                               solver=logistic_solver, random_state=42),
        ) for strength in [0.01, 0.1, 1.0]
    }
    candidates["hist_gradient"] = make_pipeline(
        ColumnTransformer([("features", "passthrough", columns)]),
        HistGradientBoostingClassifier(max_iter=trees, max_leaf_nodes=15,
                                       min_samples_leaf=30, l2_regularization=10,
                                       early_stopping=False, random_state=42),
    )
    return candidates


def selection_sample(indices: np.ndarray, y: np.ndarray, limit: int = None) -> np.ndarray:
    """Deterministic class-proportional sample from the training period only."""
    if limit is None or len(indices) <= limit:
        return indices
    classes, counts = np.unique(y[indices], return_counts=True)
    if limit < len(classes):
        raise ValueError("Selection row limit must allow every outcome class")
    allocation = np.maximum(1, np.floor(counts * limit / len(indices)).astype(int))
    while allocation.sum() > limit:
        allocation[np.argmax(allocation)] -= 1
    while allocation.sum() < limit:
        allocation[np.argmax(counts * limit / len(indices) - allocation)] += 1
    rng = np.random.default_rng(42)
    selected = np.concatenate([rng.choice(indices[y[indices] == label], size=size, replace=False)
                               for label, size in zip(classes, allocation)])
    # Retain original chronological order even if source indices are not contiguous.
    return indices[np.isin(indices, selected)]


def fit_odds_aware(X: pd.DataFrame, y: np.ndarray, splits: dict[str, np.ndarray],
                   trees: int = 200, *, progress=None, selection_max_rows: int = None,
                   logistic_max_iter: int = 2000,
                   logistic_solver: str = "lbfgs", threads: int = 2) -> tuple[OddsAwareClassifier, dict]:
    """Apply an explicit CPU budget before entering any blocking estimator fit."""
    with training_threads(threads):
        return _fit_odds_aware(X, y, splits, trees, progress=progress,
                              selection_max_rows=selection_max_rows,
                              logistic_max_iter=logistic_max_iter,
                              logistic_solver=logistic_solver)


def _fit_odds_aware(X: pd.DataFrame, y: np.ndarray, splits: dict[str, np.ndarray],
                    trees: int = 200, *, progress=None, selection_max_rows: int = None,
                    logistic_max_iter: int = 2000,
                    logistic_solver: str = "lbfgs") -> tuple[OddsAwareClassifier, dict]:
    """Select on tuning data, refit development, calibrate on a separate period."""
    train, tune, calibration = [splits[name] for name in ["train", "tune", "calibration"]]
    for indices in [train, tune, calibration]:
        if len(np.unique(y[indices])) != 3:
            raise ValueError("Expert selection periods require all outcome classes")
    development = np.concatenate([train, tune])
    experts, report = {}, {}
    observed_odds = X.odds_missing.eq(0).to_numpy()
    history_columns = FEATURE_NAMES[FEATURE_NAMES.index("home_elo"):FEATURE_NAMES.index("odds_missing")]
    for name, columns in [("market", FEATURE_NAMES), ("history", history_columns)]:
        # Missing market priors must not teach the market expert fabricated prices.
        fit_indices = train[observed_odds[train]] if name == "market" else train
        tuning = tune[observed_odds[tune]] if name == "market" else tune
        refit = development[observed_odds[development]] if name == "market" else development
        calibrate = calibration[observed_odds[calibration]] if name == "market" else calibration
        if any(len(np.unique(y[indices])) != 3 for indices in [fit_indices, tuning, refit, calibrate]):
            raise ValueError("Market expert needs observed odds and all classes in each period")
        sampled = selection_sample(fit_indices, y, selection_max_rows)
        candidates = expert_candidates(columns, trees, logistic_max_iter, logistic_solver)
        # Reuse these slices across candidates rather than copying the corpus four times.
        fit_X, fit_y = X.iloc[sampled], y[sampled]
        tune_X, tune_y = X.iloc[tuning], y[tuning]
        step = progress.step if progress is not None else lambda *_: nullcontext()
        scores = {}
        for label, candidate in candidates.items():
            with step(f"{name}/{label}: fit + tune", len(sampled)):
                candidate.fit(fit_X, fit_y)
                scores[label] = probability_metrics(tune_y, candidate.predict_proba(tune_X),
                                                    ["away_win", "draw", "home_win"])
        winner = min(scores, key=lambda label: scores[label]["log_loss"])
        del fit_X, fit_y, tune_X, tune_y
        with step(f"{name}/{winner}: full development refit", len(refit)):
            model = clone(candidates[winner]).fit(X.iloc[refit], y[refit])
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid", cv=2)
        with step(f"{name}: calibration", len(calibrate)):
            calibrated.fit(X.iloc[calibrate], y[calibrate])
        experts[name] = calibrated
        report[name] = {"selected": winner, "features": columns, "tuning": scores,
                        "fit_samples": len(refit), "calibration_samples": len(calibrate),
                        "selection_samples": len(sampled)}
    result = OddsAwareClassifier(experts["market"], experts["history"])
    result.market_, result.history_ = experts["market"], experts["history"]
    result._set_contract(X)
    return result, report
