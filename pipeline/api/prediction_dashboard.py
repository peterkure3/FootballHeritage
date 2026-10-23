"""Dashboard contracts: paginated fixtures and pre-kickoff evaluation evidence."""
from collections import defaultdict
from datetime import datetime, timezone
import math

from sqlalchemy import text

from api.db import get_db_connection
from config import MODEL_VERSION
from api.bookmaker_catalog import bookmaker_catalog

OUTCOMES = ("home_win", "draw", "away_win")
PROBABILITY_KEYS = ("home_prob", "draw_prob", "away_prob")
UTC_NOW = "(NOW() AT TIME ZONE 'UTC')"
VALID_PROBS = """p.home_prob BETWEEN 0 AND 1 AND p.draw_prob BETWEEN 0 AND 1
    AND p.away_prob BETWEEN 0 AND 1
    AND ABS(p.home_prob + p.draw_prob + p.away_prob - 1) < 0.01
    AND p.winner IN ('home_win','draw','away_win')"""


def utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def valid_probabilities(row):
    values = [row.get(key) for key in PROBABILITY_KEYS]
    if any(value is None or not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        return None
    if abs(sum(values) - 1) >= .01:
        return None
    return dict(zip(OUTCOMES, values))


def quote_comparison(probabilities, quotes, now, prediction_fresh):
    """Actual latest quotes for prices; equal-book, no-vig consensus separately."""
    available = []
    normalized = []
    for quote in quotes:
        observed = quote.get("updated_at")
        if isinstance(observed, str):
            try:
                observed = datetime.fromisoformat(observed.replace('Z', '+00:00'))
            except ValueError:
                observed = None
        if observed:
            observed = observed.replace(tzinfo=timezone.utc) if observed.tzinfo is None else observed.astimezone(timezone.utc)
        age = (now - observed).total_seconds() / 3600 if observed else None
        prices = {key: quote.get(key) if quote.get(key) is not None and math.isfinite(quote[key]) else None for key in OUTCOMES}
        valid = all(value is not None and math.isfinite(value) and value > 1 for value in prices.values())
        fresh = valid and age is not None and 0 <= age <= 24
        available.append({"bookmaker": quote["bookmaker"], "prices": prices,
                          "observed_at": observed.isoformat() if observed else None,
                          "fresh": fresh})
        if fresh:
            implied = {key: 1 / value for key, value in prices.items()}
            total = sum(implied.values())
            fair = {key: value / total for key, value in implied.items()}
            available[-1]["fair_probabilities"] = fair
            normalized.append(fair)
    consensus = {key: sum(book[key] for book in normalized) / len(normalized) for key in OUTCOMES} if normalized else None
    comparisons = []
    if probabilities and prediction_fresh:
        for key, probability in probabilities.items():
            eligible = [quote for quote in available if quote["fresh"]]
            best = max(eligible, key=lambda quote: quote["prices"][key], default=None)
            if best:
                price = best["prices"][key]
                comparisons.append({"outcome": key, "decimal_odds": price, "bookmaker": best["bookmaker"],
                    "observed_at": best["observed_at"], "break_even_prob": 1 / price,
                    "consensus_prob": consensus[key], "consensus_difference_pp": (probability - consensus[key]) * 100,
                    "estimated_ev_units": probability * price - 1})
    state = "current" if normalized else "unverified_or_stale" if available else "missing"
    return {"odds_format": "decimal", "settlement_rule": "REGULATION_1X2", "state": state,
            "quotes": available, "consensus": consensus, "comparisons": comparisons}


def fixtures(page, page_size, competition=None, match_date=None):
    filters = f"""m.date > {UTC_NOW} AND m.result IS NULL
        AND UPPER(COALESCE(m.status,'')) NOT IN
            ('FINISHED','CANCELLED','CANCELED','POSTPONED','LIVE','IN_PLAY','PAUSED')
        AND (:competition IS NULL OR m.competition = :competition)
        AND (CAST(:date AS DATE) IS NULL OR m.date::date = CAST(:date AS DATE))"""
    params = {"competition": competition or None, "date": match_date, "version": MODEL_VERSION,
              "limit": page_size, "offset": (page - 1) * page_size}
    query = f"""
        SELECT m.*, p.winner, p.home_prob, p.draw_prob, p.away_prob,
            p.model_version, p.created_at AS prediction_created_at,
            COALESCE(q.quotes, '[]'::json) AS quotes
        FROM matches m
        LEFT JOIN LATERAL (
            SELECT * FROM predictions p WHERE p.match_id = m.match_id
                AND p.model_version = :version AND p.created_at < m.date AND p.created_at <= {UTC_NOW}
            ORDER BY p.created_at DESC, p.id DESC LIMIT 1
        ) p ON TRUE
        LEFT JOIN LATERAL (
            SELECT json_agg(latest) AS quotes FROM (
                SELECT DISTINCT ON (o.bookmaker) o.bookmaker, o.home_win, o.draw, o.away_win, o.updated_at
                FROM odds o WHERE o.match_id = m.match_id
                ORDER BY o.bookmaker, o.updated_at DESC NULLS LAST, o.id DESC
            ) latest
        ) q ON TRUE
        WHERE {filters} ORDER BY m.date ASC, m.match_id ASC LIMIT :limit OFFSET :offset
    """
    with get_db_connection().connect() as connection:
        total = connection.execute(text(f"SELECT COUNT(*) FROM matches m WHERE {filters}"), params).scalar()
        rows = connection.execute(text(query), params).mappings().all()
        leagues = connection.execute(text(f"SELECT DISTINCT m.competition FROM matches m WHERE m.date > {UTC_NOW} AND m.result IS NULL AND m.competition IS NOT NULL ORDER BY m.competition")).scalars().all()
    now = datetime.now(timezone.utc)
    items = []
    for row in rows:
        probabilities = valid_probabilities(row)
        generated = row["prediction_created_at"]
        age = (now - generated.replace(tzinfo=timezone.utc)).total_seconds() / 3600 if generated else None
        fresh = age is not None and 0 <= age <= 24
        prediction = None
        if generated:
            prediction = {"probabilities": probabilities, "winner": row["winner"], "model_version": row["model_version"],
                "status": "invalid" if probabilities is None else "current" if fresh else "stale",
                "active": True, "generated_at": utc(generated), "feature_cutoff": None,
                "input_quality": "not_recorded", "fallback_inputs": None}
        items.append({"match_id": row["match_id"], "sport": "football", "competition": row["competition"],
            "home_team": row["home_team"], "away_team": row["away_team"], "kickoff": utc(row["date"]),
            "status": row["status"], "prediction": prediction,
            "market": quote_comparison(probabilities, row["quotes"], now, fresh)})
    return {"items": items, "bookmakers": bookmaker_catalog(), "total_count": total, "page": page, "page_size": page_size, "competitions": leagues,
            "generated_at": now.isoformat(), "active_model_version": MODEL_VERSION,
            "timezone_basis": "stored_pipeline_timestamps_assumed_UTC", "max_evidence_age_hours": 24}


def evaluation_scope(league=None, days=None, start_date=None, end_date=None, version=None):
    conditions = ["m.result IN ('home_win','draw','away_win')", "(:league IS NULL OR m.competition = :league)"]
    params = {"league": league or None, "version": version or None}
    # Unknown kickoff rows cannot belong to any named date window.
    if start_date:
        conditions.append("m.date >= CAST(:start AS DATE)")
        params["start"] = start_date
    if end_date:
        conditions.append("m.date < CAST(:end AS DATE) + INTERVAL '1 day'")
        params["end"] = end_date
    if days and not (start_date or end_date):
        conditions.append(f"m.date >= {UTC_NOW} - :days * INTERVAL '1 day'")
        params["days"] = days
    conditions.append(f"(m.date IS NULL OR m.date < {UTC_NOW})")
    cte = f"""WITH scope AS (
        SELECT m.* FROM matches m WHERE {' AND '.join(conditions)}
    ), eligible AS (
        SELECT m.*, p.winner AS predicted_winner, p.home_prob, p.draw_prob, p.away_prob,
            p.model_version, p.created_at AS prediction_created_at,
            m.result = p.winner AS is_correct
        FROM scope m JOIN LATERAL (
            SELECT * FROM predictions p WHERE p.match_id = m.match_id
                AND (:version IS NULL OR p.model_version = :version)
                AND p.created_at < m.date AND {VALID_PROBS}
            ORDER BY p.created_at DESC, p.id DESC LIMIT 1
        ) p ON TRUE
    )"""
    return cte, params


def evaluation_rows(league=None, days=None, start_date=None, end_date=None, version=None):
    cte, params = evaluation_scope(league, days, start_date, end_date, version)
    with get_db_connection().connect() as connection:
        rows = [dict(row) for row in connection.execute(text(cte + " SELECT * FROM eligible ORDER BY date DESC, match_id DESC"), params).mappings()]
        excluded = exclusions(connection, cte, params, bool(days or start_date or end_date))
    return rows, excluded


def exclusions(connection, cte, params, has_window):
    excluded = connection.execute(text(cte + """ SELECT
        COUNT(*) FILTER (WHERE date IS NULL) AS unknown_kickoff,
        COUNT(*) FILTER (WHERE date IS NOT NULL AND match_id NOT IN (SELECT match_id FROM eligible)) AS no_valid_pre_kickoff
        FROM scope"""), params).mappings().one()
    unknown = connection.execute(text("""SELECT COUNT(DISTINCT m.match_id) FROM matches m
        JOIN predictions p ON p.match_id=m.match_id
        WHERE m.result IS NOT NULL AND m.date IS NULL
            AND (:league IS NULL OR m.competition = :league)
            AND (:version IS NULL OR p.model_version = :version)"""), params).scalar()
    return {**dict(excluded), "unknown_kickoff_outside_date_window": unknown if has_window else 0}


def confidence(row):
    probability = max(row[key] for key in PROBABILITY_KEYS)
    return "High" if probability >= .6 else "Medium" if probability >= .45 else "Low"


def history(page, page_size, league=None, result_filter=None, days=None, start_date=None, end_date=None, version=None):
    cte, params = evaluation_scope(league, days, start_date, end_date, version)
    params.update(limit=page_size, offset=(page - 1) * page_size)
    condition = "WHERE is_correct = :correct" if result_filter in {"correct", "incorrect"} else ""
    params["correct"] = result_filter == "correct"
    with get_db_connection().connect() as connection:
        counts = connection.execute(text(cte + f" SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_correct) AS correct FROM eligible {condition}"), params).mappings().one()
        rows = connection.execute(text(cte + f" SELECT * FROM eligible {condition} ORDER BY date DESC, match_id DESC LIMIT :limit OFFSET :offset"), params).mappings().all()
        excluded = exclusions(connection, cte, params, bool(days or start_date or end_date))
    items = []
    for row in rows:
        items.append({**{key: row[key] for key in ["match_id", "home_team", "away_team", "competition", "home_score", "away_score", "predicted_winner", *PROBABILITY_KEYS, "model_version", "is_correct"]},
            "match_date": utc(row["date"]), "prediction_created_at": utc(row["prediction_created_at"]),
            "actual_result": row["result"], "confidence": confidence(row)})
    return {"predictions": items, "total_count": counts["total"], "correct_count": counts["correct"],
            "accuracy_pct": round(counts["correct"] / counts["total"] * 100, 2) if counts["total"] else None,
            "page": page, "page_size": page_size, "excluded": excluded,
            "evaluation_basis": "latest_valid_pre_kickoff_per_fixture"}


def accuracy(league=None, days=None, start_date=None, end_date=None, version=None):
    rows, excluded = evaluation_rows(league, days, start_date, end_date, version)
    groups = defaultdict(list)
    tiers = defaultdict(list)
    for row in rows:
        groups[row["competition"] or "Unknown"].append(row)
        tiers[confidence(row)].append(row)
    def aggregate(name, values, key):
        correct = sum(row["is_correct"] for row in values)
        return {key: name, "total": len(values), "correct": correct, "accuracy_pct": round(correct / len(values) * 100, 2)}
    losses, briers = [], []
    for row in rows:
        probabilities = valid_probabilities(row)
        losses.append(-math.log(max(probabilities[row["result"]], 1e-15)))
        briers.append(sum((probabilities[key] - int(row["result"] == key)) ** 2 for key in OUTCOMES))
    correct = sum(row["is_correct"] for row in rows)
    return {"overall_accuracy": round(correct / len(rows) * 100, 2) if rows else None,
        "total_predictions": len(rows), "correct_predictions": correct,
        "log_loss": sum(losses) / len(losses) if losses else None,
        "brier_score": sum(briers) / len(briers) if briers else None,
        "by_league": [aggregate(name, values, "league") for name, values in groups.items()],
        "by_confidence": [aggregate(name, values, "confidence") for name, values in tiers.items()],
        "recent_form": [{"match_id": row["match_id"], "teams": f"{row['home_team']} vs {row['away_team']}",
            "date": utc(row["date"]), "predicted": row["predicted_winner"], "actual": row["result"], "correct": row["is_correct"]} for row in rows[:10]],
        "excluded": excluded, "evaluation_basis": "latest_valid_pre_kickoff_per_fixture",
        "bookmaker_baseline": None, "calibration": None,
        "evidence_note": "Pre-kickoff timestamps are verified; training cutoff and input provenance were not recorded. These statistics do not establish bookmaker advantage.",
        "sample_start": utc(min(row["date"] for row in rows)) if rows else None,
        "sample_end": utc(max(row["date"] for row in rows)) if rows else None}
