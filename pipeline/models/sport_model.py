"""Persistable sport winner estimator with explicit missing-odds routing."""

from sklearn.base import BaseEstimator, ClassifierMixin

from models.sport_features import FEATURES, HISTORY_FEATURES


class SportWinnerModel(ClassifierMixin, BaseEstimator):
    def __init__(self, history_model, market_model=None):
        self.history_model = history_model
        self.market_model = market_model
        self.classes_ = history_model.classes_
        self.n_features_in_ = len(FEATURES)

    def predict_proba(self, X):
        if list(X.columns) != FEATURES:
            raise ValueError("Incompatible sport feature schema")
        probabilities = self.history_model.predict_proba(X[HISTORY_FEATURES])
        covered = X.odds_missing.eq(0).to_numpy()
        if self.market_model is not None and covered.any():
            probabilities[covered] = self.market_model.predict_proba(X.loc[covered, FEATURES[:-1]])
        return probabilities

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
