"""Durable gateway behavior and local measurements in the disposable auth DB."""

import asyncio
import json
import math
import platform
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))


def verify(
    base, token, destination, stream, request, check, source=None, reader_bases=None
):
    import api.db as databases
    from api.main import app
    from generate_gateway_routes import routes
    from sqlalchemy import create_engine
    from sync.gateway import claim, execute, run_one
    from sync.gateway_execute import dispatch

    check(
        routes()
        == json.loads((ROOT / "pipeline/sync/gateway_routes.json").read_text()),
        "Gateway allowlist covers the exact source route table",
    )
    remote = psycopg2.connect(destination)
    original = databases.engine, databases.heritage_engine
    engine = create_engine(
        destination,
        connect_args={"options": "-c search_path=gateway_test,public -c timezone=UTC"},
    )
    heritage = create_engine(destination)
    source_kind = "synthetic_contract"
    try:
        rows = []
        if source:
            source_connection = psycopg2.connect(source)
            try:
                with source_connection, source_connection.cursor() as cursor:
                    cursor.execute("SELECT to_regclass('public.matches')")
                    if cursor.fetchone()[0]:
                        cursor.execute(
                            "SELECT match_id,competition,date,home_team,away_team,home_score,away_score,status FROM matches ORDER BY date DESC NULLS LAST,match_id DESC LIMIT 1000"
                        )
                        rows = cursor.fetchall()
                        if rows:
                            source_kind = "captured_local_fixture_rows"
            finally:
                source_connection.close()
        if not rows:
            from datetime import UTC, datetime

            rows = [
                (
                    i,
                    "Test League",
                    datetime.now(UTC),
                    f"Test home {i}",
                    f"Test away {i}",
                    None,
                    None,
                    "SCHEDULED",
                )
                for i in range(1, 1001)
            ]
        with remote, remote.cursor() as cursor:
            cursor.execute("""CREATE SCHEMA gateway_test;
                CREATE TABLE gateway_test.matches(match_id INTEGER PRIMARY KEY,competition TEXT,date TIMESTAMP,
                    home_team TEXT,away_team TEXT,home_score INTEGER,away_score INTEGER,status TEXT);
                CREATE TABLE gateway_test.odds(id SERIAL PRIMARY KEY,match_id INTEGER,home_win FLOAT,draw FLOAT,away_win FLOAT);
                CREATE TABLE gateway_test.predictions(id SERIAL PRIMARY KEY,match_id INTEGER,winner TEXT,home_prob FLOAT,
                    draw_prob FLOAT,away_prob FLOAT,model_version TEXT,created_at TIMESTAMP)""")
            execute_values(cursor, "INSERT INTO gateway_test.matches VALUES %s", rows)
            cursor.execute(
                "INSERT INTO gateway_test.odds(match_id,home_win,draw,away_win) SELECT match_id,2.1,3.2,3.8 FROM gateway_test.matches"
            )
        databases.engine, databases.heritage_engine = engine, heritage
        check(
            execute(
                {
                    "method": "POST",
                    "path": "sport-models/preview",
                    "body": {},
                    "query": [],
                }
            )["status"]
            == 422,
            "The isolated child executor must preserve actual Python validation without a listening HTTP server",
        )
        prefix = "/api/v1/pipeline/"
        expected = {}

        def executor(envelope):
            value = asyncio.run(dispatch(envelope, app, raise_app_exceptions=True))
            expected[envelope["path"]] = value
            return value

        def publish_one():
            result = run_one(remote, stream, executor, raise_errors=True)
            check(
                result["gateway"] == "published",
                f"Actual Python adapter must publish its response: {result}",
            )

        for path in ("matches?limit=1000", "health"):
            pending_status, pending_body = request(base, prefix + path, token=token)
            check(
                pending_status == 202,
                f"Unpublished reads are explicitly pending: {pending_status}, {pending_body}",
            )
            publish_one()
            status, body = request(base, prefix + path, token=token)
            check(
                status == expected[path.split("?")[0]]["status"]
                and body == expected[path.split("?")[0]]["body"],
                "Published response must preserve the actual Python JSON",
            )
        # The worker is not called during subsequent reads or benchmarks.
        samples = []

        def measured(index):
            start = time.perf_counter()
            target = (
                base
                if concurrency == 1 or not reader_bases
                else reader_bases[index % len(reader_bases)]
            )
            status, body = request(target, prefix + "matches?limit=1000", token=token)
            return (
                (time.perf_counter() - start) * 1000,
                status,
                len(body) if isinstance(body, list) else 0,
            )

        for concurrency in (1, 4):
            count = 40 if concurrency == 1 else 160
            if concurrency == 4 and reader_bases:
                for target in reader_bases:
                    check(
                        request(target, prefix + "matches?limit=1000", token=token)[0]
                        == 200,
                        "Independent API instances read the same snapshot",
                    )
            with ThreadPoolExecutor(max_workers=concurrency) as executor_pool:
                measurements = list(executor_pool.map(measured, range(count)))
            times = sorted(item[0] for item in measurements)
            check(
                all(item[1] == 200 for item in measurements),
                "Snapshot benchmark must have zero HTTP errors",
            )
            samples.append(
                {
                    "concurrency": concurrency,
                    "api_processes": 1
                    if concurrency == 1
                    else len(reader_bases or [base]),
                    "samples": len(times),
                    "errors": 0,
                    "p50_ms": statistics.median(times),
                    "p95_ms": times[math.ceil(len(times) * 0.95) - 1],
                    "p99_ms": times[math.ceil(len(times) * 0.99) - 1],
                    "raw_ms": times,
                }
            )
        # Validation and errors pass through the existing interface without fabricated results.
        for path in ("sport-models/preview", "fpl/team/evaluate", "smart-assistant"):
            headers = {"Idempotency-Key": str(uuid.uuid4())}
            args = {
                "method": "POST",
                "data": {},
                "token": token,
                "extra_headers": headers,
            }
            check(
                request(base, prefix + path, **args)[0] == 202,
                "Compute requests are durable",
            )
            publish_one()
            check(
                request(base, prefix + path, **args)[0] == 422,
                "Original Pydantic validation must survive publication",
            )
        check(
            request(
                base,
                prefix + "sport-models/preview",
                method="POST",
                data={},
                token=token,
            )[0]
            == 428,
            "Compute requests require idempotency",
        )
        check(
            request(
                base, prefix + "predictions/run-pipeline", method="POST", token=token
            )[0]
            == 403,
            "Collection/training remains administrative",
        )
        check(
            request(base, prefix + "does-not-exist", token=token)[0] == 404,
            "Unapproved routes are never queued",
        )
        check(
            request(
                base,
                prefix + "sport-models/preview",
                method="OPTIONS",
                extra_headers={
                    "Origin": "https://web.example.test",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                },
            )[0]
            == 200,
            "Browser preflight permits the idempotency header",
        )
        check(
            request(base, "/api/v1/chat/health", token=token)[0] == 200,
            "Legacy chat health no longer needs Node HTTP",
        )
        check(
            request(
                base,
                "/api/v1/chat",
                method="POST",
                token=token,
                data={"prompt": "Hello"},
            )[0]
            == 200,
            "Legacy prompt contract uses Rust RAG",
        )
        # A successful persisted calculation must be published once, including retries.
        with remote, remote.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.ev_bets")
            before = cursor.fetchone()[0]
        calculation = {
            "method": "POST",
            "token": token,
            "extra_headers": {"Idempotency-Key": str(uuid.uuid4())},
            "data": {
                "market": "h2h",
                "selection": "home",
                "odds": 2.0,
                "stake": 1.0,
                "true_probability": 0.55,
            },
        }
        check(
            request(base, prefix + "intelligence/ev", **calculation)[0] == 202,
            "Persisting EV computation is queued",
        )
        publish_one()
        for _ in range(2):
            status, value = request(base, prefix + "intelligence/ev", **calculation)
            check(
                status == 200 and abs(value["expected_value"] - 0.1) < 1e-12,
                "EV response preserves Python numerical behavior",
            )
        with remote, remote.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.ev_bets")
            check(
                cursor.fetchone()[0] == before + 1,
                "Polling a completed calculation must not insert a duplicate",
            )
        for path in (
            "intelligence/ev-bets?limit=1",
            "intelligence/devigged-odds?limit=1",
            "intelligence/arbitrage?limit=1",
        ):
            check(
                request(base, "/api/v1/" + path, token=token)[0] == 202,
                "Native intelligence reads await their source publication",
            )
            publish_one()
            status, body = request(base, "/api/v1/" + path, token=token)
            check(
                status == 200 and isinstance(body, list),
                "Native intelligence response retains its array contract",
            )
            if path.startswith("intelligence/ev-bets"):
                check(
                    len(body) == 1
                    and isinstance(body[0]["stake"], str)
                    and float(body[0]["stake"]) == 1.0,
                    "Published EV rows preserve fixed-precision decimal strings and source IDs",
                )
        # Simulate death after claiming a write; an ambiguous write must never be replayed.
        nonce = str(uuid.uuid4())
        args = {
            "method": "POST",
            "data": {
                "market": "h2h",
                "selection": "home",
                "odds": 2.0,
                "stake": 1.0,
                "true_probability": 0.55,
            },
            "token": token,
            "extra_headers": {"Idempotency-Key": nonce},
        }
        check(
            request(base, prefix + "intelligence/ev", **args)[0] == 202,
            "Persisting calculations are durable side effects",
        )
        job = claim(remote, stream)
        check(
            job and job["side_effect"],
            "Persisting calculations must not be classified read-only",
        )
        with remote, remote.cursor() as cursor:
            cursor.execute(
                "UPDATE published.gateway_jobs SET lease_until=NOW()-INTERVAL '1 second' WHERE id=%s",
                (job["id"],),
            )
        check(
            claim(remote, stream) is None,
            "Expired side-effect lease must not execute twice",
        )
        check(
            request(base, prefix + "intelligence/ev", **args)[0] == 503,
            "Ambiguous write outcome is unavailable",
        )
        altered = {**args, "data": {**args["data"], "stake": 2.0}}
        check(
            request(base, prefix + "intelligence/ev", **altered)[0] == 409,
            "Reusing a nonce with a different body must conflict",
        )
        # Read leases can be recovered and stale workers cannot publish.
        check(
            request(base, prefix + "matches?limit=17", token=token)[0] == 202,
            "Filtered snapshot has its own identity",
        )
        old = claim(remote, stream)
        with remote, remote.cursor() as cursor:
            cursor.execute(
                "UPDATE published.gateway_jobs SET lease_until=NOW()-INTERVAL '1 second' WHERE id=%s",
                (old["id"],),
            )
        publish_one()
        check(
            request(base, prefix + "matches?limit=17", token=token)[0] == 200,
            "Expired read leases recover",
        )
        with remote, remote.cursor() as cursor:
            cursor.execute(
                "SELECT request_key,request FROM published.gateway_jobs WHERE request->>'path'='matches' AND state='completed' ORDER BY created_at LIMIT 1"
            )
            key, envelope = cursor.fetchone()
            cursor.execute(
                "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT j.id,j.state,j.response_status,j.response,j.generated_at,j.fresh_until FROM published.gateway_jobs j JOIN published.sources s USING(stream_id) WHERE j.stream_id=%s AND j.request_key=%s AND s.enabled AND j.state='completed' AND j.fresh_until>NOW()",
                (stream, key),
            )
            plan = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE published.gateway_jobs SET fresh_until=NOW()-INTERVAL '1 second' WHERE request_key=%s",
                (key,),
            )
        query = "&".join(k + "=" + v for k, v in envelope["query"])
        check(
            request(base, prefix + "matches?" + query, token=token)[0] == 202,
            "Expired snapshots are not silently served",
        )
        with remote, remote.cursor() as cursor:
            cursor.execute(
                "UPDATE published.sources SET enabled=FALSE WHERE stream_id=%s",
                (stream,),
            )
        check(
            request(base, prefix + "health", token=token)[0] == 503,
            "Disabled sources cannot serve cached results",
        )
        with remote, remote.cursor() as cursor:
            cursor.execute(
                "UPDATE published.sources SET enabled=TRUE WHERE stream_id=%s",
                (stream,),
            )
        from verify_gateway_permissions import verify as verify_permissions

        permissions = verify_permissions(destination, stream, executor, check)
        artifact = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "percentile_method": "nearest rank; sample counts 40 and 160, without tail extrapolation",
            "scope": "local warm durable gateway snapshot reads; worker stopped",
            "dataset": source_kind,
            "fixture_rows": len(rows),
            "odds": "synthetic contract quotes",
            "workloads": samples,
            "query_plan": plan,
            "permissions": permissions,
            "neon_tls_or_hosted_cold_start_measured": False,
        }
        directory = ROOT / ".release/gateway-verification"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "performance.json").write_text(
            json.dumps(artifact, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "durable_gateway_http_parity": True,
                    "durable_gateway_lease_recovery": True,
                    "durable_gateway_write_replay_blocked": True,
                    "local_snapshot_measurements": len(samples),
                }
            )
        )
    finally:
        databases.engine, databases.heritage_engine = original
        engine.dispose()
        heritage.dispose()
        remote.close()
