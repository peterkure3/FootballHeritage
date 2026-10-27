"""Commit-safe publisher: local lock -> destination commit -> local acknowledgement."""

import argparse
import json
import os
import random
import signal
import threading
from datetime import UTC, datetime

import psycopg2
from psycopg2.extras import Json, RealDictCursor, execute_values

from .neon_client import connect, fingerprint
from .publisher import validate_record

LOCK_ID = 71604261026
MAX_ATTEMPTS = 12


def retry_delay(attempt: int, random_value: float | None = None) -> float:
    """Bounded full jitter; durable next-attempt time is stored by PostgreSQL."""
    if attempt < 1:
        raise ValueError("Retry attempt must be positive")
    return min(300, 2 ** min(attempt, 9)) * (
        random.random() if random_value is None else random_value
    )


class ConflictError(ValueError):
    """Same event/version identity was reused with different content."""

    def __init__(self, event_id):
        super().__init__("Publication identity conflict")
        self.event_id = str(event_id)


def deliver(remote, events: list[dict]) -> None:
    """One bounded destination transaction; never acknowledges local events."""
    if not events:
        return
    streams = {str(event["stream_id"]) for event in events}
    if len(streams) != 1:
        raise ValueError("A batch must belong to one source stream")
    stream = streams.pop()
    for event in events:
        validate_record(event["dataset"], event["record_key"], event["payload"])
        event["content_hash"] = fingerprint(event)
    with remote, remote.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (stream,)
        )
        cursor.execute(
            "SELECT enabled FROM published.sources WHERE stream_id=%s FOR SHARE",
            (stream,),
        )
        source = cursor.fetchone()
        if not source or not source[0]:
            raise PermissionError("Publication source is not enabled")
        cursor.execute(
            "SELECT event_id::text,stream_id::text,content_hash FROM published.receipts WHERE event_id=ANY(%s::uuid[])",
            ([str(event["event_id"]) for event in events],),
        )
        receipts = {row[0]: row[1:] for row in cursor.fetchall()}
        pending = []
        for event in events:
            receipt = receipts.get(str(event["event_id"]))
            if receipt:
                if receipt != (stream, event["content_hash"]):
                    raise ConflictError(event["event_id"])
            else:
                pending.append(event)
        # Never send multiple versions of a key through one INSERT statement.
        latest = {}
        for event in pending:
            key = (event["dataset"], event["record_key"])
            if key not in latest or event["version"] > latest[key]["version"]:
                latest[key] = event
        for event in sorted(
            latest.values(), key=lambda e: (e["dataset"], e["record_key"])
        ):
            cursor.execute(
                """SELECT version,content_hash FROM published.records
                WHERE stream_id=%s AND dataset=%s AND record_key=%s FOR UPDATE""",
                (stream, event["dataset"], event["record_key"]),
            )
            existing = cursor.fetchone()
            if (
                existing
                and existing[0] == event["version"]
                and existing[1] != event["content_hash"]
            ):
                raise ConflictError(event["event_id"])
        if latest:
            execute_values(
                cursor,
                """INSERT INTO published.records
                (stream_id,dataset,record_key,version,payload,deleted,changed_at,content_hash)
                VALUES %s ON CONFLICT(stream_id,dataset,record_key) DO UPDATE SET
                version=EXCLUDED.version,payload=EXCLUDED.payload,deleted=EXCLUDED.deleted,
                changed_at=EXCLUDED.changed_at,content_hash=EXCLUDED.content_hash,published_at=NOW()
                WHERE published.records.version < EXCLUDED.version""",
                [
                    (
                        stream,
                        e["dataset"],
                        e["record_key"],
                        e["version"],
                        Json(e["payload"]),
                        e["deleted"],
                        e["changed_at"],
                        e["content_hash"],
                    )
                    for e in latest.values()
                ],
                page_size=100,
            )
        if pending:
            execute_values(
                cursor,
                """INSERT INTO published.receipts(event_id,stream_id,content_hash)
                VALUES %s""",
                [(str(e["event_id"]), stream, e["content_hash"]) for e in pending],
                page_size=100,
            )
        cursor.execute(
            "UPDATE published.sources SET last_success_at=NOW() WHERE stream_id=%s",
            (stream,),
        )
    # Exiting the connection context commits. Do not move acknowledgement above it.


def acknowledge(local, events: list[dict]) -> None:
    with local, local.cursor() as cursor:
        cursor.execute(
            "UPDATE fh_sync.outbox SET completed_at=NOW(),error_code=NULL WHERE id=ANY(%s)",
            ([event["id"] for event in events],),
        )
        cursor.execute(
            "UPDATE fh_sync.status SET last_success_at=NOW(),error_code=NULL"
        )


def run_batch(local, remote, batch_size: int = 100) -> dict:
    if not 1 <= batch_size <= 1000:
        raise ValueError("Batch size must be between 1 and 1000")
    events = []
    # Session-scoped lock spans both commits, so no concurrent local workers can
    # reorder writes. Process death or connection close releases it automatically.
    with local.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
        acquired = cursor.fetchone()[0]
    local.commit()
    if not acquired:
        return {"outcome": "busy", "count": 0}
    try:
        with local, local.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("UPDATE fh_sync.status SET last_attempt_at=NOW()")
            cursor.execute(
                """WITH candidates AS (
                    SELECT id,payload_bytes FROM fh_sync.outbox
                    WHERE completed_at IS NULL AND dead_at IS NULL AND available_at<=NOW()
                    ORDER BY id LIMIT %s
                ), bounded AS (
                    SELECT id,sum(payload_bytes) OVER (ORDER BY id) AS total_bytes FROM candidates
                ) SELECT o.* FROM fh_sync.outbox o JOIN bounded b ON b.id=o.id
                    WHERE b.total_bytes<=16777216 ORDER BY o.id FOR UPDATE OF o SKIP LOCKED""",
                (batch_size,),
            )
            events = [dict(row) for row in cursor.fetchall()]
        if not events:
            return {"outcome": "idle", "count": 0}
        try:
            deliver(remote, events)
        except (psycopg2.Error, ValueError, TypeError, PermissionError) as exc:
            # Never print database error text, DSNs or payloads.
            code = getattr(exc, "pgcode", None) or type(exc).__name__
            if not remote.closed:
                remote.rollback()
            with local, local.cursor() as cursor:
                for event in events:
                    attempts = event["attempts"] + 1
                    permanent = isinstance(exc, (ValueError, TypeError)) and (
                        not isinstance(exc, ConflictError)
                        or str(event["event_id"]) == exc.event_id
                    )
                    cursor.execute(
                        """UPDATE fh_sync.outbox SET attempts=%s,error_code=%s,
                        available_at=NOW()+(%s * INTERVAL '1 second'),
                        dead_at=CASE WHEN %s THEN NOW() ELSE NULL END WHERE id=%s""",
                        (
                            attempts,
                            code,
                            retry_delay(attempts),
                            permanent or attempts >= MAX_ATTEMPTS,
                            event["id"],
                        ),
                    )
                cursor.execute("UPDATE fh_sync.status SET error_code=%s", (code,))
            return {
                "outcome": "retry_or_dead_letter",
                "count": len(events),
                "error_code": code,
            }
        acknowledge(local, events)
        return {"outcome": "published", "count": len(events)}
    finally:
        local.rollback()
        with local.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
        local.commit()


def status(local) -> dict:
    with local, local.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""SELECT s.*,
            (SELECT stream_id::text FROM fh_sync.identity) AS stream_id,
            (SELECT count(*) FROM fh_sync.outbox WHERE completed_at IS NULL AND dead_at IS NULL) AS outstanding,
            (SELECT count(*) FROM fh_sync.outbox WHERE dead_at IS NOT NULL) AS dead_letters,
            (SELECT min(changed_at) FROM fh_sync.outbox WHERE completed_at IS NULL AND dead_at IS NULL) AS oldest_pending_at
            FROM fh_sync.status s""")
        result = dict(cursor.fetchone())
        cursor.execute(
            "SELECT to_regclass('fh_sync.dirty_fixtures') IS NOT NULL AS present"
        )
        if cursor.fetchone()["present"]:
            cursor.execute(
                "SELECT count(*) AS blocked FROM fh_sync.dirty_fixtures WHERE blocked_at IS NOT NULL"
            )
            result["blocked_projections"] = cursor.fetchone()["blocked"]
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 1000 or not 0.1 <= args.poll_seconds <= 300:
        parser.error("Invalid batch size or poll interval")
    stop = threading.Event()
    for name in ("SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, name), lambda *_: stop.set())
    local = remote = None
    connection_attempts = 0
    try:
        while not stop.is_set():
            try:
                if local is None or local.closed:
                    local = connect(os.environ["SYNC_LOCAL_DATABASE_URL"])
                if args.status:
                    print(json.dumps(status(local), default=str))
                    return 0
                if remote is None or remote.closed:
                    remote = connect(os.environ["SYNC_NEON_DATABASE_URL"], remote=True)
                result = run_batch(local, remote, args.batch_size)
                connection_attempts = 0
                print(
                    json.dumps({"at": datetime.now(UTC).isoformat(), **result}),
                    flush=True,
                )
                if args.once:
                    return (
                        0 if result["outcome"] in ("published", "idle", "busy") else 1
                    )
                if result["outcome"] != "published":
                    stop.wait(args.poll_seconds)
            except (psycopg2.Error, OSError) as exc:
                connection_attempts += 1
                print(
                    json.dumps(
                        {
                            "outcome": "connection_failure",
                            "error_code": type(exc).__name__,
                        }
                    ),
                    flush=True,
                )
                for connection in (remote, local):
                    if connection is not None:
                        connection.close()
                remote = local = None
                if args.once or args.status:
                    return 1
                stop.wait(max(1, retry_delay(connection_attempts)))
    finally:
        for connection in (remote, local):
            if connection is not None:
                connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
