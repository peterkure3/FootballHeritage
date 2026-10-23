"""Rolling future-period evaluation with separate selection and calibration."""

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import LabelEncoder
from threadpoolctl import threadpool_limits

sys.path.append(str(Path(__file__).parent.parent))
from models.features import build_feature_frame
from models.validation import forward_folds, probability_metrics
from models.selection import fit_odds_aware


def rolling_evaluation(X: pd.DataFrame, fixtures: pd.DataFrame, encoder: LabelEncoder,
                       model_factory: Callable, folds: int = 3,
                       strategy: str = "stacking", trees: int = 200, threads: int = 2) -> list[dict]:
    results = []
    y = encoder.transform(fixtures.result)
    for train, test in forward_folds(fixtures.date, folds):
        days = np.sort(fixtures.iloc[train].date.dt.normalize().unique())
        if len(days) < 20:
            raise ValueError("Each rolling training window needs at least 20 fixture days")
        boundary = days[int(len(days) * 0.8)]
        calibration_mask = fixtures.iloc[train].date.dt.normalize().ge(boundary).to_numpy()
        development, calibration = train[~calibration_mask], train[calibration_mask]
        if len(np.unique(y[development])) != 3 or len(np.unique(y[calibration])) != 3:
            raise ValueError("Rolling fit and calibration periods require all classes")
        selection = None
        if strategy == "odds-aware":
            tune_boundary = days[int(len(days) * 0.6)]
            tuning_mask = fixtures.iloc[development].date.dt.normalize().ge(tune_boundary).to_numpy()
            splits = {"train": development[~tuning_mask], "tune": development[tuning_mask],
                      "calibration": calibration}
            with threadpool_limits(limits=threads):
                calibrated, selection = fit_odds_aware(X, y, splits, trees)
        elif strategy == "stacking":
            model = model_factory()
            model.fit(X.iloc[development], y[development], dates=fixtures.iloc[development].date)
            calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid", cv=2)
            calibrated.fit(X.iloc[calibration], y[calibration])
        else:
            raise ValueError(f"Unknown model strategy: {strategy}")
        probabilities = calibrated.predict_proba(X.iloc[test])
        covered = X.iloc[test].odds_missing.eq(0).to_numpy()
        market = None
        if covered.any():
            market = {"model": probability_metrics(y[test][covered], probabilities[covered], list(encoder.classes_)),
                      "market": probability_metrics(y[test][covered], X.iloc[test][["fair_away_prob", "fair_draw_prob", "fair_home_prob"]].to_numpy()[covered], list(encoder.classes_))}
        results.append({"development_end": fixtures.iloc[development].date.max().isoformat(),
                        "calibration_start": fixtures.iloc[calibration].date.min().isoformat(),
                        "calibration_end": fixtures.iloc[calibration].date.max().isoformat(),
                        "test_start": fixtures.iloc[test].date.min().isoformat(),
                        "test_end": fixtures.iloc[test].date.max().isoformat(),
                        "metrics": probability_metrics(y[test], probabilities, list(encoder.classes_)),
                        "selection": selection,
                        "metrics_without_odds": probability_metrics(y[test][~covered], probabilities[~covered], list(encoder.classes_)) if (~covered).any() else None,
                        "market_comparison": market})
    return results


def main() -> None:
    from models.train_model_v2 import load_training_data, create_ensemble_model
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trees", type=int, default=200)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strategy", choices=["odds-aware", "stacking"], default="odds-aware")
    args = parser.parse_args()
    if args.trees < 10 or args.threads < 1 or args.folds < 2:
        parser.error("Require >=10 trees, >=1 thread, and >=2 folds")
    X, fixtures = build_feature_frame(load_training_data())
    complete = fixtures.result.notna()
    X, fixtures = X.loc[complete].reset_index(drop=True), fixtures.loc[complete].reset_index(drop=True)
    encoder = LabelEncoder().fit(["away_win", "draw", "home_win"])
    results = rolling_evaluation(X, fixtures, encoder,
                                 lambda: create_ensemble_model(args.trees, args.threads), args.folds,
                                 args.strategy, args.trees, args.threads)
    report = {"parameters": vars(args) | {"output": str(args.output)}, "windows": results}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps([{key: window[key] for key in ["test_start", "test_end", "metrics"]} for window in results]))


if __name__ == "__main__":
    main()
