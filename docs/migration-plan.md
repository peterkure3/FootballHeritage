# Migration plan and gates

This plan preserves existing functionality and applied migration bytes. No cloud
production migration or deployment has been executed by this work. Additive
publication/session DDL has been tested on an isolated child of the staging
branch; the staging parent is unchanged. The existing Neon project remains
staging by user decision; the production target will be specified later.

| Step | Exact affected files | Gate / rollback |
|---|---|---|
| 1. Audit | `docs/architecture-audit.md`, `api-inventory.md`, `schema-inventory.md`, `scripts/architecture_inventory.py` | Static source inventory; live schema/settings still to verify |
| 2. Publication foundation | `pipeline/sync/{publisher,neon_client,worker,reconciliation,football}.py`, local migrations 002/003, backend migration `20261026000001_published_data.sql`, `pipeline/tests/test_publication_sync.py`, `scripts/run_publication_tests.py` | Disposable PostgreSQL capture/replay/retry/version/delete/concurrency/parity tests; leave new tables in place on code rollback |
| 3. Database branch validation | New migration + restricted role grants in `database-ownership.md` | Confirm Neon development project/branch, test fresh/existing schema, role denials and TLS; no destructive changes |
| 4. Rust read contracts | Add `backend/src/published.rs`; update `pipeline_gateway.rs`, `handlers/ai_picks.rs`, `rag.rs`, `handlers/intelligence.rs`, `config.rs`, `main.rs` | Endpoint-by-endpoint contract and auth parity; production cannot use a local HTTP fallback |
| 5. Complete producer adapters | Existing league/sport forecasts, trial/intelligence snapshots and model metadata; preserve current generators | Active/candidate parity, source ownership, canonical provider-ID mapping, multi-sport fixtures; no model promotion |
| 6. Measured Python optimization | `etl/load_to_db.py`, `etl/utils.py`, measured collector hotspots | Baseline/after numeric parity, load throughput and provider-rate evidence |
| 7. Frontend | `src/App.jsx`, `utils/api.js`, typed domain contracts and affected pages | TypeScript 7 build, empty/stale/offline/loading/error UI, login/logout/reload and mobile/keyboard E2E |
| 8. Vercel preview | Existing service/project configuration and deployment docs | Verify actual adapter/settings; cold/warm DB/API/CORS/SPA requests; local Python offline |
| 9. Windows operations | `scripts/setup_pipeline_sync.ps1`, `start_pipeline_sync.ps1`, `install_pipeline_sync_task.ps1` | Non-overlap, restart/reboot recovery, stop behavior and task-launched smoke |
| 10. Production cutover | Approved release checkout, docs/checklists/evidence | Explicit production deployment/credential approval, drained queues, reconciliation, rollback artifact |

Do not point a partially migrated production API at the new store. Feature
coverage and response parity must be complete before switching. Preserve the
legacy code locally while migrating, but never restore production-to-Windows
HTTP calls as a rollback shortcut. Historical data and immutable trials must
remain intact, including user changes currently outside Git commits.

Open dependencies: confirmed cloud project/branch mapping and existing schema,
restricted credentials, release checkout including current uncommitted work,
runtime compatibility, provider budgets and realistic benchmark workloads.
Production changes, credential changes and destructive operations require approval.

The instance-local session blocker is now fixed in source using additive migration
`20261026000002_persistent_auth_sessions.sql`, `sessions.rs`, `auth.rs`, both auth
middlewares, auth handlers and feature identity consumers. Independent Rust
processes accept the same session after restart and enforce exact-session logout;
registration rollback and concurrent failed-login locking also passed actual
HTTP checks. See `auth-session-design.md`. Operational rollout remains pending.

Native published AI Picks generation is also implemented and tested through the
authenticated HTTP route with Python offline. See `published-ai-picks.md` for
contract, source files, parity evidence and limits. Python training/inference,
existing saved runs and development-only Python integration are preserved.
RAG now shares the approved publication reader and application pool, with no
legacy database fallback in published mode. See `published-rag.md` for the
contract and its original remaining gateway inventory. Those gateway routes now
use durable computation and published response snapshots; native intelligence
lists/refresh and legacy chat are also migrated in source. See
`durable-gateway.md`. Strict Clippy is repaired; the expanded HTTP harness covers
response parity, restricted-role denials, leases, idempotency and local API/query
measurements. Hosted role/TLS, preview, operational-task and cutover gates remain.
