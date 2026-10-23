"""Train isolated candidates with causal features and chronological selection."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version as package_version
import json
from pathlib import Path
import sys

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import LabelEncoder
from threadpoolctl import threadpool_limits
import xgboost as xgb

sys.path.append(str(Path(__file__).parent.parent))
from config import MODEL_DIR, PROCESSED_DATA_DIR, HISTORICAL_CSV_DIR, LOG_LEVEL
from etl.utils import setup_logger, save_json
from models.data import canonical_matches, historical_frames, merge_prematch_odds
from models.import_sportsbook_odds import load_imported_odds
from models.features import FEATURE_SCHEMA_VERSION, FEATURE_NAMES, build_feature_frame
from models.ensemble import TemporalStackingClassifier
from models.validation import chronological_split, probability_metrics
from models.selection import fit_odds_aware

logger = setup_logger(__name__, LOG_LEVEL)
MODEL_VERSION = "2.1.0"


def load_training_data() -> pd.DataFrame:
    files = sorted(PROCESSED_DATA_DIR.glob("matches_processed_*.parquet"))
    frames = []
    # Each transform produces a cumulative snapshot. Using every old snapshot
    # reintroduces corrected records and stale odds joins into the training corpus.
    if files:
        processed = pd.read_parquet(files[-1])
        # Legacy snapshot odds were joined on team names only and cannot be trusted.
        processed = processed.drop(columns=["home_win", "draw", "away_win", "B365H", "B365D", "B365A"], errors="ignore")
        frames.append(processed)
    frames.extend(historical_frames(HISTORICAL_CSV_DIR))
    df = canonical_matches(frames)
    imported_odds = load_imported_odds()
    if not imported_odds.empty:
        df = merge_prematch_odds(df, imported_odds, exact_kickoff=True)
        logger.info("Loaded %d imported sportsbook observations; only exact fixture kickoffs can join", len(imported_odds))
    logger.info(f"Canonical fixtures: {len(df)}, completed: {df.result.notna().sum()}")
    return df


def prepare_enhanced_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    X, fixtures = build_feature_frame(df)
    complete = fixtures.result.notna()
    return X.loc[complete].reset_index(drop=True), fixtures.loc[complete, "result"].reset_index(drop=True), FEATURE_NAMES.copy()


def create_ensemble_model(trees: int = 200, threads: int = 2) -> TemporalStackingClassifier:
    return TemporalStackingClassifier([
        ("xgb", xgb.XGBClassifier(objective="multi:softprob", num_class=3,
                                 max_depth=6, learning_rate=0.05, n_estimators=trees,
                                 subsample=0.8, colsample_bytree=0.8, random_state=42,
                                 n_jobs=threads, eval_metric="mlogloss")),
        ("lgb", lgb.LGBMClassifier(objective="multiclass", num_class=3, max_depth=6,
                                  learning_rate=0.05, n_estimators=trees, subsample=0.8,
                                  colsample_bytree=0.8, random_state=42, n_jobs=threads, verbose=-1)),
        ("rf", RandomForestClassifier(n_estimators=trees, max_depth=10,
                                      min_samples_split=10, random_state=42, n_jobs=threads)),
        ("gb", GradientBoostingClassifier(n_estimators=max(10, trees // 2),
                                          max_depth=5, learning_rate=0.1, random_state=42)),
    ])


def dataset_report(fixtures: pd.DataFrame, splits: dict) -> dict:
    return {
        "fixtures": len(fixtures), "odds_complete": int(fixtures[["home_win", "draw", "away_win"]].notna().all(axis=1).sum()),
        "by_competition": fixtures.groupby("competition", dropna=False).size().to_dict() if "competition" in fixtures else {},
        "by_year": {str(year): {"samples": len(group), "odds_complete": int(group[["home_win", "draw", "away_win"]].notna().all(axis=1).sum())}
                    for year, group in fixtures.groupby(fixtures.date.dt.year)},
        "splits": {name: {"samples": len(indices),
                          "start": fixtures.iloc[indices].date.min().isoformat(),
                          "end": fixtures.iloc[indices].date.max().isoformat(),
                          "odds_complete": int(fixtures.iloc[indices][["home_win", "draw", "away_win"]].notna().all(axis=1).sum()),
                          "classes": fixtures.iloc[indices].result.value_counts().to_dict()}
                   for name, indices in splits.items()},
    }


def train_model(output_dir: Path = None, trees: int = 200, threads: int = 2,
                dry_run: bool = False, strategy: str = "odds-aware") -> dict:
    df = load_training_data()
    X, fixtures = build_feature_frame(df)
    mask = fixtures.result.notna()
    X, fixtures = X.loc[mask].reset_index(drop=True), fixtures.loc[mask].reset_index(drop=True)
    if len(X) < 1000:
        raise ValueError(f"Insufficient completed fixtures: {len(X)}; need at least 1000")
    splits = chronological_split(fixtures.date)
    report = dataset_report(fixtures, splits)
    logger.info(json.dumps(report, default=str))
    if dry_run:
        return report
    output_dir = output_dir or MODEL_DIR / "candidates" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir.mkdir(parents=True, exist_ok=False)
    encoder = LabelEncoder().fit(["away_win", "draw", "home_win"])
    y = encoder.transform(fixtures.result)
    for name, indices in splits.items():
        if len(np.unique(y[indices])) != 3:
            raise ValueError(f"{name} period must contain all three classes")
    train, tune, calibration, test = [splits[k] for k in ["train", "tune", "calibration", "test"]]
    selection = None
    if strategy == "odds-aware":
        logger.info("Selecting separate market and history experts on the tuning period")
        with threadpool_limits(limits=threads):
            calibrated, selection = fit_odds_aware(X, y, splits, trees)
        # These are selection-period scores before development refitting.
        tune_metrics = selection["market"]["tuning"][selection["market"]["selected"]]
    elif strategy == "stacking":
        model = create_ensemble_model(trees, threads)
        logger.info("Training chronological ensemble for tuning-period evaluation")
        model.fit(X.iloc[train], y[train], dates=fixtures.iloc[train].date)
        tune_metrics = probability_metrics(y[tune], model.predict_proba(X.iloc[tune]), list(encoder.classes_))
        logger.info("Refitting on train+tune, leaving calibration and test untouched")
        development = np.concatenate([train, tune])
        model.fit(X.iloc[development], y[development], dates=fixtures.iloc[development].date)
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid", cv=2)
        calibrated.fit(X.iloc[calibration], y[calibration])
    else:
        raise ValueError(f"Unknown model strategy: {strategy}")
    probabilities = calibrated.predict_proba(X.iloc[test])
    test_metrics = probability_metrics(y[test], probabilities, list(encoder.classes_))
    baseline_columns = ["fair_away_prob", "fair_draw_prob", "fair_home_prob"]
    covered = X.iloc[test].odds_missing.eq(0).to_numpy()
    comparison = {}
    if covered.any():
        comparison = {"model": probability_metrics(y[test][covered], probabilities[covered], list(encoder.classes_)),
                      "market": probability_metrics(y[test][covered], X.iloc[test][baseline_columns].to_numpy()[covered], list(encoder.classes_))}
    by_league = {}
    if "competition" in fixtures:
        for league in fixtures.iloc[test].competition.dropna().unique():
            subset = fixtures.iloc[test].competition.eq(league).to_numpy()
            by_league[str(league)] = probability_metrics(y[test][subset], probabilities[subset], list(encoder.classes_))
    dataset_path = output_dir / "dataset.parquet"
    fixtures.to_parquet(dataset_path, index=False)
    missing = ~covered
    metrics = {"model_version": MODEL_VERSION, "feature_schema_version": FEATURE_SCHEMA_VERSION,
               "model_type": "calibrated_odds_aware_experts" if strategy == "odds-aware" else "calibrated_temporal_stacking_ensemble", "features": FEATURE_NAMES,
               "classes": list(encoder.classes_), "trained_at": datetime.now(timezone.utc).isoformat(),
               "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
               "data_report": report, "tune": tune_metrics, "test": test_metrics,
               "market_comparison": comparison, "test_by_competition": by_league,
               "test_without_odds": probability_metrics(y[test][missing], probabilities[missing], list(encoder.classes_)) if missing.any() else None,
               "selection": selection,
               "parameters": {"trees": trees, "threads": threads, "strategy": strategy}, "status": "candidate",
               "dependencies": {name: package_version(name) for name in ["numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "joblib"]}}
    joblib.dump(calibrated, output_dir / f"model_v{MODEL_VERSION}.pkl")
    joblib.dump(encoder, output_dir / f"label_encoder_v{MODEL_VERSION}.pkl")
    joblib.dump(FEATURE_NAMES, output_dir / f"features_v{MODEL_VERSION}.pkl")
    save_json(metrics, output_dir / f"metrics_v{MODEL_VERSION}.json")
    logger.info(f"Candidate saved to {output_dir}; test accuracy={test_metrics['accuracy']:.4f}, log_loss={test_metrics['log_loss']:.4f}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--trees", type=int, default=200)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strategy", choices=["odds-aware", "stacking"], default="odds-aware")
    args = parser.parse_args()
    if args.trees < 10 or args.threads < 1:
        parser.error("--trees must be >= 10 and --threads must be >= 1")
    train_model(args.output_dir, args.trees, args.threads, args.dry_run, args.strategy)


if __name__ == "__main__":
    main()
