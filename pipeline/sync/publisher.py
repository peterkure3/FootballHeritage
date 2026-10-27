"""Publish bundles using the caller's local transaction; never commits it."""

import json

from psycopg2.extras import Json

DATASETS = frozenset({"fixture_bundle", "model_metadata", "simulation_bundle"})


def validate_record(dataset: str, record_key: str, payload: dict) -> None:
    if dataset not in DATASETS:
        raise ValueError("Dataset is not approved for publication")
    if not isinstance(record_key, str) or not 1 <= len(record_key) <= 512:
        raise ValueError("Invalid canonical record key")
    if not isinstance(payload, dict):
        raise TypeError("Publication payload must be an object")
    if len(json.dumps(payload, allow_nan=False).encode("utf-8")) > 1024 * 1024:
        raise ValueError("Publication payload exceeds the one MiB limit")


def publish(
    cursor, dataset: str, record_key: str, payload: dict, *, deleted: bool = False
) -> None:
    """Call inside the same transaction that persists the producer's output.

    Bundle builders must supply canonical provider/sport IDs, model identity,
    generation time and explicit evidence freshness. This transport never infers
    probabilities, promotes a model, or copies arbitrary tables.
    """
    validate_record(dataset, record_key, payload)
    cursor.execute(
        """
        INSERT INTO fh_sync.records(dataset,record_key,payload,deleted)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT(dataset,record_key) DO UPDATE
        SET payload=EXCLUDED.payload, deleted=EXCLUDED.deleted
        WHERE (fh_sync.records.payload,fh_sync.records.deleted)
            IS DISTINCT FROM (EXCLUDED.payload,EXCLUDED.deleted)
    """,
        (dataset, record_key, Json(payload), deleted),
    )


def tombstone(cursor, dataset: str, record_key: str) -> None:
    """Intentional deletion; retain the version floor on both databases forever."""
    publish(cursor, dataset, record_key, {}, deleted=True)
