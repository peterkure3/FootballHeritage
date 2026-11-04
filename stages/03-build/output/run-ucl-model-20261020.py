"""Run the configured active football model read-only for tonight's fixtures."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URI, MODEL_DIR, MODEL_VERSION
from models.predict_v2 import load_model_artifacts, get_team_elo_ratings, build_feature_vector

now = datetime.now(timezone.utc)
engine = create_engine(DATABASE_URI, connect_args={"options": "-c default_transaction_read_only=on", "connect_timeout": 10})
model, encoder, features, scaler = load_model_artifacts()
report = {"generated_at": now.isoformat(), "model_version": MODEL_VERSION,
          "model_type": type(model).__name__, "feature_count": len(features),
          "classes": list(encoder.classes_), "matches": []}
report["calibration_method"] = getattr(model, "method", None)
report["base_estimator_type"] = type(getattr(model, "estimator", None)).__name__
report["scope"] = "Read-only execution of active model; raw probabilities are diagnostic, not validated bets"
metrics = MODEL_DIR / f"metrics_v{MODEL_VERSION}.json"
if metrics.exists():
    report["training_metrics"] = json.loads(metrics.read_text(encoding="utf-8"))
with engine.connect() as conn:
    report["history_audit"] = dict(conn.execute(text("SELECT COUNT(*) AS completed, MAX(date) AS latest_completed, COUNT(*) FILTER (WHERE date >= :now) AS future_completed FROM matches WHERE sport_type = 'football' AND result IS NOT NULL"), {"now": now}).mappings().one())
    fixtures = list(conn.execute(text("SELECT match_id, date, home_team, away_team, status, result FROM matches WHERE sport_type = 'football' AND date >= :start AND date < :end ORDER BY date, home_team"), {"start": "2026-10-20T16:00:00+00:00", "end": "2026-10-20T21:00:00+00:00"}).mappings())
elo = get_team_elo_ratings(engine)
for fixture in fixtures:
    row = dict(fixture)
    with engine.connect() as conn:
        quotes = list(conn.execute(text("SELECT DISTINCT ON (bookmaker) bookmaker, home_win, draw, away_win, updated_at FROM odds WHERE match_id = :id AND updated_at <= :now AND home_win > 1 AND draw > 1 AND away_win > 1 ORDER BY bookmaker, updated_at DESC, id DESC"), {"id": row["match_id"], "now": now}).mappings())
        coverage = {}
        for side in ("home_team", "away_team"):
            coverage[side] = dict(conn.execute(text("SELECT COUNT(*) AS completed, MAX(date) AS latest_completed FROM matches WHERE sport_type = 'football' AND result IS NOT NULL AND date < :now AND (home_team = :team OR away_team = :team)"), {"now": now, "team": row[side]}).mappings().one())
    row["coverage"] = coverage
    row["quotes"] = [dict(q) for q in quotes]
    if not quotes:
        row["withheld"] = "No stored complete odds; refusing serving fallback odds"
        report["matches"].append(row)
        continue
    odds = {k: float(np.mean([float(q[k]) for q in quotes])) for k in ("home_win", "draw", "away_win")}
    row["input_mean_odds"] = odds
    X = build_feature_vector(row["home_team"], row["away_team"], engine, elo, odds, features, cutoff=pd.Timestamp(now))
    if scaler is not None:
        X = pd.DataFrame(scaler.transform(X), columns=X.columns)
    probabilities = model.predict_proba(X)[0]
    assert np.isfinite(probabilities).all() and abs(float(sum(probabilities)) - 1) < 1e-6
    row["probabilities"] = {str(k): float(v) for k, v in zip(encoder.classes_, probabilities)}
    row["predicted_outcome"] = str(encoder.inverse_transform([model.predict(X)[0]])[0])
    row["features"] = {str(k): float(v) for k, v in X.iloc[0].items()}
    row["best_stored_prices"] = {k: max(float(q[k]) for q in quotes) for k in odds}
    row["gross_ev_at_best_stored"] = {k: row["probabilities"][k] * row["best_stored_prices"][k] - 1 for k in odds}
    row["quality_flags"] = []
    if any(p <= 0 or p >= 1 for p in probabilities):
        row["quality_flags"].append("Boundary probability: inspect calibration before using EV")
    if any(c["completed"] < 5 for c in coverage.values()):
        row["quality_flags"].append("Fewer than five exact-name completed records for at least one team")
    if pd.Timestamp(row["date"], tz="UTC") <= pd.Timestamp(now):
        row["quality_flags"].append("Past scheduled kickoff: pre-match model output is not a live forecast")
    row["quality_flags"].append("Legacy model uses unnormalized team-name database matching; coverage may omit aliases")
    report["matches"].append(row)
output = Path(__file__).with_name("ucl-active-model-20261020.json")
output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(json.dumps({"output": str(output), "model_version": MODEL_VERSION, "model_type": type(model).__name__, "calibration_method": report["calibration_method"], "features": len(features), "history_audit": report["history_audit"], "matches": [{k: v for k, v in r.items() if k not in ("features", "quotes")} for r in report["matches"]]}, indent=2, default=str))
