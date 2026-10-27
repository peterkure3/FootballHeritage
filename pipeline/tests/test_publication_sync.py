"""Commit/recovery tests in disposable PostgreSQL schemas, never user tables."""

import json
import os
import subprocess
import sys
import unittest
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg2
from psycopg2.extensions import parse_dsn
from psycopg2.extras import RealDictCursor
from sync.football import project
from sync.neon_client import connect, fingerprint
from sync.outbox import dead_letters, requeue
from sync.publisher import publish, tombstone, validate_record
from sync.reconciliation import reconcile
from sync.worker import LOCK_ID, deliver, retry_delay, run_batch, status

ROOT = Path(__file__).resolve().parents[2]


class ContractTests(unittest.TestCase):
    def test_ownership_allowlist(self):
        for dataset in ("users", "wallets", "bets", "sessions", "events"):
            with self.assertRaises(ValueError):
                validate_record(dataset, "one", {})
        for key in ("", "x" * 513):
            with self.assertRaises(ValueError):
                validate_record("fixture_bundle", key, {})

    def test_bounded_retry(self):
        self.assertEqual(retry_delay(1, 1), 2)
        self.assertEqual(retry_delay(1000, 1), 300)
        self.assertEqual(retry_delay(10, 0), 0)

    def test_requires_verified_tls_before_connecting(self):
        with patch("sync.neon_client.psycopg2.connect") as connector:
            with self.assertRaises(ValueError):
                connect(
                    "postgresql://example.invalid/test?sslmode=require", remote=True
                )
            connector.assert_not_called()

    def test_fingerprint_stable_and_sensitive_to_effect(self):
        event = {
            "stream_id": str(uuid.uuid4()),
            "dataset": "fixture_bundle",
            "record_key": "football:provider:1",
            "version": 1,
            "payload": {"b": 2, "a": 1},
            "deleted": False,
            "changed_at": datetime.now(UTC),
        }
        self.assertEqual(
            fingerprint(event),
            fingerprint({**event, "payload": {"a": 1, "b": 2}, "attempts": 4}),
        )
        self.assertNotEqual(fingerprint(event), fingerprint({**event, "deleted": True}))
        self.assertEqual(
            fingerprint(event),
            fingerprint(
                {
                    **event,
                    "changed_at": event["changed_at"].astimezone(
                        timezone(timedelta(hours=3))
                    ),
                }
            ),
        )


class CursorProxy:
    def __init__(self, cursor, names):
        self.cursor = cursor
        self.names = names

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    def __enter__(self):
        self.cursor.__enter__()
        return self

    def __exit__(self, *args):
        return self.cursor.__exit__(*args)

    def execute(self, statement, params=None):
        binary = isinstance(statement, bytes)
        if binary:
            statement = statement.decode("utf-8")
        for original, replacement in self.names.items():
            statement = statement.replace(original, replacement)
        return self.cursor.execute(
            statement.encode("utf-8") if binary else statement, params
        )


class ConnectionProxy:
    def __init__(self, connection, names):
        self.connection = connection
        self.names = names

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def cursor(self, *args, **kwargs):
        return CursorProxy(self.connection.cursor(*args, **kwargs), self.names)


@unittest.skipUnless(
    os.getenv("PUBLICATION_TEST_DATABASE_URL"),
    "Set PUBLICATION_TEST_DATABASE_URL to a local test database",
)
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        dsn = os.environ["PUBLICATION_TEST_DATABASE_URL"]
        settings = parse_dsn(dsn)
        if settings.get("host", "") not in ("127.0.0.1", "localhost", "::1"):
            self.fail("Publication integration tests require loopback PostgreSQL")
        stamp = uuid.uuid4().hex
        self.source = f"test_source_{stamp}"
        self.names = {
            "fh_sync": f"test_sync_{stamp}",
            "published": f"test_pub_{stamp}",
            "public.": f"{self.source}.",
        }
        self.local = ConnectionProxy(psycopg2.connect(dsn), self.names)
        self.remote = ConnectionProxy(psycopg2.connect(dsn), self.names)
        self.addCleanup(self.cleanup)
        with self.local, self.local.cursor() as cursor:
            cursor.execute(
                (ROOT / "pipeline/migrations/002_publication_outbox.sql").read_text()
            )
            cursor.execute(
                (
                    ROOT / "backend/migrations/20261026000001_published_data.sql"
                ).read_text()
            )
            cursor.execute(f"CREATE SCHEMA {self.source}")
            cursor.execute("""CREATE TABLE public.matches(match_id integer PRIMARY KEY,
                competition text,date timestamp,home_team text,away_team text,
                home_score integer,away_score integer,status text,result text,
                sport_type text DEFAULT 'football');
                CREATE TABLE public.predictions(id serial PRIMARY KEY,
                match_id integer REFERENCES public.matches(match_id) ON DELETE CASCADE,
                model_version text,winner text,home_prob float,draw_prob float,away_prob float,created_at timestamp);
                CREATE TABLE public.odds(id serial PRIMARY KEY,
                match_id integer REFERENCES public.matches(match_id) ON DELETE CASCADE,
                bookmaker text,home_win float,draw float,away_win float,updated_at timestamp)""")
            cursor.execute(
                (
                    ROOT / "pipeline/migrations/003_football_publication_capture.sql"
                ).read_text()
            )
            cursor.execute("SELECT stream_id::text FROM fh_sync.identity")
            self.stream = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO published.sources(stream_id,description) VALUES (%s,%s)",
                (self.stream, "disposable integration test"),
            )

    def cleanup(self):
        self.remote.close()
        self.local.rollback()
        with self.local, self.local.cursor() as cursor:
            for schema in (self.names["fh_sync"], self.names["published"], self.source):
                # Only exact UUID schemas created by this test, never app schemas.
                cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        self.local.close()

    def publish(self, value=1, key="football:provider:1"):
        with self.local, self.local.cursor() as cursor:
            publish(cursor, "fixture_bundle", key, {"value": value})

    def scalar(self, connection, query):
        with connection, connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]

    def test_atomic_capture_noop_and_producer_rollback(self):
        self.publish()
        self.publish()
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.outbox"), 1
        )
        with self.local.cursor() as cursor:
            publish(cursor, "fixture_bundle", "rolled-back", {})
        self.local.rollback()
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.outbox"), 1
        )

    def test_commit_ack_loss_replay_and_reconciliation(self):
        self.publish()
        with (
            patch(
                "sync.worker.acknowledge",
                side_effect=psycopg2.OperationalError(
                    "simulated crash after remote commit"
                ),
            ),
            self.assertRaises(psycopg2.OperationalError),
        ):
            run_batch(self.local, self.remote)
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.receipts"), 1
        )
        self.assertEqual(status(self.local)["outstanding"], 1)
        self.assertEqual(run_batch(self.local, self.remote)["outcome"], "published")
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.receipts"), 1
        )
        self.assertEqual(list(reconcile(self.local, self.remote, 1)), [])

    def test_monotonic_versions_and_tombstones(self):
        self.publish(1)
        self.publish(2)
        self.assertEqual(run_batch(self.local, self.remote)["count"], 2)
        self.assertEqual(
            self.scalar(self.remote, "SELECT version FROM published.records"), 2
        )
        with self.local, self.local.cursor() as cursor:
            tombstone(cursor, "fixture_bundle", "football:provider:1")
        run_batch(self.local, self.remote)
        self.assertTrue(
            self.scalar(self.remote, "SELECT deleted FROM published.records")
        )
        self.assertEqual(
            self.scalar(self.remote, "SELECT version FROM published.records"), 3
        )
        with (
            self.assertRaises(psycopg2.Error),
            self.local,
            self.local.cursor() as cursor,
        ):
            cursor.execute("DELETE FROM fh_sync.records")

    def test_network_failure_does_not_acknowledge(self):
        self.publish()
        with patch(
            "sync.worker.deliver",
            side_effect=psycopg2.OperationalError("simulated outage"),
        ):
            self.assertEqual(
                run_batch(self.local, self.remote)["outcome"], "retry_or_dead_letter"
            )
        self.assertEqual(status(self.local)["outstanding"], 1)
        self.assertEqual(
            self.scalar(self.local, "SELECT attempts FROM fh_sync.outbox"), 1
        )
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.receipts"), 0
        )

    def test_concurrent_worker_is_excluded(self):
        self.publish()
        with self.remote.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        self.remote.commit()
        self.assertEqual(run_batch(self.local, self.remote)["outcome"], "busy")
        with self.remote.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
        self.remote.commit()

    def test_missing_and_unexpected_records_reported(self):
        self.publish(key="one")
        self.publish(key="two")
        self.assertEqual(len(list(reconcile(self.local, self.remote, 1))), 2)
        run_batch(self.local, self.remote)
        self.assertEqual(list(reconcile(self.local, self.remote, 1)), [])
        with self.remote, self.remote.cursor() as cursor:
            cursor.execute(
                "UPDATE published.records SET record_key='unexpected' WHERE record_key='two'"
            )
        reasons = {row["reason"] for row in reconcile(self.local, self.remote, 1)}
        self.assertEqual(reasons, {"missing", "unexpected_target"})

    def source_fixture(self):
        with self.local, self.local.cursor() as cursor:
            cursor.execute("""INSERT INTO public.matches VALUES (1,'Test league',
                '2026-12-01 12:00:00','Home','Away',NULL,NULL,'SCHEDULED',NULL,'football');
                INSERT INTO public.predictions(match_id,model_version,winner,home_prob,draw_prob,away_prob,created_at)
                VALUES (1,'test-active','home_win',0.5,0.3,0.2,'2026-10-26 12:00:00');
                INSERT INTO public.odds(match_id,bookmaker,home_win,draw,away_win,updated_at)
                VALUES (1,'test-book',2.2,3.5,4.0,(NOW() AT TIME ZONE 'UTC')-INTERVAL '1 minute')""")

    def test_source_capture_projection_atomic_bundle_and_numerical_parity(self):
        self.source_fixture()
        # A future-dated correction must not hide the last observed valid quote.
        with self.local, self.local.cursor() as cursor:
            cursor.execute("""INSERT INTO public.odds(match_id,bookmaker,home_win,draw,away_win,updated_at)
                VALUES (1,'test-book',99,99,99,(NOW() AT TIME ZONE 'UTC')+INTERVAL '1 hour')""")
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.dirty_fixtures"), 1
        )
        self.assertEqual(project(self.local, "test-active")["published"], 1)
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.dirty_fixtures"), 0
        )

        run_batch(self.local, self.remote)
        with self.remote, self.remote.cursor() as cursor:
            cursor.execute(
                "SELECT payload FROM published.records WHERE dataset='fixture_bundle'"
            )
            payload = cursor.fetchone()[0]
        self.assertEqual(payload["prediction"]["home_prob"], 0.5)
        self.assertEqual(payload["prediction"]["draw_prob"], 0.3)
        self.assertEqual(payload["prediction"]["away_prob"], 0.2)
        self.assertEqual(payload["quotes"][0]["home_win"], 2.2)
        self.assertEqual(payload["local_match_id"], payload["fixture"]["match_id"])
        self.assertEqual(
            payload["prediction"]["created_at"], "2026-10-26T12:00:00+00:00"
        )
        with self.local.cursor() as cursor:
            cursor.execute("UPDATE public.predictions SET home_prob=0.4,draw_prob=0.4")
        self.local.rollback()
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.dirty_fixtures"), 0
        )

    def test_process_termination_after_remote_commit_recovers(self):
        self.publish()
        environment = {**os.environ, "PUBLICATION_TEST_NAMES": json.dumps(self.names)}
        program = """
import json, os, sys
from pathlib import Path
from unittest.mock import patch
import psycopg2
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_publication_sync import ConnectionProxy
from sync.worker import run_batch
names = json.loads(os.environ["PUBLICATION_TEST_NAMES"])
local = ConnectionProxy(psycopg2.connect(os.environ["PUBLICATION_TEST_DATABASE_URL"]), names)
remote = ConnectionProxy(psycopg2.connect(os.environ["PUBLICATION_TEST_DATABASE_URL"]), names)
with patch("sync.worker.acknowledge", side_effect=lambda *_: os._exit(73)):
    run_batch(local, remote)
"""
        result = subprocess.run(
            [sys.executable, "-c", program],
            cwd=ROOT / "pipeline",
            env=environment,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 73)
        self.assertEqual(status(self.local)["outstanding"], 1)
        self.assertEqual(run_batch(self.local, self.remote)["outcome"], "published")
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.receipts"), 1
        )

    def test_retry_exhaustion_is_parked_and_explicit_requeue_preserves_identity(self):
        self.publish()
        for _ in range(12):
            with patch(
                "sync.worker.deliver",
                side_effect=psycopg2.OperationalError("test-only outage"),
            ):
                run_batch(self.local, self.remote)
            with self.local, self.local.cursor() as cursor:
                cursor.execute("UPDATE fh_sync.outbox SET available_at=NOW()")
        letters = dead_letters(self.local)
        self.assertEqual(len(letters), 1)
        self.assertEqual(status(self.local)["dead_letters"], 1)
        self.assertTrue(requeue(self.local, uuid.UUID(str(letters[0]["event_id"]))))
        self.assertEqual(run_batch(self.local, self.remote)["outcome"], "published")
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.receipts"), 1
        )

    def test_raw_deletion_is_not_implicit_production_deletion(self):
        self.source_fixture()
        project(self.local, "test-active")
        run_batch(self.local, self.remote)
        with self.local, self.local.cursor() as cursor:
            cursor.execute("DELETE FROM public.matches")
        self.assertEqual(project(self.local, "test-active")["missing_source"], 1)
        self.assertFalse(
            self.scalar(
                self.remote,
                "SELECT deleted FROM published.records WHERE dataset='fixture_bundle'",
            )
        )

    def test_other_sports_are_quarantined_and_corrections_resume(self):
        self.source_fixture()
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE public.matches SET sport_type='basketball'")
        self.assertEqual(project(self.local, "test-active")["invalid"], 1)
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.outbox"), 0
        )
        self.assertEqual(
            self.scalar(self.local, "SELECT error_code FROM fh_sync.dirty_fixtures"),
            "UNSUPPORTED_SPORT",
        )
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE public.matches SET sport_type='football'")
        self.assertEqual(project(self.local, "test-active")["published"], 1)
        with self.local, self.local.cursor() as cursor:
            cursor.execute("SELECT dataset,payload FROM fh_sync.outbox ORDER BY id")
            events = cursor.fetchall()
        self.assertEqual(
            [event[0] for event in events], ["model_metadata", "fixture_bundle"]
        )
        self.assertEqual(events[0][1]["model_version"], "test-active")
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE public.matches SET status=status")
        project(self.local, "test-active")
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.outbox"), 2
        )

    def test_invalid_stored_probabilities_retain_dirty_queue(self):
        self.source_fixture()
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE public.predictions SET home_prob=0.99")
        self.assertEqual(project(self.local, "test-active")["invalid"], 1)
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.outbox"), 0
        )
        self.assertEqual(
            self.scalar(self.local, "SELECT count(*) FROM fh_sync.dirty_fixtures"), 1
        )
        self.assertEqual(project(self.local, "test-active")["processed"], 0)
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE public.predictions SET home_prob=0.5")
        self.assertEqual(project(self.local, "test-active")["published"], 1)

    def test_stale_delivery_cannot_resurrect_a_tombstone(self):
        self.publish(1)
        with self.local, self.local.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM fh_sync.outbox ORDER BY id LIMIT 1")
            previous = dict(cursor.fetchone())
        run_batch(self.local, self.remote)
        with self.local, self.local.cursor() as cursor:
            tombstone(cursor, "fixture_bundle", "football:provider:1")
        run_batch(self.local, self.remote)
        previous["event_id"] = str(uuid.uuid4())
        deliver(self.remote, [previous])
        self.assertTrue(
            self.scalar(self.remote, "SELECT deleted FROM published.records")
        )
        self.assertEqual(
            self.scalar(self.remote, "SELECT version FROM published.records"), 2
        )

    def test_disabled_source_never_publishes_or_acknowledges(self):
        self.publish()
        with self.remote, self.remote.cursor() as cursor:
            cursor.execute("UPDATE published.sources SET enabled=FALSE")
        result = run_batch(self.local, self.remote)
        self.assertEqual(result["error_code"], "PermissionError")
        self.assertEqual(status(self.local)["outstanding"], 1)
        self.assertEqual(
            self.scalar(self.remote, "SELECT count(*) FROM published.records"), 0
        )

    def test_identity_conflict_does_not_dead_letter_unrelated_events(self):
        self.publish(key="conflicting")
        self.publish(key="valid")
        with self.local, self.local.cursor() as cursor:
            cursor.execute(
                "SELECT event_id::text FROM fh_sync.outbox ORDER BY id LIMIT 1"
            )
            conflicting = cursor.fetchone()[0]
        with self.remote, self.remote.cursor() as cursor:
            cursor.execute(
                "INSERT INTO published.receipts(event_id,stream_id,content_hash) VALUES (%s,%s,%s)",
                (conflicting, self.stream, "0" * 64),
            )
        self.assertEqual(
            run_batch(self.local, self.remote)["error_code"], "ConflictError"
        )
        self.assertEqual(status(self.local)["dead_letters"], 1)
        self.assertEqual(status(self.local)["outstanding"], 1)
        with self.local, self.local.cursor() as cursor:
            cursor.execute("UPDATE fh_sync.outbox SET available_at=NOW()")
        self.assertEqual(run_batch(self.local, self.remote)["outcome"], "published")
        self.assertEqual(
            self.scalar(self.remote, "SELECT record_key FROM published.records"),
            "valid",
        )
