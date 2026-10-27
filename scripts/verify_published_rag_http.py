"""RAG contracts inside the auth harness's disposable loopback database only."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
from psycopg2.extras import Json


def verify(base, token, destination, stream, request, check):
    route = "/api/v1/ai-picks/chat"
    now = datetime.now(UTC)
    day = (now + timedelta(days=8)).date().isoformat()
    body = {
        "sport": "Football",
        "messages": [{"role": "user", "content": f"TailClub on {day}"}],
    }

    def chat(data=None):
        status, result = request(
            base, route, method="POST", token=token, data=data or body
        )
        check(status == 200, f"Published RAG must respond (HTTP {status})")
        return result

    check(
        request(base, route, method="POST", data=body)[0] == 401,
        "Chat requires authentication",
    )
    connection = psycopg2.connect(destination)
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT payload->>'model_version' FROM published.records WHERE stream_id=%s AND dataset='model_metadata'",
                (stream,),
            )
            model = cursor.fetchone()[0]
            for index in range(250):
                payload = {
                    "schema_version": 1,
                    "sport": "Football",
                    "local_match_id": 1000 + index,
                    "fixture": {
                        "match_id": 1000 + index,
                        "home_team": "TailClub" if index == 249 else "OtherClub",
                        "away_team": "Visitors",
                        "competition": "Premier League",
                        "date": day + "T12:00:00Z",
                        "status": "SCHEDULED",
                        "result": None,
                    },
                    "prediction": {
                        "match_id": 1000 + index,
                        "home_prob": 0.55,
                        "draw_prob": 0.25,
                        "away_prob": 0.2,
                        "model_version": model,
                        "created_at": now.isoformat(),
                    },
                    "quotes": [
                        {
                            "bookmaker": name,
                            "home_win": 2.0,
                            "updated_at": timestamp.isoformat(),
                        }
                        for name, timestamp in [
                            ("recent", now),
                            ("expired", now - timedelta(days=2)),
                            ("future", now + timedelta(hours=1)),
                        ]
                    ],
                }
                cursor.execute(
                    """INSERT INTO published.records(stream_id,dataset,record_key,version,payload,changed_at,content_hash)
                    VALUES(%s,'fixture_bundle',%s,1,%s,NOW(),%s)""",
                    (stream, f"rag-test:{index:04d}", Json(payload), "0" * 64),
                )
        body["request_id"] = str(uuid.uuid4())
        result = chat()
        reply = result["reply"]
        picks = [value for value in reply["evidence"] if value["kind"] == "prediction"]
        check(
            reply["prediction_evidence_available"] is True and len(picks) == 1,
            "RAG finds the named team beyond page two",
        )
        pick = picks[0]
        check(
            pick["match_id"] == 1249 and pick["home_prob"] == 0.55,
            "Published probabilities must be preserved",
        )
        check(
            pick["source"] == f"published:{stream}:rag-test:0249"
            and pick["freshness"]["state"] == "fresh",
            "RAG must carry publication provenance",
        )
        check(
            [q["bookmaker"] for q in pick["quotes"]] == ["recent"],
            "RAG excludes expired and future quotes",
        )
        check(chat() == result, "Request replay preserves the saved answer")
        status, history = request(
            base,
            "/api/v1/ai-picks/conversations/" + result["conversation_id"],
            token=token,
        )
        check(
            status == 200 and len(history) == 2,
            "Chat history persists without duplicate retries",
        )
        followup = {
            "sport": "Football",
            "conversation_id": result["conversation_id"],
            "messages": [{"role": "user", "content": "What about the draw?"}],
        }
        followup_reply = chat(followup)["reply"]
        check(
            any(p.get("match_id") == 1249 for p in followup_reply["evidence"]),
            "Follow-ups inherit the named team",
        )
        for mutation in [
            "UPDATE published.sources SET enabled=FALSE WHERE stream_id=%s",
            "UPDATE published.records SET deleted=TRUE WHERE stream_id=%s AND dataset='model_metadata'",
        ]:
            with connection, connection.cursor() as cursor:
                cursor.execute(mutation, (stream,))
            fresh_request = {**body, "request_id": str(uuid.uuid4())}
            unavailable = chat(fresh_request)["reply"]
            check(
                unavailable["prediction_evidence_available"] is False
                and not any(p["kind"] == "prediction" for p in unavailable["evidence"]),
                "Disabled/missing model must remove prediction evidence",
            )
            with connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE published.sources SET enabled=TRUE WHERE stream_id=%s",
                    (stream,),
                )
        with connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE published.records SET deleted=FALSE WHERE stream_id=%s AND dataset='model_metadata'",
                (stream,),
            )
            cursor.execute(
                "UPDATE published.records SET deleted=TRUE WHERE stream_id=%s AND dataset='fixture_bundle'",
                (stream,),
            )
        empty = chat({**body, "request_id": str(uuid.uuid4())})["reply"]
        check(
            empty["prediction_evidence_available"] is True
            and not any(p["kind"] == "prediction" for p in empty["evidence"]),
            "Withdrawal yields empty evidence from an available source",
        )
    finally:
        connection.close()
