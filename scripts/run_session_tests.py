"""Execute Rust durable-session tests against disposable loopback schemas."""

import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from psycopg2.extensions import parse_dsn

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    dsn = os.getenv("SESSION_TEST_DATABASE_URL") or dotenv_values(
        ROOT / "pipeline/.env"
    ).get("DATABASE_URL")
    if not dsn or parse_dsn(dsn).get("host") not in ("localhost", "127.0.0.1", "::1"):
        raise SystemExit("Set SESSION_TEST_DATABASE_URL to loopback PostgreSQL")
    environment = {**os.environ, "SESSION_TEST_DATABASE_URL": dsn}
    return subprocess.run(
        [
            "cargo",
            "test",
            "--locked",
            "--bin",
            "football-heritage-backend",
            "durable_sessions_survive_independent_instances_and_revocation",
            "--",
            "--ignored",
            "--nocapture",
        ],
        cwd=ROOT / "backend",
        env=environment,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
