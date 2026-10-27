"""Read-only, keyset-paginated reconciliation of approved publications."""

import argparse
import json
import os

from psycopg2.extras import RealDictCursor, execute_values

from .neon_client import connect, fingerprint


def reconcile(local, remote, page_size: int = 100):
    """Yield missing/stale/content conflicts and unexpected destination keys.

    Compare a quiescent stream for a cutover decision. A live producer/worker can
    legitimately change rows during pagination; repeat after draining the queue.
    Never repair data or alter checkpoints automatically.
    """
    if not 1 <= page_size <= 1000:
        raise ValueError("Page size must be between 1 and 1000")
    with local.cursor() as cursor:
        cursor.execute("SELECT stream_id::text FROM fh_sync.identity")
        stream = cursor.fetchone()[0]
    last = ("", "")
    while True:
        with local.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """SELECT * FROM fh_sync.records WHERE (dataset,record_key)>(%s,%s)
                ORDER BY dataset,record_key LIMIT %s""",
                (*last, page_size),
            )
            rows = [dict(row) for row in cursor.fetchall()]
        local.commit()
        if not rows:
            break
        with remote.cursor() as cursor:
            execute_values(
                cursor,
                """SELECT r.dataset,r.record_key,r.version,r.content_hash
                FROM published.records r JOIN (VALUES %s) AS k(stream_id,dataset,record_key)
                ON (r.stream_id,r.dataset,r.record_key)=(k.stream_id,k.dataset,k.record_key)""",
                [(stream, r["dataset"], r["record_key"]) for r in rows],
                template="(%s::uuid,%s,%s)",
                page_size=page_size,
            )
            targets = {(r[0], r[1]): r[2:] for r in cursor.fetchall()}
        remote.commit()
        for row in rows:
            key = (row["dataset"], row["record_key"])
            target = targets.get(key)
            row["stream_id"] = stream
            reason = (
                "missing"
                if target is None
                else (
                    "version_mismatch"
                    if target[0] != row["version"]
                    else "content_mismatch"
                    if target[1] != fingerprint(row)
                    else None
                )
            )
            if reason:
                yield {"dataset": key[0], "record_key": key[1], "reason": reason}
        last = (rows[-1]["dataset"], rows[-1]["record_key"])
    last = ("", "")
    while True:
        with remote.cursor() as cursor:
            cursor.execute(
                """SELECT dataset,record_key FROM published.records
                WHERE stream_id=%s AND (dataset,record_key)>(%s,%s)
                ORDER BY dataset,record_key LIMIT %s""",
                (stream, *last, page_size),
            )
            rows = cursor.fetchall()
        remote.commit()
        if not rows:
            break
        with local.cursor() as cursor:
            execute_values(
                cursor,
                """SELECT r.dataset,r.record_key FROM fh_sync.records r
                JOIN (VALUES %s) AS k(dataset,record_key)
                ON (r.dataset,r.record_key)=(k.dataset,k.record_key)""",
                rows,
                page_size=page_size,
            )
            existing = set(cursor.fetchall())
        local.commit()
        for key in rows:
            if key not in existing:
                yield {
                    "dataset": key[0],
                    "record_key": key[1],
                    "reason": "unexpected_target",
                }
        last = rows[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()
    local = connect(os.environ["SYNC_LOCAL_DATABASE_URL"])
    remote = None
    try:
        remote = connect(os.environ["SYNC_NEON_DATABASE_URL"], remote=True)
        # Never emit full database rows or payloads.
        mismatches = 0
        for finding in reconcile(local, remote, args.page_size):
            print(json.dumps(finding))
            mismatches += 1
        print(json.dumps({"mismatches": mismatches}))
        return int(mismatches > 0)
    finally:
        local.close()
        if remote is not None:
            remote.close()


if __name__ == "__main__":
    raise SystemExit(main())
