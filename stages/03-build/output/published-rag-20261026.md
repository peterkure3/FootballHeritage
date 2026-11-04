# Published RAG phase — 2026-10-26

## Delivered

RAG now reads approved Football publications through the existing application
pool in non-development environments or whenever a stream is configured. It
does not parse or connect to `RAG_DATABASE_URL` in that mode. Development without
a publication stream retains the existing optional legacy reader.

`backend/src/published_picks.rs` exposes a shared paginated candidate visitor;
AI Picks retains its existing ranker and response contract. RAG uses the same
active-model, enabled-source, ID, sport, upcoming-status, prediction freshness,
probability and quote-time checks. Its bounded 200-candidate relevance window
considers every eligible page before selecting up to five predictions. Evidence
includes stream/key, publication version/time, model and prediction timestamps.
Knowledge reads remain in the application database, with a three-second timeout;
published prediction retrieval has a ten-second timeout. Missing/disabled/error
states return unavailable prediction evidence without a legacy fallback.

Changed files: `backend/src/{rag,published_picks,published}.rs`,
`backend/.env.example`, `scripts/verify_auth_http.py`, new
`scripts/verify_published_rag_http.py`, `docs/{published-rag,migration-plan,
architecture-audit,VERCEL_DEPLOYMENT}.md`, and `shared/CODEBASE_INDEX.md`.

## Executed verification

- `cargo fmt --check`: passed after formatting the changed code.
- `cargo test --locked`: **40 passed, five explicitly ignored**, including frozen
  Python ranking parity and the new 350-candidate RAG relevance regression.
- Existing Python 3.14 and the Scrapling environment have no Ruff module; those
  first module invocations failed. The installed Python 3.12 Ruff executable then
  formatted both changed scripts; `ruff check` and `ruff format --check` passed.
- `pipeline/.venv-scrapling/Scripts/python.exe scripts/verify_auth_http.py`:
  **passed**, using a newly created disposable loopback database that the harness
  removed afterward. The production-mode Rust processes started with an invalid
  legacy RAG URL and unreachable Python URL. RAG found a named team after 249
  earlier records, preserved numerical probabilities and publication provenance,
  excluded old/future quotes, persisted history, replayed request IDs without
  duplication, inherited the named team on follow-up, and suppressed prediction
  evidence for disabled sources, missing manifests and withdrawals. Authentication,
  independent-process/restart/revocation, registration rollback/retry, concurrent
  login locking and multi-page AI Picks/Python parity also passed again.
- Strict `cargo clippy --locked --all-targets -- -D warnings`: **failed**, with
  the same 35 application / 36 test-target diagnostics recorded in the preceding
  phase. None referenced the changed RAG/publication-reader modules. No lint
  suppressions were added.
- Initial `npx --no-install fallow --summary` could not find a local package.
  Approved `npx --yes fallow --summary` completed with existing findings (36 dead
  code issues, 43 clone groups, 180 complexity findings). Post-change
  `fallow audit --format json` returned `warn`: no introduced dead code or clone
  groups; the reported complexity finding was in existing frontend test code.
  Analysis spans the large pre-existing working tree, not this phase alone.
  Root dependencies are absent and architecture boundaries are unconfigured,
  so those checks are degraded/unmeasured; this is not Rust validation.

## Remaining scope and risks

Only RAG is migrated by this phase. `pipeline_gateway.rs` still serves Python
domains. `docs/published-rag.md` maps the remaining callers and required producer,
response-parity, identity, calculation and administrative-command contracts.
These include dashboard/operations/trials, history/accuracy/models, multi-sport
previews, betting intelligence/parlays, FPL, college sports and Smart Assistant.
Existing Football bundles do not represent those domains completely. Preserve
their functionality while implementing each adapter; do not replace them with
empty successful snapshots or disable them as a substitute for migration.

No representative latency, throughput or query-plan benchmark is claimed. Hosted
API/browser verification, restricted Neon credentials/TLS, complete gateway
parity and strict Clippy repair remain release gates. AI provider generation was
not exercised; the HTTP harness uses grounded mode. Saved request replays retain
their original response evidence, as before.

The working tree was already extensively modified/untracked; this phase did not
commit or clean up unrelated work. No applied migration bytes, operational data,
Python models, ranking algorithms or credentials were changed. Neon remains
staging. No production deployment or hosting-setting changes were made.
