"""Incrementally project existing football outputs; no inference or model changes."""

import argparse
import json
import math
import os

from psycopg2.extras import RealDictCursor

from .neon_client import connect
from .publisher import publish


def bootstrap(local) -> None:
    """Explicit first-run/backfill only; normal cycles read the durable dirty queue."""
    with local, local.cursor() as cursor:
        cursor.execute("""INSERT INTO fh_sync.dirty_fixtures(match_id)
                SELECT match_id FROM public.matches ON CONFLICT(match_id) DO NOTHING""")


def valid_prediction(prediction: dict | None) -> bool:
    if prediction is None:
        return False
    probabilities = [
        prediction.get(key) for key in ("home_prob", "draw_prob", "away_prob")
    ]
    return (
        all(
            isinstance(p, (float, int)) and math.isfinite(p) and 0 <= p <= 1
            for p in probabilities
        )
        and abs(sum(probabilities) - 1) < 0.01
    )


def project(local, model_version: str, batch_size: int = 100) -> dict:
    if not model_version or not 1 <= batch_size <= 1000:
        raise ValueError("A model version and bounded batch size are required")
    with local, local.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'UTC'")
        cursor.execute(
            """SELECT match_id FROM fh_sync.dirty_fixtures WHERE blocked_at IS NULL ORDER BY match_id
            LIMIT %s FOR UPDATE SKIP LOCKED""",
            (batch_size,),
        )
        ids = [row["match_id"] for row in cursor.fetchall()]
        if not ids:
            return {"processed": 0, "published": 0, "missing_source": 0, "invalid": 0}
        cursor.execute(
            """SELECT m.match_id,m.sport_type,
            jsonb_build_object('match_id',m.match_id,'competition',m.competition,
                'date',m.date AT TIME ZONE 'UTC','home_team',m.home_team,'away_team',m.away_team,
                'home_score',m.home_score,'away_score',m.away_score,'status',m.status,'result',m.result) AS fixture,
            CASE WHEN p.id IS NULL THEN NULL ELSE jsonb_build_object(
                'match_id',m.match_id,'model_version',p.model_version,'winner',p.winner,
                'home_prob',p.home_prob,'draw_prob',p.draw_prob,'away_prob',p.away_prob,
                'created_at',p.created_at AT TIME ZONE 'UTC') END AS prediction,
            COALESCE(q.quotes,'[]'::jsonb) AS quotes
            FROM public.matches m
            LEFT JOIN LATERAL (SELECT * FROM public.predictions p
                WHERE p.match_id=m.match_id AND p.model_version=%s
                ORDER BY p.created_at DESC,p.id DESC LIMIT 1) p ON TRUE
            LEFT JOIN LATERAL (SELECT jsonb_agg(latest ORDER BY latest.bookmaker) AS quotes FROM (
                SELECT DISTINCT ON (bookmaker) bookmaker,home_win,draw,away_win,
                    updated_at AT TIME ZONE 'UTC' AS updated_at
                FROM public.odds WHERE match_id=m.match_id
                    AND updated_at <= (NOW() AT TIME ZONE 'UTC')
                ORDER BY bookmaker,updated_at DESC NULLS LAST,id DESC) latest) q ON TRUE
            WHERE m.match_id=ANY(%s) ORDER BY m.match_id""",
            (model_version, ids),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        invalid_ids = []
        valid_rows = []
        for row in rows:
            prediction = row["prediction"]
            error_code = None
            if str(row["sport_type"]).strip().lower() not in ("football", "soccer"):
                error_code = "UNSUPPORTED_SPORT"
            elif prediction is not None and not valid_prediction(prediction):
                error_code = "INVALID_PREDICTION"
            if error_code:
                invalid_ids.append(row["match_id"])
                cursor.execute(
                    """UPDATE fh_sync.dirty_fixtures SET blocked_at=NOW(),error_code=%s
                    WHERE match_id=%s""",
                    (error_code, row["match_id"]),
                )
                continue
            valid_rows.append(row)
        if valid_rows:
            # Explicit operator-selected model; no inference from filenames or dates.
            # Manifest and bundles enter the same local transaction/outbox.
            publish(
                cursor,
                "model_metadata",
                "football:active-model",
                {
                    "schema_version": 1,
                    "sport": "Football",
                    "model_version": model_version,
                },
            )
        for row in valid_rows:
            publish(
                cursor,
                "fixture_bundle",
                f"football:legacy.matches:{row['match_id']}",
                {
                    "schema_version": 1,
                    "sport": "Football",
                    "source_namespace": "legacy.matches",
                    "local_match_id": row["match_id"],
                    "fixture": row["fixture"],
                    "prediction": row["prediction"],
                    "quotes": row["quotes"],
                },
            )
        # Missing source rows are NOT permission to delete a production record.
        cursor.execute(
            "DELETE FROM fh_sync.dirty_fixtures WHERE match_id=ANY(%s) AND blocked_at IS NULL",
            (ids,),
        )
    return {
        "processed": len(ids),
        "published": len(rows) - len(invalid_ids),
        "missing_source": len(ids) - len(rows),
        "invalid": len(invalid_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Explicit one-time enumeration of existing matches",
    )
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    local = connect(os.environ["SYNC_LOCAL_DATABASE_URL"])
    try:
        if args.bootstrap:
            bootstrap(local)
        while True:
            result = project(local, args.model_version, args.batch_size)
            print(json.dumps(result), flush=True)
            if not result["processed"]:
                break
        return 0
    finally:
        local.close()


if __name__ == "__main__":
    raise SystemExit(main())
