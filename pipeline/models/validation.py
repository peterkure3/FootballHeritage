"""Date-blocked model selection and probability scoring."""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix


def chronological_split(dates: pd.Series) -> dict[str, np.ndarray]:
    days = pd.to_datetime(dates, utc=True).dt.normalize()
    unique = np.sort(days.unique())
    if len(unique) < 20:
        raise ValueError("Need at least 20 distinct match days for chronological evaluation")
    edges = [unique[int(len(unique) * f)] for f in [0.6, 0.75, 0.85]]
    masks = [days < edges[0], (days >= edges[0]) & (days < edges[1]),
             (days >= edges[1]) & (days < edges[2]), days >= edges[2]]
    return dict(zip(["train", "tune", "calibration", "test"], [np.flatnonzero(m) for m in masks]))


def forward_folds(dates: pd.Series, n_splits: int = 3) -> list[tuple[np.ndarray, np.ndarray]]:
    days = pd.to_datetime(dates, utc=True).dt.normalize()
    blocks = np.array_split(np.sort(days.unique()), n_splits + 1)
    folds = []
    for i in range(1, len(blocks)):
        train = np.flatnonzero(days.isin(np.concatenate(blocks[:i])))
        test = np.flatnonzero(days.isin(blocks[i]))
        if len(train) and len(test):
            folds.append((train, test))
    return folds


def probability_metrics(y: np.ndarray, probabilities: np.ndarray,
                        classes: list[str]) -> dict:
    probabilities = np.asarray(probabilities, dtype=float)
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("Probabilities must be finite and nonnegative")
    if not np.allclose(probabilities.sum(axis=1), 1):
        raise ValueError("Probability rows must sum to one")
    one_hot = np.eye(len(classes))[y]
    bins = {}
    for i, name in enumerate(classes):
        bins[name] = []
        assignments = np.minimum((probabilities[:, i] * 10).astype(int), 9)
        for bucket in range(10):
            mask = assignments == bucket
            if mask.any():
                bins[name].append({"count": int(mask.sum()),
                                  "mean_probability": float(probabilities[mask, i].mean()),
                                  "observed_frequency": float(one_hot[mask, i].mean())})
    return {"samples": len(y), "accuracy": float(accuracy_score(y, probabilities.argmax(axis=1))),
            "log_loss": float(log_loss(y, probabilities, labels=np.arange(len(classes)))),
            "brier_score": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
            "brier_by_class": dict(zip(classes, np.mean((probabilities - one_hot) ** 2, axis=0).tolist())),
            "confusion_matrix": confusion_matrix(y, probabilities.argmax(axis=1), labels=np.arange(len(classes))).tolist(),
            "calibration_bins": bins}
