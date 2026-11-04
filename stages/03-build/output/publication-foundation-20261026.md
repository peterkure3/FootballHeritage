# Publication foundation — phase report

Status: audited, incremental foundation delivered; **not production-ready**.
No application deployment, production credential change, operational local
migration, source-model promotion, training rewrite or production data cutover.
The pre-existing working-tree changes were preserved; no commit was made.

## Files changed

| Group | Files |
|---|---|
| Audit/contracts | `docs/architecture-audit.md`, `target-architecture.md`, `database-ownership.md`, `neon-sync-design.md`, `api-inventory.md`, `schema-inventory.md`, `migration-plan.md`, `performance-report.md`, `deployment-guide.md`, `windows-pipeline-setup.md`, `rollback-plan.md` |
| Live schema evidence | `docs/footballheritage_app_staging-schema.json`, `docs/footballheritage_predictions_staging-schema.json` |
| Local capture | `pipeline/migrations/002_publication_outbox.sql`, `003_football_publication_capture.sql` |
| Destination schema | `backend/migrations/20261026000001_published_data.sql` |
| Transport/projection | `pipeline/sync/__init__.py`, `publisher.py`, `neon_client.py`, `worker.py`, `outbox.py`, `reconciliation.py`, `football.py`, `scheduler.py` |
| Sync verification | `pipeline/tests/test_publication_sync.py`, `scripts/run_publication_tests.py`, `.github/workflows/publication-sync.yml` |
| Windows/setup | `pipeline/requirements-sync.txt`, `scripts/apply_local_publication_migrations.py`, `setup_pipeline_sync.ps1`, `start_pipeline_sync.ps1`, `install_pipeline_sync_task.ps1` |
| Rust | `backend/src/published.rs`, route registration in `main.rs`, prompt logging fix in `handlers/chat.rs` |
| Frontend | `frontend/src/App.jsx`, `frontend/package.json`, `frontend/package-lock.json` |
| Configuration/record | `.env.example`, `.gitignore`, `scripts/architecture_inventory.py`, `shared/CODEBASE_INDEX.md`, architecture stage output |

## Implemented and preserved

Transactional source capture, durable dirty/outbox queues, allowlisted self-contained
bundles, per-record versions, byte/row-bounded delivery, destination commit receipts,
commit-before-acknowledge ordering, local/destination concurrency locks, jittered
retries, blocked invalid projections, dead-letter recovery, tombstones, durable
status and read-only reconciliation. Source corrections unblock invalid projections;
raw cleanup never implicitly deletes production records. Transport SQL cannot
write application/user/financial tables.

The initial adapter copies existing stored football outputs without inference.
Native Rust `GET /api/v1/predictions/{match_id}` uses the application pool and a
configured source UUID, returning pending/unavailable/withdrawn states without
fabricated probabilities, and additive freshness metadata on available predictions.
Legacy gateway URLs and existing features are unchanged. React route splitting
retains routing/auth/design; the legacy chat UTF-8 slicing/logging bug is removed.
Zod alone was updated from 4.1.12 to 4.6.7 after a high-severity advisory.

## Executed verification

| Check | Actual result |
|---|---|
| Rust `cargo fmt --check` | Passed after formatting the new module/registration |
| Rust `cargo test --locked --bin football-heritage-backend` | 36 passed, 3 ignored; includes three publication response tests |
| Strict `cargo clippy --locked --bin football-heritage-backend -- -D warnings` baseline | Failed on 36 existing lint errors; release gate remains open |
| Full Python `pytest tests -q` | 286 passed, 30 skipped, 63 subtests passed; 48 existing utcnow deprecation warnings |
| Publication PostgreSQL suite | 18 passed against disposable UUID schemas on loopback PostgreSQL; no operational source tables changed |
| New Python Ruff lint/format | Passed following fixes; final check recorded in tool transcript |
| Frontend lint / TypeScript / production build | Passed with TypeScript 7.0.2 and Zod 4.6.7; upstream annotation warnings noted |
| Browser flows after security update | 37 Chromium checks passed; test APIs are explicit mocks, not real hosted data |
| Frontend `npm audit --omit=dev` | Initially one high Zod advisory; after focused update, zero reported vulnerabilities |
| PowerShell setup/start/task scripts | All three parsed successfully; no task registered or script launch/reboot rehearsal |
| Fallow 3.36.0 | Remains failing: 19 unused-file candidates, 16 unused-export candidates, one unresolved import, 43 clone groups, 180 complexity findings; root resolution warning limits classification |
| Neon development DDL | Exact additive destination migration committed on isolated child; PK/FK/checks read back; original staging parent schema verified untouched |
| Hosted inspection | Read-only Vercel settings/deployment state and Neon catalogs; no application endpoint/cold-start certification |

Recovery checks include producer rollback/no-op publication, destination-commit
local-ack failure, actual subprocess exit after destination commit, concurrent
worker exclusion, outage retries, retry exhaustion/requeue, identity conflict
isolation, disabled-source rejection, stale replay after tombstone, reconciliation,
source-delete policy and exact stored probability/quote/UTC projection parity.

The new CI workflow is prepared but has not run on GitHub. Database-backed Rust
tests needing separate env vars remain ignored/gated; do not count them as live
production validation. Numeric parity here covers publication, not a new ML model.

## Performance measurements

Final main JS entry: 661.62 → 341.37 kB, approximately 48% smaller. Main CSS:
148.36 → 97.49 kB, approximately 34% smaller. See `docs/performance-report.md` for
the intermediate route-only build and limits. API/query/cold-start/ingestion/
inference/simulation/bulk-write/sync throughput and CPU/RSS are not measured.

## Cloud state and user decision

Keep `footballheritage-staging` as staging; production project selection is deferred
by the user. Its original `staging` branch remains unchanged. Validation child
`codex-publication-contract-20261026` (`br-lucky-wind-b4r6rgn1`) is retained for review.
Requested autosuspend customization was rejected by account policy; no automatic
cleanup/suspend guarantee. Existing Vercel deployments still point at `d8aaa59`;
Preview env scopes are incomplete. No cloud credential values were exported.

## Remaining issues, risks and next phase

1. Critical: authentication sessions live in an instance-local DashMap. Add
   Neon-owned durable sessions without weakening revocation/idle-timeout checks;
   verify multiple independent API instances and cold restart.
2. Complete the Rust gateway/AI Picks/RAG/domain migrations over approved published
   data; the new native read endpoint does not remove existing Python dependencies.
   Preserve existing selection math and response contracts with parity tests.
3. Extend publication to existing league/multi-sport/model/simulation/trial/fantasy/
   intelligence outputs with explicit provider mapping and ownership contracts.
4. Validate actual restricted roles, source registration, verified TLS transport,
   network interruption and Neon throughput end-to-end on a development destination.
5. Measure source/query/ML bottlenecks before optimizing; do not infer a faster
   engine from language/dataframe choice. Resolve strict Clippy and remaining
   security/test gates before release.
6. Configure and test Windows task restart/stop/reboot operation and log retention;
   the prepared default task is interactive sign-in, not unattended startup.
7. Provision Preview env scopes and perform real hosted endpoint, CORS, SPA,
   auth, missing/stale prediction and cold-start verification with Python offline.
8. Only after those gates and production-target selection prepare a concrete
   cutover/rollback release and request explicit production deployment approval.
