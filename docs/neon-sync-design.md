# Durable publication design

Status: first implementation with local integration tests and destination DDL
validated on an isolated Neon development branch. End-to-end Python transport
against Neon with restricted TLS credentials remains unverified.

## Contracts

`pipeline/migrations/002_publication_outbox.sql` installs local stream identity,
publication records, outbox and status. `003_football_publication_capture.sql`
adds a durable dirty-fixture queue and triggers on existing matches, predictions
and odds. The backend's new `20261026000001_published_data.sql` creates an isolated
destination schema, source registry, versioned records and commit receipts.
Existing applied migrations are untouched.

Every local source mutation enqueues its affected fixture inside the producer's
transaction. The projector claims a bounded dirty batch, reads existing outputs,
validates probabilities, writes complete bundles and clears claimed dirty rows
in one transaction. Publication triggers allocate per-key versions and capture
the full effect in the outbox. A producer rollback also rolls back capture.
Unchanged publications generate no new event. Global sequences are queue IDs,
never high-watermark checkpoints: sequence allocation does not imply commit order.

`sync.publisher.publish(cursor, ...)` can also join any existing producer's
transaction for approved model/simulation bundles. It never commits the caller's
transaction. No arbitrary SQL/table replication or model inference occurs here.

## Delivery and recovery

1. Acquire a PostgreSQL **session** advisory lock on the local connection. It
   spans destination commit and source acknowledgment and is released on death.
2. Claim at most 1,000 eligible outbox rows and 16 MiB of payload, ordered by queue
   ID. Each payload is limited to 1 MiB by both schemas. The session lock
   prevents another worker from publishing this database concurrently.
3. Lock the registered destination stream transactionally; reject disabled or
   unregistered streams. Compare existing receipts by event UUID and content hash.
4. Coalesce multiple versions of the same record within the batch, then bulk
   UPSERT only a greater version. A same-version/different-content or reused-event
   conflict is quarantined. Whole fixture aggregates preserve parent/child order.
5. Insert receipts and update destination success time in the same transaction.
   Complete the Neon commit before attempting any local acknowledgment.
6. Acknowledge exact outbox IDs locally and update local success time. If this
   commit fails, replay checks the existing destination receipt and produces no
   duplicate effects. No external financial actions are attached to this writer.

Receipts are retained; tombstones retain version floors. No automatic retention,
source rewinds, checkpoint reset or receipt deletion is implemented. Restoring an
old local backup requires reconciliation and a new stream identity or a reviewed
version restoration; never reuse old versions with different content.

## Failures and deletion

Transient attempts persist a bounded exponential full-jitter next-attempt time.
After 12 failed attempts the record is parked in the dead-letter queue for review;
that is retry exhaustion, not proof of invalid data. Conflicting identities are
quarantined explicitly. Errors/logs contain classes or SQLSTATE codes, not database
messages, payloads or DSNs. A denied/unregistered source is a configuration fault,
not permission to register a source automatically. Status distinguishes queued
and dead-letter rows. Queue state, not an in-memory cursor, is authoritative.

Physical deletion of local publication records is forbidden. Use the explicit
`tombstone()` API only after intentional-deletion review. Source-table cleanup
does not imply production deletion: missing source fixtures are counted and
removed from the dirty queue while previous published records remain intact.
Record/receipt cleanup and automatic repairs are deliberately absent.

Invalid stored predictions remain blocked dirty rows with an explicit error code.
They do not block unrelated fixtures. A source correction atomically clears the
block through the source trigger, allowing projection to resume.
An unavailable prediction remains null; no fallback model or fabricated output
is introduced. The first adapter projects football only; other sports and
file-backed trial/intelligence outputs remain to be integrated explicitly.

The football projector checks `matches.sport_type` before assigning a sport.
Non-football/soccer rows remain blocked with `UNSUPPORTED_SPORT`; correcting the
source unblocks them through the existing capture trigger. A nonempty valid batch
atomically queues the explicit operator-selected `football:active-model` metadata
before its fixture bundles. Unchanged metadata is a no-op. Model switches can
temporarily leave no eligible fixtures until the new-model bundles arrive; the API
returns empty picks rather than borrowing another model's results. A model switch
requires explicitly re-enqueuing/backfilling existing fixtures, not just changing
the worker argument. The worker does not train or select a model automatically.

## Connections, inspection and reconciliation

The proven psycopg2 client already used by the repository is retained. Remote
connections require `sslmode=verify-full` and a hostname, with finite connect,
statement and lock timeouts. Supply the trusted CA through libpq configuration.
Runtime API pooling and direct migration credentials remain separate.

`py -3 -m sync.worker --status` reports queue size, dead letters, oldest pending
timestamp, last attempt and last acknowledged success. It needs only local access.
It also reports the source UUID and blocked projection count when football capture
is installed. `sync.outbox` lists dead letters without payloads; `--requeue <uuid>`
retries one reviewed event without changing its identity/version/effect/receipts.
`py -3 -m sync.reconciliation` uses bounded keyset pages, comparing versions,
canonical effect hashes and missing/unexpected keys for the registered stream.
It makes no repairs and does not read user data. Reconcile after quiescing source
writes/draining queues for a cutover decision; concurrent changes can produce
temporary differences. Full reconciliation is deliberate maintenance, not every
poll cycle. Large-payload and outage-throughput benchmarks remain pending.

Neon supports verified TLS connections; certificate/hostname verification matters
in addition to encryption. See [Neon connection security](https://neon.com/docs/connect/connect-securely).
