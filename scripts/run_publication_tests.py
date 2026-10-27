"""Run publication tests in disposable schemas on loopback PostgreSQL only."""

import os
import sys
import unittest
from pathlib import Path

from dotenv import dotenv_values
from psycopg2.extensions import parse_dsn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))


def main() -> int:
    dsn = os.getenv("PUBLICATION_TEST_DATABASE_URL")
    if not dsn:
        values = dotenv_values(ROOT / "pipeline/.env")
        dsn = values.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set PUBLICATION_TEST_DATABASE_URL to local PostgreSQL")
    if parse_dsn(dsn).get("host") not in ("localhost", "127.0.0.1", "::1"):
        raise SystemExit("Refusing non-loopback integration database")
    os.environ["PUBLICATION_TEST_DATABASE_URL"] = dsn
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "pipeline/tests"), pattern="test_publication_sync.py"
    )
    return int(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())


if __name__ == "__main__":
    raise SystemExit(main())
