# Production audit — 2026-10-22

Status: implementation and local verification completed, with release blockers documented below; this is not production approval. Existing uncommitted work was present before this audit and must not be included indiscriminately in release commits.

## Applications and dependencies

| Root | Application | Deployment assessment |
|---|---|---|
| `frontend/` | React 19, Vite 7, React Router 7, Tailwind 4, Zustand, React Query; public site and nested `/admin` dashboard | One Vercel Vite project, `npm ci`, `npm run build`, output `dist`; SPA rewrites required |
| `backend/` | Rust Actix-web 4 binary, SQLx 0.7/PostgreSQL, Argon2, JWT, AES-GCM wallets, governor rate limits | Persistent container recommended; native Rust Functions require a different entrypoint. Vercel container Services are a possible deployment model, subject to account availability and lifecycle verification |
| `pipeline/` | FastAPI, SQLAlchemy/Postgres, sklearn/XGBoost model files, ETL/provider collectors, paper trials and training CLIs | Dedicated API/worker compute with persistent artifact storage; training and ingestion stay out of request lifecycles |
| `chatbot/` | Express/Genkit/Gemini, PostgreSQL and Redis | Legacy separate Node service; Rust RAG chat also exists. Keep private behind authenticated API until its feature enforcement is integrated |
| `scripts/`, pipeline batch files | SSH Pegasus sync, scheduled collection, model training | Persistent worker/scheduler; existing Windows tasks and Pegasus systemd automation are distinct from web hosting |
| `backend/package.json` | Backend utility package | Not an independent web frontend |

There is no root npm workspace. Backend migrations live in `backend/migrations/` and run at startup. Backend application data and pipeline data use different databases. Rust RAG has a separate read-only pipeline connection. Existing admin components and styling must be reused.

## Routing and access

Rust routes use `/api/v1`; Python routes also use `/api/v1`. Browser clients currently connect to both services. Avoid appending the prefix twice. Frontend API fallbacks point to localhost; `pages/Chat.jsx` also hardcodes port 3000. API clients are spread across hooks, stores, pages and components. No active WebSocket client was found in the inspected application sources.

Roles are `user`, `admin`, `superadmin`. `RequireAdmin` trusts the signed JWT role without reloading the current database role/status. Ordinary auth stores sessions in a process-local DashMap: process restarts invalidate sessions, and replicas do not share sessions. The cosmetic role switcher is not authorization. Existing `/auth` operations, `/limits` self-exclusion and account security must remain accessible during feature maintenance.

No centralized feature registry or subscription entitlement schema was found. Build-time `VITE_ENABLE_*` variables are not backend authorization. Existing functionality includes AI picks/chat, predictions, betting intelligence, player props, parlays, wallet, betting, sports/leagues, FPL and college basketball. No verified payment-provider integration or subscription billing was found; wallet deposits directly credit balances and must not be advertised as real payment processing.

## Security and reliability findings

| Severity | Evidence / risk | Required action |
|---|---|---|
| Critical | Wallet deposit accepts a user amount and immediately credits it, without provider confirmation | Block production funding until a verified payment/ledger workflow exists; retain demo behavior only with explicit configuration |
| High | Wallet balance reads in mutations lack consistent row locking | Serialize money operations; verify concurrent debit/deposit behavior |
| High | Public pipeline endpoints include refresh and inference operations without shared user authorization | Make upstream private and proxy/gate requests through Rust; do not rely on CORS for authorization |
| High | JWT admin role is not rechecked; suspension can leave an existing token privileged | Reload database role/status for administrative actions; protect last active superadmin |
| High | Historical handover reports committed credential/hash-bearing SQL and known bootstrap credentials | Scan tracked source/history and rotate previously exposed credentials before release; do not reproduce credentials in reports |
| High | In-memory sessions and rate limits cannot safely support multiple replicas | Single API replica initially; externalize sessions and distributed limiting before scaling |
| Medium | Pool has fixed 50 max/10 min connections per replica; RAG has another pool | Budget/configure pools against hosted Postgres limits |
| Medium | `/health` returns monitoring status without a live DB readiness query; metrics publicly routed | Add readiness; restrict operational metrics at ingress |
| Medium | Production origins default to localhost when missing | Require an exact HTTPS origin allowlist in production; separate development defaults |
| Medium | Feature changes have no existing transactional audit mechanism | Add append-only transactional feature audit and default-deny unknown keys |
| Medium | Browser sessionStorage bearer tokens | No cookie-auth CSRF surface in this client, but XSS can steal tokens; maintain strict CSP and dependency/security scanning |

Existing rate limit middleware, validation, encryption, transaction handling and security headers are present; their presence alone is not evidence of end-to-end safety. Admin bet settlement routes remain commented out in `main.rs`.

## Integrations and local dependencies

Sources include football-data.org, The Odds API, BALLDONTLIE, CFBD, ESPN, nflverse, FPL and public sportsbook collectors through Scrapling. Gemini is used by Rust RAG and the legacy chatbot. Raw snapshots, model artifacts, certificates, browser automation dependencies, local caches and SSH credentials are not portable Vercel static assets. Provider secrets belong only in backend/worker environments. Never expose them through `VITE_*`.

## Existing delivery and test assets

`.github/workflows/ci.yml` checks Rust, frontend lint/build, chatbot syntax and Python tests. Rust has unit tests and `.sqlx` offline metadata; frontend has Playwright tests; pipeline has a substantial unittest suite. `chatbot`'s test script is a placeholder. `frontend/vercel.json` already defines Vite and SPA routing; earlier deployment assessment artifacts exist under `stages/05-deploy/output/`. No active application Dockerfile was found by the repository inventory.

Fallow initial invocation (`npx --no-install fallow --summary`) failed because Fallow is not installed locally. Analysis availability and baseline test results must be recorded before claiming repository-wide quality gates passed.

## Implemented remediation and final evidence

The feature migration, centralized evaluator/middleware, current-database admin checks, admin feature workspace, frontend route/navigation controls, private Python gateway, hosted database URL handling, production templates and CI/runbooks have been implemented. Wallet mutation reads now lock rows, production demo funding defaults to denied, database pool sizing is configurable, production origins are validated and `/ready` checks the database. Feature controls intentionally do not solve payment-provider verification, settlement completion, shared session persistence or historical-secret rotation.

Local verification: 26 Rust tests passed (three existing ignored DB tests); the new DB-backed feature integration test ran against an isolated PostgreSQL cluster. The complete 17-file migration chain passed there, treating the existing comment-only migration as a no-op. Python: 269 tests completed with 14 gated skips. JavaScript policy tests, frontend lint/typecheck, guarded production build, 38 selected existing/new Chromium browser tests and six expanded feature tests across Chromium/Firefox passed. The frontend production dependency audit found zero vulnerabilities.

Fallow was subsequently downloaded and run. Its repository-root baseline reported 405 issues with degraded root dependency resolution. A frontend-scoped audit reported 36 dead-code/dependency issues, 40 clone groups and 165 functions above threshold; after refactoring, the final focused health report had no complexity findings in the new feature modules/page. Overall repository Fallow gates remain failing. These counts are different scopes, not a before/after improvement claim.

A redacted signature scan of tracked text files up to 2 MB found no common AWS/Google/GitHub/private-key signatures, but confirmed password hashes in `backend/scripts/update_admin_password.sql`. That helper is removed from version control and ignored while its local copy is preserved; no application source references it. This was not a complete history/provider-secret scan. Rotate exposed credentials and review history before release; existing commits still contain the old file.

The Docker daemon returned an EOF during the image build, and its retry stalled. Task-owned build clients were stopped. The Dockerfile and optional Vercel Services example are provided but the container image/hosted topology are not certified. See the verification report under `stages/04-test/output/` for phase files, commits, failures and outstanding integration work in pre-existing untracked files.

The real temporary-server boot also confirmed historical migrations emit a bootstrap-credential notice and insert sample NBA Cup data. Application tracing now suppresses PostgreSQL notice events without changing applied migration checksums. Verify bootstrap-account rotation and sample-data exclusion before exposing a new database; this task did not delete existing records or rewrite migration history.

## Implementation and verification plan

1. Add backward-compatible feature migration and explicit registry; verify precedence/unknown-key rules with Rust tests.
2. Add transactional audited admin mutations, current database role checks, reusable API enforcement and effective access endpoint; exercise disabled direct API requests.
3. Add existing-style admin feature UI, user and role controls, confirmation and audit; verify browser visibility and route denial.
4. Configure normalized API URLs, private upstream topology, production CORS and readiness; verify preflight and URL construction.
5. Provide environment templates, Vercel/persistent-service deployment runbook, guarded CI and rollback checklist; run Rust, frontend and Python checks.

Production must remain blocked until real-money safety, secrets rotation, external service access and staging verification are signed off. No production deployment or destructive database operation is authorized by this audit.

## Phase 2 local staging findings — 2026-10-23

The active chatbot is the Rust RAG agent; the Node chatbot is legacy and optional. A dedicated release worktree captures required source dependencies separately from unrelated existing work. A missing bookmaker registry and incomplete clean-CI Python dependencies were discovered and corrected. See `docs/STAGING_SOURCE_INTEGRITY.json` for provenance.

Logout was a success-only stub and did not revoke server sessions. It now revokes the verified session, and all frontend logout paths invoke it before clearing storage. Production funding can no longer be enabled through the old demo environment override; production bet-placement writes are also blocked pending financial lifecycle verification. Wallet balance reads no longer create wallets, simultaneous first deposits lock their owner, and a new additive unique-owner index prevents duplicate wallets. Metrics now require current administrative authorization.

The isolated native environment passed DB-backed feature/financial tests, 40 API acceptance checks and a real browser admin/user/logout flow. Its migration credential is separated from its non-owner runtime credential. The native PostgreSQL database, synthetic predictions and new secrets are isolated; no existing databases or credentials were changed. Details and explicit limitations are in [LOCAL_STAGING.md](LOCAL_STAGING.md) and the Phase 2 verification report in `stages/04-test/output/`.

Docker Desktop metadata I/O errors required a normal restart. The engine recovered, but BuildKit's pinned Rust compiler still returns no version/output and produces no binary, even in a minimal application-independent build. The same compiler runs normally in a container. The release image, container port binding, signal handling, PostgreSQL 17 topology and hosted staging remain unverified. Native Windows checks do not close those gates. Historical bootstrap accounts/sample data, complete secret/history scanning, payment/settlement, model artifacts, hosted ingress and backup/restore remain production blockers.
