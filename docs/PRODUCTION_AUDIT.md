# Production audit — 2026-10-22

Status: implementation in progress; this is not production approval. Existing uncommitted work was present before this audit and must not be included indiscriminately in release commits.

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

## Implementation and verification plan

1. Add backward-compatible feature migration and explicit registry; verify precedence/unknown-key rules with Rust tests.
2. Add transactional audited admin mutations, current database role checks, reusable API enforcement and effective access endpoint; exercise disabled direct API requests.
3. Add existing-style admin feature UI, user and role controls, confirmation and audit; verify browser visibility and route denial.
4. Configure normalized API URLs, private upstream topology, production CORS and readiness; verify preflight and URL construction.
5. Provide environment templates, Vercel/persistent-service deployment runbook, guarded CI and rollback checklist; run Rust, frontend and Python checks.

Production must remain blocked until real-money safety, secrets rotation, external service access and staging verification are signed off. No production deployment or destructive database operation is authorized by this audit.
