"""Build independently evaluated sport candidates without changing active models."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from config import MODEL_DIR
from models.sport_data import SPORTS, load_games, attach_moneylines
from models.sport_features import FEATURES, HISTORY_FEATURES, SCHEMA_VERSION, build_features
from models.sport_model import SportWinnerModel
from models.validation import chronological_split, probability_metrics


def select_expert(X, y, splits, columns, mask):
    train, tune, calibration = [splits[k][mask[splits[k]]] for k in ["train", "tune", "calibration"]]
    outcome_count = len(np.unique(y[y >= 0]))
    if min(len(train), len(tune), len(calibration)) < 30 or any(len(np.unique(y[index])) != outcome_count for index in [train, tune, calibration]):
        return None, {"status": "insufficient_coverage"}
    candidates, scores = {}, {}
    classes = [str(i) for i in np.unique(y[y >= 0])]
    for C in [.01, .1, 1.]:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000, random_state=42))
        model.fit(X.iloc[train][columns], y[train])
        scores[str(C)] = probability_metrics(y[tune], model.predict_proba(X.iloc[tune][columns]), classes)["log_loss"]
        candidates[str(C)] = model
    selected = min(scores, key=scores.get)
    model = candidates[selected]
    development = np.concatenate([train, tune])
    model.fit(X.iloc[development][columns], y[development])
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(X.iloc[calibration][columns], y[calibration])
    return calibrated, {"status": "trained", "selected_C": selected, "tuning_log_loss": scores,
                        "development_samples": len(development), "calibration_samples": len(calibration)}


def supervised_splits(games, sport):
    """Keep NFL ties in history, with no invented winner label or tie probability."""
    splits = chronological_split(games.date)
    excluded = {}
    for name, index in list(splits.items()):
        eligible = games.iloc[index].result.isin(SPORTS[sport]["classes"]).to_numpy()
        purged = np.zeros(len(index), dtype=bool)
        if sport in {"nfl", "ncaaf"} and name != "test":
            next_name = {"train": "tune", "tune": "calibration", "calibration": "test"}[name]
            boundary = games.iloc[splits[next_name]].date.min().normalize()
            purged = games.iloc[index].result_available_at.ge(boundary).to_numpy()
        splits[name] = index[eligible & ~purged]
        excluded[name] = {"unmodeled_outcomes": int((~eligible).sum()), "labels_unavailable_at_next_partition": int(purged.sum())}
    return splits, excluded


def train_sport(sport, directory, min_games=500):
    games = load_games(sport)
    count = len(games)
    report = {"sport": sport, "completed_games": count, "minimum_games": min_games, "status": "insufficient_data", "data_quality": games.attrs.get("data_quality", {})}
    if count < min_games:
        return report
    if games.date.dt.normalize().nunique() < 20:
        return report | {"reason": "Need at least 20 distinct game days"}
    splits, split_exclusions = supervised_splits(games, sport)
    classes = SPORTS[sport]["classes"]
    y = np.array([classes.index(value) if value in classes else -1 for value in games.result])
    if (y >= 0).sum() < min_games:
        return report | {"reason": "Too few games with a modeled winner outcome"}
    if any(len(index) < 30 or len(np.unique(y[index])) != len(classes) for index in splits.values()):
        return report | {"reason": "Each chronological partition needs 30 games and every outcome class"}
    games = attach_moneylines(games, sport)
    X = build_features(games, sport)
    history, history_selection = select_expert(X, y, splits, HISTORY_FEATURES, np.ones(count, dtype=bool))
    market, market_selection = select_expert(X, y, splits, FEATURES[:-1], X.odds_missing.eq(0).to_numpy())
    if history is None:
        return report | {"reason": "Insufficient history expert partitions"}
    model = SportWinnerModel(history, market)
    test = splits["test"]
    probabilities = model.predict_proba(X.iloc[test])
    metrics = probability_metrics(y[test], probabilities, classes)
    development = np.concatenate([splits["train"], splits["tune"]])
    prior = np.bincount(y[development], minlength=len(classes)) / len(development)
    prior_metrics = probability_metrics(y[test], np.tile(prior, (len(test), 1)), classes)
    covered = X.iloc[test].odds_missing.eq(0).to_numpy()
    comparison = None
    if covered.any() and len(classes) == 2:
        comparison = {"model": probability_metrics(y[test][covered], probabilities[covered], classes),
            "market": probability_metrics(y[test][covered], X.iloc[test].loc[covered, ["fair_away_prob", "fair_home_prob"]].to_numpy(), classes)}
    directory.mkdir(parents=True, exist_ok=False)
    games.to_parquet(directory / "dataset.parquet", index=False)
    joblib.dump(model, directory / "model.pkl")
    report.update(status="candidate", model_version="sport-winner-1.0", feature_schema_version=SCHEMA_VERSION,
        features=FEATURES, classes=classes,
        settlement_rule="INCLUDING_OVERTIME_TIES_VOID" if sport == "nfl" else "FINAL_SCORE_WITH_TIES" if sport == "americanfootball" else "INCLUDING_OVERTIME",
        probability_basis="CONDITIONAL_ON_NO_FINAL_TIE" if sport == "nfl" else "UNCONDITIONAL_FINAL_RESULT",
        labeled_games=int((y >= 0).sum()), ties_in_history_not_fitted=int((y < 0).sum()), split_exclusions=split_exclusions,
        data_by_league=games.league.value_counts().to_dict(), odds_complete=int(X.odds_missing.eq(0).sum()),
        training_leagues=sorted(games.iloc[development].league.unique().tolist()),
        transfer_evaluation_leagues=sorted(set(games.iloc[test].league) - set(games.iloc[development].league)),
        trained_at=datetime.now(timezone.utc).isoformat(), directory=str(directory.resolve()),
        dataset_sha256=hashlib.sha256((directory / "dataset.parquet").read_bytes()).hexdigest(),
        model_sha256=hashlib.sha256((directory / "model.pkl").read_bytes()).hexdigest(),
        splits={name: {"samples": len(index), "start": games.iloc[index].date.min().isoformat(), "end": games.iloc[index].date.max().isoformat()} for name, index in splits.items()},
        history_selection=history_selection, market_selection=market_selection, test=metrics,
        training_prior_baseline=prior_metrics, market_comparison=comparison,
        test_by_league={league: probability_metrics(y[test][games.iloc[test].league.eq(league).to_numpy()], probabilities[games.iloc[test].league.eq(league).to_numpy()], classes) for league in games.iloc[test].league.unique()},
        active=False)
    (directory / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def train_all(sports, output=None):
    output = output or MODEL_DIR / "candidates/sports" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for sport in sports:
        print(f"Building {sport} candidate...", flush=True)
        if sport == "football":
            from models.train_model_v2 import train_model
            metrics = train_model(output / "football")
            results[sport] = {"sport": sport, "status": "candidate", "directory": str((output / sport).resolve()),
                             "completed_games": metrics["data_report"]["fixtures"], "test": metrics["test"], "active": False}
        else:
            with threadpool_limits(limits=2):
                results[sport] = train_sport(sport, output / sport)
        (output / "report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps({"sport": sport, "status": results[sport]["status"], "completed_games": results[sport]["completed_games"]}), flush=True)
    print(f"Sport model report: {output / 'report.json'}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sports", nargs="+", choices=["football", *SPORTS], default=[*SPORTS, "football"])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    train_all(list(dict.fromkeys(args.sports)), args.output_dir)


if __name__ == "__main__":
    main()
