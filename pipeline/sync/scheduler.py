"""Windows/local supervisor: projection, publishing, bounded restart and shutdown."""

import argparse
import json
import os
import signal
import threading
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from .football import project
from .neon_client import connect
from .worker import retry_delay, run_batch

SCHEDULER_LOCK = 71604261027


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not args.env.is_file():
        parser.error("The private sync environment file does not exist")
    load_dotenv(args.env, override=False)
    required = (
        "SYNC_LOCAL_DATABASE_URL",
        "SYNC_NEON_DATABASE_URL",
        "SYNC_MODEL_VERSION",
    )
    if any(not os.getenv(key) for key in required):
        parser.error("Configure both sync database URLs and SYNC_MODEL_VERSION")
    stop = threading.Event()
    for name in ("SIGINT", "SIGTERM"):
        signal.signal(getattr(signal, name), lambda *_: stop.set())
    local = remote = None
    attempts = 0
    try:
        while not stop.is_set():
            try:
                if local is None or local.closed:
                    local = connect(os.environ["SYNC_LOCAL_DATABASE_URL"])
                    with local.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_try_advisory_lock(%s)", (SCHEDULER_LOCK,)
                        )
                        acquired = cursor.fetchone()[0]
                    local.commit()
                    if not acquired:
                        print(json.dumps({"outcome": "already_running"}), flush=True)
                        return 0
                projected = project(local, os.environ["SYNC_MODEL_VERSION"])
                if remote is None or remote.closed:
                    remote = connect(os.environ["SYNC_NEON_DATABASE_URL"], remote=True)
                result = run_batch(local, remote)
                print(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "projection": projected,
                            **result,
                        }
                    ),
                    flush=True,
                )
                attempts = 0
                if args.once:
                    return int(result["outcome"] == "retry_or_dead_letter")
                if result["outcome"] != "published" and not projected["processed"]:
                    stop.wait(5)
            except (psycopg2.Error, OSError, ValueError) as exc:
                attempts += 1
                print(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "outcome": "failed",
                            "error_code": type(exc).__name__,
                        }
                    ),
                    flush=True,
                )
                for connection in (remote, local):
                    if connection is not None:
                        connection.close()
                remote = local = None
                if args.once:
                    return 1
                stop.wait(max(1, retry_delay(attempts)))
    finally:
        for connection in (remote, local):
            if connection is not None:
                connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
