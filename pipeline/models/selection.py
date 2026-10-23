"""Select and calibrate separate market and history experts without test labels."""

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


def expert_candidates(columns: list[str], trees: int = 200) -> dict[str, BaseEstimator]:
    candidates = {
        f"logistic_C_{strength}": make_pipeline(
            ColumnTransformer([("features", StandardScaler(), columns)]),
            LogisticRegression(C=strength, max_iter=2000, random_state=42),
        ) for strength in [0.01, 0.1, 1.0]
    }
    candidates["hist_gradient"] = make_pipeline(
        ColumnTransformer([("features", "passthrough", columns)]),
        HistGradientBoostingClassifier(max_iter=trees, max_leaf_nodes=15,
                                       min_samples_leaf=30, l2_regularization=10,
                                       early_stopping=False, random_state=42),
    )
    return candidates


def fit_odds_aware(X: pd.DataFrame, y: np.ndarray, splits: dict[str, np.ndarray],
                   trees: int = 200) -> tuple[OddsAwareClassifier, dict]:
    """Select on tuning data, refit development, calibrate on a separate period."""
    train, tune, calibration = [splits[name] for name in ["train", "tune", "calibration"]]
    for indices in [train, tune, calibration]:
        if len(np.unique(y[indices])) != 3:
            raise ValueError("Expert selection periods require all outcome classes")
    development = np.concatenate([train, tune])
    experts, report = {}, {}
    history_columns = FEATURE_NAMES[FEATURE_NAMES.index("home_elo"):FEATURE_NAMES.index("odds_missing")]
    for name, columns in [("market", FEATURE_NAMES), ("history", history_columns)]:
        # Missing market priors must not teach the market expert fabricated prices.
        fit_indices = train[X.iloc[train].odds_missing.eq(0).to_numpy()] if name == "market" else train
        tuning = tune[X.iloc[tune].odds_missing.eq(0).to_numpy()] if name == "market" else tune
        refit = development[X.iloc[development].odds_missing.eq(0).to_numpy()] if name == "market" else development
        calibrate = calibration[X.iloc[calibration].odds_missing.eq(0).to_numpy()] if name == "market" else calibration
        if any(len(np.unique(y[indices])) != 3 for indices in [fit_indices, tuning, refit, calibrate]):
            raise ValueError("Market expert needs observed odds and all classes in each period")
        candidates = expert_candidates(columns, trees)
        scores = {}
        for label, candidate in candidates.items():
            candidate.fit(X.iloc[fit_indices], y[fit_indices])
            scores[label] = probability_metrics(y[tuning], candidate.predict_proba(X.iloc[tuning]),
                                                ["away_win", "draw", "home_win"])
        winner = min(scores, key=lambda label: scores[label]["log_loss"])
        model = clone(candidates[winner]).fit(X.iloc[refit], y[refit])
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid", cv=2)
        calibrated.fit(X.iloc[calibrate], y[calibrate])
        experts[name] = calibrated
        report[name] = {"selected": winner, "features": columns, "tuning": scores,
                        "fit_samples": len(refit), "calibration_samples": len(calibrate)}
    result = OddsAwareClassifier(experts["market"], experts["history"])
    result.market_, result.history_ = experts["market"], experts["history"]
    result._set_contract(X)
    return result, report
