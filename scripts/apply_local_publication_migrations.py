"""Apply additive publication migrations to loopback PostgreSQL only."""

import argparse
import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from psycopg2.extensions import parse_dsn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from sync.neon_client import connect


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, required=True)
    args = parser.parse_args()
    if not args.env.is_file():
        parser.error("Private sync environment file does not exist")
    load_dotenv(args.env, override=False)
    dsn = os.environ["SYNC_LOCAL_DATABASE_URL"]
    if parse_dsn(dsn).get("host") not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Only an explicit loopback database is allowed")
    connection = connect(dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(71604261028)")
        connection.commit()
        with connection, connection.cursor() as cursor:
            cursor.execute("""CREATE SCHEMA IF NOT EXISTS fh_sync;
                CREATE TABLE IF NOT EXISTS fh_sync.schema_migrations(
                    name text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT NOW())""")
        for name in (
            "002_publication_outbox.sql",
            "003_football_publication_capture.sql",
        ):
            content = (ROOT / "pipeline/migrations" / name).read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            with connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT sha256 FROM fh_sync.schema_migrations WHERE name=%s",
                    (name,),
                )
                existing = cursor.fetchone()
                if existing:
                    if existing[0] != digest:
                        raise SystemExit(f"Applied migration checksum differs: {name}")
                    continue
                cursor.execute(content.decode("utf-8-sig"))
                cursor.execute(
                    "INSERT INTO fh_sync.schema_migrations(name,sha256) VALUES (%s,%s)",
                    (name, digest),
                )
            print(f"Applied {name}")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
