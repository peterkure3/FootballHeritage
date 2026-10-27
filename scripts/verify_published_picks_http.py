"""Synthetic HTTP contract checks, invoked only inside the disposable auth database."""

import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from api.ai_picks import build_picks


def equivalent(actual, expected):
    if isinstance(expected, dict):
        return all(
            key in actual and equivalent(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            equivalent(a, b) for a, b in zip(actual, expected)
        )
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isclose(
            actual, expected, rel_tol=1e-12, abs_tol=1e-12
        )
    return actual == expected


def verify(base, token, destination, stream, request, check):
    """No source/provider data, production records, or fabricated runtime fallback."""
    route = "/api/v1/ai-picks/generate"
    arguments = {"method": "POST", "data": {"sport": "Football", "limit": 20}}
    check(
        request(base, route, **arguments)[0] == 401,
        "AI Picks must require authentication",
    )
    check(
        request(base, route, token=token, **arguments)[0] == 503,
        "Missing active model must be unavailable",
    )
    now = datetime.now(UTC)
    version = "synthetic-http-contract-only"
    rows = []
    connection = psycopg2.connect(destination)
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO published.sources(stream_id,description) VALUES(%s,'disposable HTTP contract')",
                (stream,),
            )
            manifest = {
                "schema_version": 1,
                "sport": "Football",
                "model_version": version,
            }
            cursor.execute(
                """INSERT INTO published.records(stream_id,dataset,record_key,version,payload,changed_at,content_hash)
                VALUES(%s,'model_metadata','football:active-model',1,%s,NOW(),%s)""",
                (stream, Json(manifest), "0" * 64),
            )
            for index in range(165):
                probability = 0.4 + index / 10000
                predicted = now - timedelta(hours=25 if index == 160 else 1)
                fixture = {
                    "match_id": index + 1,
                    "home_team": f"Synthetic home {index}",
                    "away_team": f"Synthetic away {index}",
                    "competition": "Premier League",
                    "date": (now + timedelta(days=2)).isoformat(),
                    "result": None,
                    "status": "FINISHED" if index == 161 else "SCHEDULED",
                }
                prediction = {
                    "match_id": index + 1,
                    "model_version": "other-test-model" if index == 162 else version,
                    "home_prob": probability,
                    "draw_prob": 0.3,
                    "away_prob": 1 - probability - 0.3,
                    "created_at": (now + timedelta(hours=1)).isoformat()
                    if index == 163
                    else predicted.isoformat(),
                }
                if index == 164:
                    prediction["home_prob"] = 0.99
                quotes = [
                    {
                        "bookmaker": "synthetic-test-book",
                        "home_win": 3.0,
                        "draw": 2.0,
                        "away_win": 2.0,
                        "updated_at": predicted.isoformat(),
                    },
                    {
                        "bookmaker": "expired-test-book",
                        "home_win": 100.0,
                        "updated_at": (now - timedelta(hours=25)).isoformat(),
                    },
                    {
                        "bookmaker": "future-test-book",
                        "home_win": 100.0,
                        "updated_at": (now + timedelta(hours=1)).isoformat(),
                    },
                ]
                payload = {
                    "schema_version": 1,
                    "sport": "Football",
                    "local_match_id": index + 1,
                    "fixture": fixture,
                    "prediction": prediction,
                    "quotes": quotes,
                }
                cursor.execute(
                    """INSERT INTO published.records(stream_id,dataset,record_key,version,payload,changed_at,content_hash)
                    VALUES(%s,'fixture_bundle',%s,1,%s,NOW(),%s)""",
                    (
                        stream,
                        f"football:legacy.matches:{index + 1:04d}",
                        Json(payload),
                        "0" * 64,
                    ),
                )
                if index < 160:
                    rows.append(
                        {
                            "match_id": index + 1,
                            "home_team": fixture["home_team"],
                            "away_team": fixture["away_team"],
                            "competition": fixture["competition"],
                            "match_date": fixture["date"],
                            "model_version": version,
                            "prediction_created_at": predicted.isoformat(),
                            "home_prob": probability,
                            "draw_prob": 0.3,
                            "away_prob": 1 - probability - 0.3,
                            "quotes": quotes[:1],
                        }
                    )
        status, result = request(base, route, token=token, **arguments)
        check(
            status == 200,
            f"Published AI Picks must work with Python offline (HTTP {status})",
        )
        check(
            equivalent(result["picks"], build_picks(rows, 20)),
            "Rust HTTP picks must match the existing Python ranker across pages",
        )
        check(
            result["summary"]["fixtures_considered"] == 161,
            "Freshness/model/status filters must exclude ineligible evidence",
        )
        check(
            all(pick["freshness"]["state"] == "fresh" for pick in result["picks"]),
            "Published picks must carry freshness",
        )
        check(
            result["provenance"]["model"] == version,
            "Model provenance must come from the publication manifest",
        )
        run_id = result["id"]
        check(
            request(base, "/api/v1/ai-picks/" + run_id, token=token)[0] == 200,
            "Saved picks must remain retrievable",
        )
        empty = {
            **arguments,
            "data": {
                "sport": "Football",
                "date": (now + timedelta(days=10)).date().isoformat(),
            },
        }
        status, result = request(base, route, token=token, **empty)
        check(
            status == 200 and result["picks"] == [],
            "Expected missing predictions must return an empty result",
        )
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE published.sources SET enabled=FALSE WHERE stream_id=%s",
                (stream,),
            )
        check(
            request(base, route, token=token, **arguments)[0] == 503,
            "Disabled source must fail closed",
        )
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE published.sources SET enabled=TRUE WHERE stream_id=%s",
                (stream,),
            )
            cursor.execute(
                "UPDATE published.records SET deleted=TRUE WHERE dataset='fixture_bundle'"
            )
        status, result = request(base, route, token=token, **arguments)
        check(
            status == 200 and result["picks"] == [],
            "Withdrawn predictions must not produce picks",
        )
    finally:
        connection.close()
