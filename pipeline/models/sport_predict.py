"""Preview a specifically selected sport candidate; never replace active models."""

import argparse
import hashlib
import json
from pathlib import Path
import re

import joblib
import pandas as pd

from config import MODEL_DIR
from models.sport_data import SPORTS
from models.sport_features import FEATURES, SCHEMA_VERSION, live_features

CANDIDATE_ROOT = MODEL_DIR / "candidates/sports"


def candidate_directory(candidate_id: str, sport: str, root: Path = CANDIDATE_ROOT) -> Path:
    if sport not in {"football", *SPORTS} or not re.fullmatch(r"\d{8}T\d{12}Z", candidate_id):
        raise ValueError("Invalid sport or candidate ID")
    directory = (root / candidate_id / sport).resolve()
    if not directory.is_relative_to(root.resolve()):
        raise ValueError("Candidate must be inside the sport model store")
    return directory


def catalog() -> list[dict]:
    runs = []
    for path in sorted(CANDIDATE_ROOT.glob("*/report.json"), reverse=True):
        report = json.loads(path.read_text(encoding="utf-8"))
        runs.append({"candidate_id": path.parent.name, "sports": {sport: {key: value.get(key) for key in
            ["status", "completed_games", "active", "minimum_games", "reason"]} for sport, value in report.items()}})
    return runs


def candidate_teams(candidate_id: str, sport: str, league: str | None = None) -> list[str]:
    directory = candidate_directory(candidate_id, sport)
    history = pd.read_parquet(directory / "dataset.parquet")
    if sport != "football":
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        if league not in SPORTS[sport]["leagues"] or league not in metrics.get("training_leagues", []):
            raise ValueError("League has no candidate training data")
        history = history[history.league.eq(league)]
    names = pd.concat([history.home_team, history.away_team]).dropna()
    return sorted(set(names.astype(str).str.strip()) - {""}, key=str.casefold)


def predict_candidate(candidate_id, sport, home, away, kickoff, league=None, home_odds=None, away_odds=None, draw_odds=None, neutral_site=False):
    directory = candidate_directory(candidate_id, sport)
    cutoff = pd.Timestamp(kickoff)
    if cutoff.tzinfo is None:
        raise ValueError("Kickoff must include a timezone")
    cutoff = cutoff.tz_convert("UTC")
    if home.casefold().strip() == away.casefold().strip():
        raise ValueError("Competitors must differ")
    if sport == "football":
        from models.features import FEATURE_NAMES, build_live_features
        from models.football_identity import football_history_key, football_identity_key
        metrics = json.loads((directory / "metrics_v2.1.0.json").read_text(encoding="utf-8"))
        history = pd.read_parquet(directory / "dataset.parquet")
        known = set(history.home_key) | set(history.away_key)
        feature_home = football_history_key(home, known)
        feature_away = football_history_key(away, known)
        if football_identity_key(home) == football_identity_key(away):
            raise ValueError("Competitors must differ")
        X = build_live_features(history, feature_home, feature_away, cutoff, {"home_win": home_odds, "away_win": away_odds, "draw": draw_odds})
        path = directory / "model_v2.1.0.pkl"
        # Football uses the established candidate format. Dataset integrity is
        # verified before using its scores to reconstruct history features.
        if hashlib.sha256((directory / "dataset.parquet").read_bytes()).hexdigest() != metrics["dataset_sha256"]:
            raise ValueError("Candidate dataset checksum mismatch")
        model = joblib.load(path)
        if metrics["features"] != FEATURE_NAMES or model.n_features_in_ != len(FEATURE_NAMES):
            raise ValueError("Incompatible football feature schema")
    else:
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        if metrics["sport"] != sport or metrics["features"] != FEATURES or metrics["feature_schema_version"] != SCHEMA_VERSION:
            raise ValueError("Incompatible sport candidate schema")
        for filename, key in [("model.pkl", "model_sha256"), ("dataset.parquet", "dataset_sha256")]:
            if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != metrics[key]:
                raise ValueError("Candidate checksum mismatch")
        history = pd.read_parquet(directory / "dataset.parquet")
        if league not in SPORTS[sport]["leagues"] or league not in metrics.get("training_leagues", []):
            raise ValueError("League has no candidate training data")
        league_history = history[history.league.eq(league)]
        known = set(league_history.home_key) | set(league_history.away_key)
        if home.casefold().strip() not in known or away.casefold().strip() not in known:
            raise ValueError("Teams lack training history for this league")
        model = joblib.load(directory / "model.pkl")
        X = live_features(history, sport, {"home_team": home, "away_team": away, "date": cutoff, "league": league,
                                          "home_win": home_odds, "away_win": away_odds, "neutral_site": neutral_site})
    if cutoff <= pd.Timestamp(metrics["trained_at"]):
        raise ValueError("Candidate previews require kickoff after model training; use held-out evaluation for historical matches")
    probabilities = model.predict_proba(X)[0]
    return {"candidate_id": candidate_id, "sport": sport, "league": league, "home_team": home, "away_team": away,
        "kickoff": cutoff.isoformat(), "probabilities": dict(zip(metrics["classes"], probabilities.tolist())),
        "winner": metrics["classes"][int(probabilities.argmax())], "model_version": metrics["model_version"],
        "status": "candidate_preview", "active": False, "history_through": history.date.max().isoformat(),
        "settlement_rule": metrics.get("settlement_rule", "REGULATION_1X2"),
        "probability_basis": metrics.get("probability_basis", "UNCONDITIONAL_FINAL_RESULT"),
        "market_features_used": bool(X.iloc[0].odds_missing == 0 and (sport == "football" or model.market_model is not None))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--sport", choices=["football", *SPORTS], required=True)
    parser.add_argument("--league")
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--kickoff", required=True)
    parser.add_argument("--neutral-site", action="store_true")
    args = parser.parse_args()
    print(json.dumps(predict_candidate(args.candidate_id, args.sport, args.home, args.away, args.kickoff, args.league, neutral_site=args.neutral_site), indent=2))


if __name__ == "__main__":
    main()
