# Published AI Picks phase — 2026-10-26

## Files changed

- `backend/src/pick_selection.rs`, `published_picks.rs`, `handlers/ai_picks.rs`,
  `main.rs`: native shared-pool publication reads and existing Python ranking rules.
- `backend/tests/fixtures/ai_pick_selection_contract.json`,
  `scripts/generate_pick_selection_contract.py`,
  `pipeline/tests/test_rust_pick_contract.py`: reviewed frozen Python contract.
- `pipeline/sync/football.py`, `pipeline/tests/test_publication_sync.py`: explicit
  sport guard, model manifest ordering/no-op behavior and observed quote selection.
- `scripts/verify_published_picks_http.py`, `verify_auth_http.py`: authenticated
  independent-process HTTP validation with the Python API offline.
- Both readiness/sync workflows, generated API/schema inventories,
  `docs/{published-ai-picks,neon-sync-design,migration-plan,architecture-audit}.md`,
  and `shared/CODEBASE_INDEX.md`: CI and current evidence.

## Implemented and preserved

Configured production/staging AI Picks reads approved PostgreSQL publications,
never local Python HTTP. Explicit missing-model/storage/source failures are 503;
expected missing fresh predictions produce an empty successful result. Existing
Football filters, value/probability selection, explanatory text, authenticated
saved runs and retrieval remain. Every eligible page contributes to ranking;
memory is bounded, reads are consistent and statement/total timeouts are finite.
Publication metadata and quote timestamps accompany estimates. Stable ties use
record-key order because the previous fixture query had no explicit ordering.

Python training, models, inference, simulations and numerical probabilities are
unchanged. Development without a publication stream keeps its existing Python
interface. Other sports are quarantined rather than mislabelled Football. Model
manifest and bundles enter one local transaction, manifest first; unchanged
projection does not create repeated events. Source correction resumes blocked rows.
No historical data, operational databases, user financial state or applied
migration bytes were changed by this phase.

## Executed verification

- `cargo fmt --check`, `cargo check`: passed.
- `cargo test --locked`: 39 passed, five explicit external/fixture tests ignored.
- Frozen Rust parity test: all 12 Python cases passed within 1e-12 tolerance;
  the Python source-hash/output test also passed. Its first invocation from the
  repository root failed to import `api`; rerunning from `pipeline/` passed,
  matching the CI working directory.
- Local publication suite: 19 passed, including termination after remote commit,
  lost acknowledgment, idempotency, concurrent worker exclusion, retries,
  quarantine/correction, manifest order/no-op and quote/probability parity.
- Real authenticated Rust HTTP checks passed in a newly created disposable local
  database: 160 eligible synthetic fixtures across pages plus five deliberately
  ineligible/invalid cases matched the actual Python ranker. Missing manifests,
  disabled sources, empty dates, saved-run retrieval, stale/future quote filtering
  and withdrawal behaved as specified with the Python HTTP service offline.
- The same harness rechecked independent-instance sessions, restart/revocation,
  registration rollback/retry and concurrent failed-login locking successfully.
- Changed Python code: Ruff lint and formatting checks passed after fixing one
  UTC alias diagnostic. GitHub workflow changes are prepared, not remotely run.

No representative API percentile, query-plan or throughput benchmark is claimed.
The fixtures above are synthetic test evidence, never runtime fallback data.
`cargo clippy --locked --all-targets -- -D warnings` failed with 35 diagnostics
for the application target and 36 for the test target, including the existing
test-module ordering diagnostic. No diagnostic referenced the new ranking or
publication-reader modules. This release gate remains failed and needs repair.

## Remaining risks and next phase

RAG still uses its optional prediction database; other gateway routes still proxy
Python. Complete those public data paths and multi-sport/provider ID contracts
before production cutover. New model selection requires reprojecting existing
fixtures; a manifest can arrive before all of its bundles and temporarily yield
empty picks. Realistic query plans, API latency/cold starts, Neon TLS/restricted
credential transport and hosted browser/API checks remain outstanding.

The existing Neon project is staging only, per user decision. This phase performs
no deployment, production credential change or destructive migration. Roll back
the code as a unit and retain additive records/history; never restore a production
dependency on the local computer. See `docs/rollback-plan.md`.
