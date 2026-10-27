"""Run/replay SQLx migrations in a newly created disposable loopback database."""

import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from dotenv import dotenv_values
from psycopg2 import sql
from psycopg2.extensions import parse_dsn

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    source = os.getenv("SESSION_TEST_DATABASE_URL") or dotenv_values(
        ROOT / "pipeline/.env"
    ).get("DATABASE_URL")
    if not source or parse_dsn(source).get("host") not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise SystemExit("A loopback PostgreSQL URL is required")
    parsed = urlsplit(source)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise SystemExit("Use PostgreSQL URL syntax for SQLx testing")
    name = "fh_migration_test_" + uuid.uuid4().hex
    destination = urlunsplit(parsed._replace(path="/" + name))
    admin = psycopg2.connect(source)
    admin.autocommit = True
    created = False
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        created = True
        environment = {**os.environ, "MIGRATION_DATABASE_URL": destination}
        for _ in range(2):
            result = subprocess.run(
                ["cargo", "run", "--locked", "--bin", "migrate"],
                cwd=ROOT / "backend",
                env=environment,
                check=False,
            )
            if result.returncode:
                return result.returncode
        connection = psycopg2.connect(destination)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM _sqlx_migrations WHERE success")
                count = cursor.fetchone()[0]
                expected = len(list((ROOT / "backend/migrations").glob("*.sql")))
                if count != expected:
                    raise RuntimeError("Migration count mismatch")
                print(f"Fresh migration chain and replay passed: {count} migrations")
        finally:
            connection.close()
        return 0
    finally:
        if created:
            # This exact name is generated above; never target an operator DB.
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(name)
                    )
                )
        admin.close()


if __name__ == "__main__":
    raise SystemExit(main())
