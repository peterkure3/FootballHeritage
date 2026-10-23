"""Stacking with strictly chronological out-of-fold meta-learner inputs."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from models.validation import forward_folds


class TemporalStackingClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, estimators: list, n_splits: int = 3) -> None:
        self.estimators = estimators
        self.n_splits = n_splits

    def fit(self, X: pd.DataFrame, y: np.ndarray,
            dates: pd.Series = None) -> "TemporalStackingClassifier":
        if dates is None:
            raise ValueError("Chronological stacking requires fixture dates")
        y = np.asarray(y)
        self.classes_ = np.unique(y)
        self.n_features_in_ = X.shape[1]
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        oof, targets = [], []
        for train, valid in forward_folds(dates, self.n_splits):
            if not np.array_equal(np.unique(y[train]), self.classes_):
                raise ValueError("Every forward training fold must contain all outcome classes")
            parts = []
            for _, prototype in self.estimators:
                model = clone(prototype).fit(X.iloc[train], y[train])
                parts.append(model.predict_proba(X.iloc[valid]))
            oof.append(np.hstack(parts + [X.iloc[valid].to_numpy()]))
            targets.append(y[valid])
        if not oof:
            raise ValueError("No usable forward folds")
        self.final_estimator_ = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        self.final_estimator_.fit(np.vstack(oof), np.concatenate(targets))
        self.estimators_ = [(name, clone(model).fit(X, y)) for name, model in self.estimators]
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        check_is_fitted(self, "estimators_")
        parts = [model.predict_proba(X) for _, model in self.estimators_]
        return self.final_estimator_.predict_proba(np.hstack(parts + [np.asarray(X)]))

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
