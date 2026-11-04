# Durable gateway and local readiness — 2026-10-27

Implementation and local verification are complete for the remaining gateway
transport, strict Clippy cleanup and local API/query measurements. This is not a
production-readiness or hosted-rollout sign-off.

## Result

Production/staging gateway paths now read approved PostgreSQL response snapshots
or create explicit durable computation requests. Rust no longer contacts the
Windows Python/Node HTTP services or starts a local Python process. Existing
Python functions retain their models, calculations, filters and source IDs.
Default reads are proactively published; filtered or request-specific outputs
are pending until the worker publishes them. Original completed JSON/status
contracts are retained. The frontend polls the explicit pending protocol with
one immutable request body/key, cancellation and bounded waiting.

Native intelligence lists/refresh and the legacy chat contract are migrated too.
Intelligence views preserve filters, ordering, limit clamping, UUIDs, UTC timestamp
format and monetary decimal strings. Successful writes invalidate public views.
Ranking snapshots expire before visible kickoff/quote/prediction age boundaries.
Completed cache hits use one approved-source SELECT instead of a queue transaction.

Private/admin operations use per-user idempotency. The worker has fenced leases,
read recovery, process deadlines and bounded reconnects. An uncertain side effect
is not automatically repeated. The transport never claims exactly-once external
effects across a crash between a local commit and destination acknowledgement.

Strict Clippy's previous 35/36 diagnostics are repaired without suppressions.
Changes are mechanical Rust cleanups, tuple aliases, a grouped transaction balance
argument, an internal JWT variant rename and test-module placement. Kelly handling
explicitly preserves the prior NaN result. Money-path bind order and transaction
boundaries were reviewed with the code-review skill; no betting/wallet behavior
was intentionally changed.

## Files and contracts

- `backend/src/durable_gateway.rs`, `pipeline_gateway.rs`, native intelligence/chat
  handlers, `main.rs`, `config.rs`; the mechanical Clippy fixes across existing
  Rust modules.
- New additive migration `20261027000001_durable_gateway.sql`; `backend/build.rs`
  now tracks added migration files, preventing stale embedded migration binaries.
  Earlier phase migration bytes are unchanged.
- `pipeline/sync/{gateway,gateway_execute,intelligence_views}.py`, generated worker
  and crate-local route manifests, `scripts/generate_gateway_routes.py`.
- `frontend/src/utils/publishedFetch.mjs`, API utility/CORS wiring, Node and
  Chromium protocol tests; Windows launchers now support a separate gateway task.
- Expanded HTTP/permission verification, CI hooks and requirements; contracts and
  rollout instructions in `docs/durable-gateway.md` and `database-ownership.md`.

## Executed checks

| Check | Result |
|---|---|
| Rust formatting, check and strict Clippy | Passed; no lint suppressions |
| `cargo test --locked` | 40 passed, five explicitly ignored external/fixture tests |
| Publication synchronization regressions | 19 passed, disposable local schemas |
| Gateway freshness/wire/packaging tests | Six passed |
| Frontend lint and production build/typecheck | Passed with a fixture HTTPS API URL |
| Node production-policy/polling tests | 11 passed |
| Chromium prediction and gateway tests | 19 passed, two existing opt-in cases skipped |
| Authenticated independent-process HTTP harness | Passed, including migration replay |

The HTTP harness supplied an unreachable Python HTTP URL and invalid legacy RAG
URL. It exercised actual Python interfaces through ASGI and a real isolated
child executor, without a listening Python HTTP server. Checks include response
and validation parity, real EV insertion/replay, native intelligence decimal
serialization, CORS/idempotency, native legacy chat, stale/disabled source states,
read-lease recovery, uncertain-write replay blocking, saved RAG history, Python
ranking parity and durable sessions/revocation/restart/registration rollback.

A restricted NOLOGIN worker with stream RLS published a legitimate result.
PostgreSQL denied six prohibited operations: reading account emails or sessions,
updating wallets or source controls, deleting published records and truncating
the queue. Test roles, databases and processes were removed by the harness.

The two skipped browser cases require explicit `RUN_LEAGUE_LIVE_TESTS=1` or
`RUN_PREDICTION_DB_TESTS=1`. Their separate authenticated live services were not
started. Five ordinary Rust ignored fixtures were not enabled in the unit command;
the HTTP server fixture was exercised separately by the harness. AI provider
generation and live external collection/training commands were not run.

Initial verification exposed stale compile-time migration discovery and JSON-list
query-pair encoding; both were corrected and the complete harness rerun. A new
unit invocation from the repository root lacked the pipeline import path; its
documented `pipeline/` invocation passed. Final lint and formatting pass.

Fallow's final audit returned `warn`, with no new dead-code or clone findings.
The complexity findings include inherited functions and an earlier deployment
artifact, not a new gateway implementation finding. Root dependency discovery is
degraded and architecture boundaries are unconfigured; Fallow is not Rust or
hosted verification. The large pre-existing working tree was preserved.

## Measurements and remaining rollout gates

`durable-gateway-20261027/performance.json` contains 200 successful local API samples,
1,000 captured fixture rows, synthetic quotes, nearest-rank percentiles and the
actual cached-read `EXPLAIN (ANALYZE, BUFFERS)` plan. One process/concurrency one
uses 40 samples; four independent processes/concurrency four use 160. The worker
is stopped during reads. Baseline samples are archived alongside them.

These are debug-build, loopback PostgreSQL measurements with client parsing and
concurrent host activity. Latency varied; no reliable speedup or production
latency/throughput budget is claimed. See `docs/performance-report.md` for values
and limitations. Ingestion, feature/inference/simulation throughput and Vercel
cold-start/Neon latency measurements remain separate workloads, not inferred from
these API tests.

Apply/provision the additive schema, registered stream and reviewed role policies
on the approved hosted target, prewarm outputs, and release the frontend pending
helper before switching the backend contract. Verified remote TLS/login grants,
hosted API/browser acceptance and real Windows sign-in/reboot/task recovery require
that rollout. The new role tests are local, not proof of an unprovisioned Neon
credential. Preserve the ledger and manually review indeterminate actions during
rollback; never restore production-to-Windows HTTP fallback.

Neon remains staging. No deployment, production target selection, credential
change, scheduled-task registration, operational source mutation, model promotion
or cleanup/commit of unrelated work was performed. Production readiness therefore
remains unsigned until the external acceptance gates above are satisfied.
