"""Outbound-only durable computation worker; no provider/model implementation changes."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from .neon_client import connect

ROUTES = json.loads(Path(__file__).with_name("gateway_routes.json").read_text())
PREWARM = [
    ("intelligence/devigged-odds", []),
    ("intelligence/ev-bets", []),
    ("intelligence/arbitrage", []),
    ("health", []),
    ("matches", [["limit", "100"]]),
    ("prediction-dashboard/fixtures", [["page", "1"], ["page_size", "6"]]),
    ("prediction-dashboard/operations", []),
    ("prediction-dashboard/paper-trials", []),
    ("predictions/versions", []),
    ("sport-models", []),
    ("betting-intel", []),
    ("fpl/advice", []),
    ("ncaab/games", [["limit", "50"]]),
    ("suggested-parlays", []),
    ("best-value-bets", []),
]


def fresh_until(path, payload, evaluated_at, ttl_seconds):
    """Expire ranking views before any visible kickoff or evidence-age boundary."""
    deadline = evaluated_at + timedelta(seconds=ttl_seconds)
    market_view = path.startswith(
        (
            "betting-intel",
            "prediction-dashboard/fixtures",
            "predictions/upcoming",
            "predictions/value-bets",
        )
    ) or path in {"best-value-bets", "suggested-parlays", "ai-picks"}
    if not market_view:
        return deadline
    nodes = [payload]
    while nodes:
        node = nodes.pop()
        if isinstance(node, list):
            nodes.extend(node)
        elif isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, (list, dict)):
                    nodes.append(value)
                if not isinstance(value, str):
                    continue
                try:
                    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=UTC)
                except ValueError:
                    continue
                expiry = None
                if key in {
                    "date",
                    "match_date",
                    "kickoff",
                    "event_date",
                    "commence_time",
                }:
                    expiry = timestamp
                elif key in {"observed_at", "updated_at", "source_updated_at"}:
                    expiry = timestamp + timedelta(
                        seconds=1800 if path.startswith("betting-intel") else 86400
                    )
                elif key in {"prediction_created_at", "generated_at"}:
                    expiry = timestamp + timedelta(days=1)
                elif key == "snapshot_at" and path.startswith("betting-intel"):
                    expiry = timestamp + timedelta(seconds=1800)
                if expiry is not None and expiry >= evaluated_at:
                    deadline = min(deadline, expiry)
    return deadline


def contract(method, path):
    matches = [r for r in ROUTES if r["method"] == method]
    exact = next((r for r in matches if r["path"] == path), None)
    if exact:
        return exact
    return next(
        (
            r
            for r in matches
            if len(r["path"].split("/")) == len(path.split("/"))
            and all(
                a == b or (a.startswith("{") and b)
                for a, b in zip(r["path"].split("/"), path.split("/"))
            )
        ),
        None,
    )


def prewarm(remote, stream):
    """Refresh bounded default views proactively; filtered views are durable requests."""
    with remote, remote.cursor() as cursor:
        cursor.execute(
            "SELECT stream_id FROM published.sources WHERE stream_id=%s AND enabled",
            (stream,),
        )
        if not cursor.fetchone():
            return
        for path, query in PREWARM:
            rule = contract("GET", path)
            envelope = {
                "schema_version": 1,
                "method": "GET",
                "path": path,
                "query": query,
                "body": None,
                "ttl_seconds": rule["ttl_seconds"],
                "side_effect": False,
                "admin": False,
            }
            encoded = json.dumps(
                [None, None, envelope],
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            key = hashlib.sha256(encoded.encode()).hexdigest()
            cursor.execute(
                """INSERT INTO published.gateway_jobs(stream_id,request_key,id,request,side_effect)
                VALUES(%s,%s,%s,%s,FALSE) ON CONFLICT(stream_id,request_key) DO UPDATE
                SET state='queued',attempts=0,response=NULL,response_status=NULL,generated_at=NULL,fresh_until=NULL,created_at=NOW()
                WHERE (gateway_jobs.state='completed' AND gateway_jobs.fresh_until<NOW())
                    OR (gateway_jobs.state='failed' AND gateway_jobs.created_at<NOW()-INTERVAL '5 minutes')""",
                (stream, key, str(uuid.uuid4()), Json(envelope)),
            )


def claim(remote, stream):
    with remote, remote.cursor(cursor_factory=RealDictCursor) as cursor:
        # Never repeat a potentially committed side effect after a worker crash.
        cursor.execute(
            """UPDATE published.gateway_jobs SET state=CASE WHEN side_effect THEN 'indeterminate' ELSE 'failed' END
            WHERE stream_id=%s AND state='running' AND lease_until<NOW() AND (side_effect OR attempts>=3)""",
            (stream,),
        )
        cursor.execute(
            """UPDATE published.gateway_jobs SET state='failed' WHERE stream_id=%s
            AND state='queued' AND created_at<NOW()-INTERVAL '1 day'""",
            (stream,),
        )
        cursor.execute(
            """SELECT j.* FROM published.gateway_jobs j JOIN published.sources s USING(stream_id)
            WHERE j.stream_id=%s AND s.enabled AND (j.state='queued' OR
                (j.state='running' AND NOT j.side_effect AND j.lease_until<NOW() AND j.attempts<3))
            ORDER BY j.created_at,j.id FOR UPDATE OF j SKIP LOCKED LIMIT 1""",
            (stream,),
        )
        job = cursor.fetchone()
        if job is None:
            return None
        lease = str(uuid.uuid4())
        cursor.execute(
            """UPDATE published.gateway_jobs SET state='running',attempts=attempts+1,
            lease_token=%s,lease_until=NOW()+INTERVAL '5 minutes' WHERE id=%s""",
            (lease, job["id"]),
        )
        return {**job, "lease_token": lease}


def execute(envelope):
    """Hard process deadline bounds ML/provider stalls and releases all child resources."""
    python = os.getenv("SYNC_COMPUTE_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="fh-gateway-") as temporary:
        request_file, response_file = (
            Path(temporary) / "request.json",
            Path(temporary) / "response.json",
        )
        request_file.write_text(json.dumps(envelope, allow_nan=False), encoding="utf-8")
        subprocess.run(
            [
                python,
                "-m",
                "sync.gateway_execute",
                str(request_file),
                str(response_file),
            ],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            timeout=240,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if response_file.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Response exceeds publication limit")
        response = json.loads(response_file.read_text(encoding="utf-8"))
        if (
            not isinstance(response.get("status"), int)
            or not 200 <= response["status"] < 500
        ):
            raise ValueError("Computation did not return a publishable response")
        return response


def run_one(remote, stream, executor=execute, *, raise_errors=False):
    job = claim(remote, stream)
    if job is None:
        return {"gateway": "idle"}
    envelope = job["request"]
    rule = contract(envelope.get("method"), envelope.get("path", ""))
    try:
        if not rule or envelope.get("schema_version") != 1:
            raise ValueError("Unknown gateway contract")
        refresh = any(
            k == "refresh" and v not in ("false", "0", "") for k, v in envelope["query"]
        )
        if bool(job["side_effect"]) != bool(rule["side_effect"] or refresh):
            raise ValueError("Side effect classification mismatch")
        if bool(envelope.get("admin")) != bool(rule["admin"] or refresh):
            raise ValueError("Authorization classification mismatch")
        if envelope.get("admin"):
            with remote, remote.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM users WHERE id=%s AND is_active AND role IN ('admin','superadmin') AND (locked_until IS NULL OR locked_until<NOW())",
                    (job["owner_id"],),
                )
                if not cursor.fetchone():
                    raise ValueError("Administrator permission was revoked")
        evaluated_at = datetime.now(UTC)
        response = executor(envelope)
        if (
            not isinstance(response.get("status"), int)
            or not 200 <= response["status"] < 500
        ):
            raise ValueError("Unpublishable computation response")
        if len(json.dumps(response, allow_nan=False).encode()) > 8 * 1024 * 1024:
            raise ValueError("Response exceeds publication limit")
        with remote, remote.cursor() as cursor:
            cursor.execute(
                """UPDATE published.gateway_jobs j SET state='completed',response_status=%s,
                response=%s,generated_at=NOW(),fresh_until=%s,lease_until=NULL
                WHERE j.id=%s AND j.state='running' AND j.lease_token=%s AND j.lease_until>NOW()
                AND EXISTS(SELECT 1 FROM published.sources s WHERE s.stream_id=j.stream_id AND s.enabled)""",
                (
                    response["status"],
                    Json(response["body"]),
                    fresh_until(
                        envelope["path"],
                        response["body"],
                        evaluated_at,
                        rule["ttl_seconds"],
                    ),
                    job["id"],
                    job["lease_token"],
                ),
            )
            published = cursor.rowcount == 1
            if job["side_effect"] and response["status"] < 300:
                cursor.execute(
                    "UPDATE published.gateway_jobs SET fresh_until=NOW()-INTERVAL '1 millisecond' WHERE stream_id=%s AND owner_id IS NULL AND state='completed' AND NOT side_effect",
                    (stream,),
                )
            return {"gateway": "published" if published else "lease_lost"}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        with remote, remote.cursor() as cursor:
            cursor.execute(
                """UPDATE published.gateway_jobs SET state=CASE WHEN side_effect THEN 'indeterminate' ELSE 'failed' END,
                lease_until=NULL WHERE id=%s AND state='running' AND lease_token=%s""",
                (job["id"], job["lease_token"]),
            )
            if job["side_effect"]:
                cursor.execute(
                    "UPDATE published.gateway_jobs SET fresh_until=NOW()-INTERVAL '1 millisecond' WHERE stream_id=%s AND owner_id IS NULL AND state='completed' AND NOT side_effect",
                    (stream,),
                )
        if raise_errors:
            raise
        return {"gateway": "failed"}


def main():
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    load_dotenv(args.env, override=False)
    stream = str(uuid.UUID(os.environ["SYNC_GATEWAY_STREAM_ID"]))
    stop = threading.Event()
    for name in ("SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, name), lambda *_: stop.set())
    remote = None
    failures = 0
    prewarm_at = 0.0
    try:
        while not stop.is_set():
            try:
                if remote is None or remote.closed:
                    remote = connect(os.environ["SYNC_NEON_DATABASE_URL"], remote=True)
                    prewarm_at = 0.0
                if time.monotonic() >= prewarm_at:
                    prewarm(remote, stream)
                    prewarm_at = time.monotonic() + 30
                result = run_one(remote, stream)
                print(json.dumps(result), flush=True)
                failures = 0
                if args.once:
                    return int(result["gateway"] == "failed")
                if result["gateway"] == "idle":
                    stop.wait(2)
            except (psycopg2.Error, OSError, ValueError) as exc:
                print(
                    json.dumps(
                        {
                            "gateway": "connection_failed",
                            "error_code": type(exc).__name__,
                        }
                    ),
                    flush=True,
                )
                if remote is not None:
                    remote.close()
                remote = None
                failures += 1
                if args.once:
                    return 1
                stop.wait(min(60, 2 ** min(failures, 6)))
    finally:
        if remote is not None:
            remote.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
