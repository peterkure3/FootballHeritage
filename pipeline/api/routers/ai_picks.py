"""AI Picks from current stored model predictions and observed odds."""

from datetime import date as Date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.ai_picks import build_picks
from api.db import get_db_connection
from config import MODEL_VERSION

router = APIRouter()


@router.get("/ai-picks")
def generate_ai_picks(
    competition: str | None = None,
    date: Date | None = None,
    limit: int = Query(10, ge=1, le=20),
):
    # Filter fixtures before ranking; only use the active model and fresh, pre-kickoff evidence.
    query = text("""
        SELECT m.match_id, m.home_team, m.away_team, m.competition, m.date AT TIME ZONE 'UTC' AS match_date,
               p.home_prob, p.draw_prob, p.away_prob, p.model_version,
               p.created_at AT TIME ZONE 'UTC' AS prediction_created_at,
               COALESCE(q.quotes, '[]'::json) AS quotes
        FROM matches m
        JOIN LATERAL (
            SELECT * FROM predictions p WHERE p.match_id=m.match_id AND p.model_version=:version
            ORDER BY p.created_at DESC, p.id DESC LIMIT 1
        ) p ON TRUE
        LEFT JOIN LATERAL (
            SELECT json_agg(latest) AS quotes FROM (
                SELECT DISTINCT ON (o.bookmaker) o.bookmaker, o.home_win, o.draw, o.away_win,
                    o.updated_at AT TIME ZONE 'UTC' AS updated_at
                FROM odds o WHERE o.match_id=m.match_id
                    AND o.updated_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
                    AND o.updated_at <= (NOW() AT TIME ZONE 'UTC')
                ORDER BY o.bookmaker, o.updated_at DESC, o.id DESC
            ) latest
        ) q ON TRUE
        WHERE m.date > (NOW() AT TIME ZONE 'UTC')
          AND m.date <= (NOW() AT TIME ZONE 'UTC') + INTERVAL '30 days'
          AND m.result IS NULL
          AND UPPER(COALESCE(m.status,'')) NOT IN ('FINISHED','CANCELLED','CANCELED','POSTPONED','IN_PLAY','PAUSED')
          AND p.created_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
          AND p.created_at <= (NOW() AT TIME ZONE 'UTC')
          AND (:competition IS NULL OR m.competition = :competition
               OR m.competition = 'UEFA ' || :competition)
          AND (CAST(:date AS DATE) IS NULL OR m.date::date = CAST(:date AS DATE))
    """)
    try:
        with get_db_connection().connect() as conn:
            rows = [dict(row) for row in conn.execute(query, {
                "version": MODEL_VERSION, "competition": competition, "date": date,
            }).mappings()]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="AI Picks prediction database is unavailable")
    picks = build_picks(rows, limit)
    return {
        "picks": picks,
        "summary": {
            "fixtures_considered": len(rows),
            "value_picks": sum(p["pick_type"] == "value" for p in picks),
            "prediction_picks": sum(p["pick_type"] == "prediction" for p in picks),
            "message": "Predictions ranked from the active model." if picks else
                "No recent model predictions match these filters. Run the prediction pipeline or choose another date or competition.",
        },
        "provenance": {
            "model": MODEL_VERSION, "criterion": "value_edge_then_model_probability",
            "min_edge": 0.05, "max_evidence_age_hours": 24, "reference_stake_units": 1,
            "match_date_timezone": "UTC", "odds_source": "stored_bookmaker_quotes",
        },
    }
