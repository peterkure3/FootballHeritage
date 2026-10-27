"""Local dead-letter inspection and explicit replay without modifying event effects."""

import argparse
import json
import os
import uuid

from psycopg2.extras import RealDictCursor

from .neon_client import connect
from .worker import LOCK_ID


def dead_letters(local, limit: int = 100) -> list[dict]:
    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000")
    with local, local.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """SELECT event_id,dataset,record_key,version,attempts,dead_at,error_code
                FROM fh_sync.outbox WHERE dead_at IS NOT NULL ORDER BY id LIMIT %s""",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def requeue(local, event_id: uuid.UUID) -> bool:
    """Operator-reviewed event only; preserves UUID, version, payload and receipts."""
    with local, local.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        cursor.execute(
            """UPDATE fh_sync.outbox SET dead_at=NULL,attempts=0,
                available_at=NOW(),error_code=NULL WHERE event_id=%s
                AND dead_at IS NOT NULL AND completed_at IS NULL""",
            (str(event_id),),
        )
        return cursor.rowcount == 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--requeue", type=uuid.UUID, help="Replay one reviewed dead-letter event UUID"
    )
    args = parser.parse_args()
    local = connect(os.environ["SYNC_LOCAL_DATABASE_URL"])
    try:
        result = (
            {"requeued": requeue(local, args.requeue)}
            if args.requeue
            else dead_letters(local)
        )
        print(json.dumps(result, default=str))
        return 0
    finally:
        local.close()


if __name__ == "__main__":
    raise SystemExit(main())
