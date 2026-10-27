"""Restricted PostgreSQL transport using the repository's existing psycopg2."""

import hashlib
import json
from datetime import UTC

import psycopg2
from psycopg2.extensions import parse_dsn


def connect(dsn: str, *, remote: bool = False):
    settings = parse_dsn(dsn)
    if remote:
        # Refuse a cleartext or certificate-unverified production connection.
        if settings.get("sslmode") != "verify-full":
            raise ValueError("Sync destination requires sslmode=verify-full")
        if not settings.get("host") or settings.get("hostaddr"):
            raise ValueError("Sync destination requires a verified hostname")
    return psycopg2.connect(
        dsn,
        connect_timeout=10,
        application_name="footballheritage-sync",
        options="-c timezone=UTC -c statement_timeout=20000 -c lock_timeout=5000",
    )


def fingerprint(event: dict) -> str:
    """Exclude queue timestamps/attempts; include every destination effect."""
    value = {
        key: event[key]
        for key in (
            "stream_id",
            "dataset",
            "record_key",
            "version",
            "payload",
            "deleted",
            "changed_at",
        )
    }
    value["stream_id"] = str(value["stream_id"])
    value["changed_at"] = (
        value["changed_at"].astimezone(UTC).isoformat(timespec="microseconds")
    )
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
