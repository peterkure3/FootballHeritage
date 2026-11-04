"""Run provenance-gated feature ablations without writing production artifacts.

Input JSON contains classes, feature_groups, feature_definitions, snapshots and
rows. Each row has game_id, kickoff, cutoff, competition, season, target (class
index), features and provenance (one evidence record per feature).
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.feature_availability import ForecastContract, utc_timestamp, validate_feature
from models.training_resources import training_threads
from models.validation import chronological_split, forward_folds, probability_metrics


def package_versions() -> dict:
    result = {}
    for name in ["numpy", "pandas", "scikit-learn", "lightgbm", "xgboost"]:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def validate_dataset(data: dict, root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = data["feature_groups"]
    if "basic" not in groups or not groups["basic"]:
        raise ValueError("A nonempty basic feature group is required")
    columns = [column for values in groups.values() for column in values]
    if len(columns) != len(set(columns)):
        raise ValueError("Feature groups must be disjoint")
    snapshots = set()
    for snapshot in data["snapshots"]:
        path = (root / snapshot["path"]).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != snapshot["sha256"] or not snapshot["source_url"]:
            raise ValueError("Input snapshot checksum or source mismatch")
        utc_timestamp(snapshot["retrieved_at"])
        snapshots.add((digest, snapshot["source_url"]))
    rows = data["rows"]
    if not rows or len({str(row["game_id"]) for row in rows}) != len(rows):
        raise ValueError("Need nonempty rows with globally unique game IDs")
    for row in rows:
        contract = ForecastContract(str(row["game_id"]), row["kickoff"], row["cutoff"], row.get("mode", "prematch"))
        if (row.get("target_availability_status") != "verified"
                or utc_timestamp(row.get("target_available_at")) <= utc_timestamp(row["kickoff"])):
            raise ValueError("Outcome labels need verified availability after kickoff")
        for column in columns:
            evidence = row["provenance"][column]
            if (evidence["feature"] != column or evidence["definition"] != data["feature_definitions"][column]
                    or (evidence["snapshot_sha256"], evidence["source_url"]) not in snapshots):
                raise ValueError("Feature definition or input snapshot is not registered")
            validate_feature(contract, evidence)
            value = row["features"][column]
            if value is not None and not np.isfinite(float(value)):
                raise ValueError("Numerical features must be finite or explicitly null")
            if "stale_features" in row:
                stale = row["stale_provenance"][column]
                if (stale["feature"] != column or stale["definition"] != evidence["definition"]
                        or (stale["snapshot_sha256"], stale["source_url"]) not in snapshots):
                    raise ValueError("Stale feature provenance is not registered")
                validate_feature(contract, stale)
                if utc_timestamp(stale["available_at"]) >= utc_timestamp(evidence["available_at"]):
                    raise ValueError("Stale inputs must come from an earlier observed snapshot")
                value = row["stale_features"][column]
                if value is not None and not np.isfinite(float(value)):
                    raise ValueError("Stale features must be finite or null")
        target = row["target"]
        if type(target) is not int or not 0 <= target < len(data["classes"]):
            raise ValueError("Target must index the declared class order")
    metadata = pd.DataFrame([{key: row[key] for key in ["game_id", "kickoff", "cutoff", "competition", "season", "target", "target_available_at"]} for row in rows])
    metadata["date"] = pd.to_datetime(metadata.cutoff, utc=True)
    order = metadata.sort_values(["date", "game_id"]).index
    features = pd.DataFrame([row["features"] for row in rows], columns=columns, dtype=float)
    return features.loc[order].reset_index(drop=True), metadata.loc[order].reset_index(drop=True)


def candidates(seed: int, trees: int) -> dict:
    # All preprocessing is fitted inside the estimator on the training period.
    result = {"logistic": make_pipeline(SimpleImputer(add_indicator=True, keep_empty_features=True),
        StandardScaler(), LogisticRegression(max_iter=2000, random_state=seed))}
    try:
        from lightgbm import LGBMClassifier
        result["lightgbm"] = LGBMClassifier(n_estimators=trees, num_leaves=15, random_state=seed, n_jobs=1, verbosity=-1)
    except ImportError:
        pass
    try:
        from xgboost import XGBClassifier
        result["xgboost"] = XGBClassifier(n_estimators=trees, max_depth=3, random_state=seed, n_jobs=1)
    except ImportError:
        pass
    return result


def grouped_metrics(meta: pd.DataFrame, y: np.ndarray, probabilities: np.ndarray, classes: list) -> dict:
    return {str(key): probability_metrics(y[positions], probabilities[positions], classes)
            for key, positions in meta.reset_index(drop=True).groupby(["competition", "season"]).indices.items()}


def stress_inputs(X: pd.DataFrame, groups: dict, seed: int) -> dict:
    result = {"clean": X.copy()}
    rng = np.random.default_rng(seed)
    for name, columns in groups.items():
        missing = X.copy()
        missing.loc[:, columns] = np.nan
        result[f"missing/{name}"] = missing
        corrupted = X.copy()
        # A fixed multiplicative stress, not noise scaled using future outcomes.
        corrupted.loc[:, columns] *= rng.choice([.5, 1.5], size=(len(X), len(columns)))
        result[f"corrupted/{name}"] = corrupted
    return result


def run(data: dict, root: Path, seed: int = 42, trees: int = 200) -> dict:
    X, meta = validate_dataset(data, root)
    by_id = {str(row["game_id"]): row for row in data["rows"]}
    classes = data["classes"]
    if len(classes) < 2 or len(set(classes)) != len(classes):
        raise ValueError("Need distinct outcome classes")
    y = meta.target.to_numpy()
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "seed": seed, "trees": trees,
              "versions": package_versions(), "snapshots": data["snapshots"],
              "feature_definitions": data["feature_definitions"], "feature_groups": data["feature_groups"],
              "classes": classes, "production_changed": False, "competitions": {},
              "limitations": ["Availability evidence is supplied by the adapter; this verifier cannot establish that source claims are true.",
                  "No calibration or ensemble tuning in this fixed-budget experiment.",
                  "Repeated examination consumes the final holdout; use a new future period for subsequent decisions.",
                  "Stale inputs run only when every test row supplies verified earlier snapshots."]}
    for competition, positions in meta.groupby("competition").indices.items():
        features, rows = X.iloc[positions].reset_index(drop=True), meta.iloc[positions].reset_index(drop=True)
        labels = y[positions]
        split = chronological_split(rows.date)
        development = np.concatenate([split[key] for key in ["train", "tune", "calibration"]])
        test = split["test"]
        target_times = pd.to_datetime(rows.target_available_at, utc=True)
        development = development[(target_times.iloc[development] < rows.iloc[test].date.min()).to_numpy()]
        folds = forward_folds(rows.iloc[development].date.reset_index(drop=True))
        groups = data["feature_groups"]
        configurations = {"basic": groups["basic"]}
        configurations.update({f"basic+{key}": groups["basic"] + value for key, value in groups.items() if key != "basic"})
        models = candidates(seed, trees)
        output = {"splits": {key: {"samples": len(idx), "start": rows.iloc[idx].date.min().isoformat(),
                    "end": rows.iloc[idx].date.max().isoformat(), "game_ids": rows.iloc[idx].game_id.tolist()} for key, idx in split.items()},
                  "forecast_cutoffs": rows[["game_id", "kickoff", "cutoff"]].to_dict("records"),
                  "development_fit_samples": len(development),
                  "unavailable_models": [key for key in ["lightgbm", "xgboost"] if key not in models], "experiments": {}}
        for group, columns in configurations.items():
            for name, prototype in models.items():
                fold_results = []
                for train, validation in folds:
                    train = train[(target_times.iloc[development[train]] < rows.iloc[development[validation]].date.min()).to_numpy()]
                    if len(np.unique(labels[development[train]])) != len(classes):
                        raise ValueError("Every walk-forward training fold needs every outcome class")
                    estimator = clone(prototype).fit(features.iloc[development[train]][columns], labels[development[train]])
                    fold_metrics = probability_metrics(labels[development[validation]],
                        estimator.predict_proba(features.iloc[development[validation]][columns]), classes)
                    fold_metrics["periods"] = {key: {"start": rows.iloc[idx].date.min().isoformat(),
                        "end": rows.iloc[idx].date.max().isoformat(), "samples": len(idx)}
                        for key, idx in [("train", development[train]), ("validation", development[validation])]}
                    fold_results.append(fold_metrics)
                estimator = clone(prototype).fit(features.iloc[development][columns], labels[development])
                scenarios = stress_inputs(features.iloc[test][columns],
                    {key: [c for c in value if c in columns] for key, value in groups.items() if any(c in columns for c in value)}, seed)
                if all("stale_features" in by_id[str(game)] for game in rows.iloc[test].game_id):
                    scenarios["stale"] = pd.DataFrame([by_id[str(game)]["stale_features"] for game in rows.iloc[test].game_id], columns=columns, dtype=float)
                results = {}
                for scenario, inputs in scenarios.items():
                    probability = estimator.predict_proba(inputs)
                    results[scenario] = probability_metrics(labels[test], probability, classes)
                    results[scenario]["by_competition_season"] = grouped_metrics(rows.iloc[test], labels[test], probability, classes)
                    results[scenario]["predictions"] = [{"game_id": game, "probabilities": p.tolist()} for game, p in zip(rows.iloc[test].game_id, probability)]
                clean = results["clean"]
                for metrics in results.values():
                    metrics["log_loss_degradation"] = metrics["log_loss"] - clean["log_loss"]
                    metrics["brier_degradation"] = metrics["brier_score"] - clean["brier_score"]
                output["experiments"][f"{group}/{name}"] = {"configuration": {key: str(value) for key, value in prototype.get_params().items()},
                    "stale_status": "evaluated" if "stale" in scenarios else "unavailable_verified_earlier_snapshots",
                    "walk_forward": fold_results, "test": results}
        for key, experiment in output["experiments"].items():
            baseline = output["experiments"]["basic/logistic"]["test"]["clean"]
            measured = experiment["test"]["clean"]
            experiment["improved_over_basic_logistic"] = all(measured[m] < baseline[m] for m in ["log_loss", "brier_score"])
        report["competitions"][str(competition)] = output
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trees", type=int, default=200)
    args = parser.parse_args()
    if args.output.exists() or args.trees < 1:
        parser.error("Output must be new and trees must be positive")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    with training_threads(1):
        report = run(data, args.input.parent, args.seed, args.trees)
    report["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
