# Production deployment

No production deployment has been performed as part of this preparation. Replace example domains with your actual owned domains before deployment; no production frontend/admin origins were supplied in the task.

## Frontend `VITE_API_URL` build failure

Authenticated follow-up: global CLI 65.2.0 is working and signed in as `peterkure3`. The hosted frontend root is `frontend`; its latest existing production deployment is `READY`. `VITE_API_URL` is present only in Production, while the other four frontend variables also cover Preview. Both projects currently designate `feature/footballheritage-frontend` as their **production branch**. Review that designation before pushing or redeploying; this branch is not presently a Preview target. Earlier logged-out/access-blocked observations below describe the initial investigation.

The hosted backend root is currently `backend/src`; the intended package root is `backend`. Its latest failed build reports 16 compile-time SQLx database connection errors. Repository Cargo config now defaults to the checked-in offline query cache, preserving database-free builds. Before any runtime smoke test, explicitly set backend `APP_ENV=production` and `RUN_MIGRATIONS=false` in the reviewed target scope; neither name was present in the hosted environment inventory. No hosting settings or deployments were changed during inspection.

`frontend/vercel.json` deliberately runs `npm run build:production`. The validator loads Vite's production environment and process overrides, and requires an HTTPS Rust API origin or its `/api/v1` URL. A local HTTP development URL in `.env` is not valid deployment configuration. Set `VITE_API_URL` in **football-heritage-frontend**, scoped to the deployment's Preview or Production environment; check branch-specific Preview overrides too. Do not put this variable only in the Rust project or point it at the Vite site or private FastAPI service. `VITE_PIPELINE_API_URL` is obsolete: browser pipeline traffic goes through Rust's authenticated `/api/v1/pipeline` gateway.

The validator and production API client share the same URL checks. Production bundles cannot silently fall back to localhost, even if someone bypasses the validation script. Missing/invalid URLs and secret-like public variables remain errors. Do not bypass validation, insert a fake backend URL, or relax HTTPS to obtain a green hosted build. The `.env.production.example` URL is a template, not a running API.

On this Windows workstation, the working checkout is `D:\Github\FootballHeritage`; `C:\FootballHeritage` contains backups. CLI 65.2.0 can be run with `npx --yes --package=vercel@65.2.0 vercel --version`; the global installation was incomplete and the CLI authentication check reported logged out. The catalog project IDs are `prj_T0Aus4LHcFJJRMNKtmdVXLRbd5ad` (frontend) and `prj_0r4mFmPbEpDGrvHKLPK76tXuKxdh` (backend), in team `team_PbpiKdM3J9zfUN4UpZnixHZy`. No local `.vercel/project.json` or `.vercel/repo.json` mapping was found. Authenticate and verify each project's folder, team and root before deliberately linking it; no link or cloud setting was changed during diagnosis. Actual hosted environment scopes remain unverified because team-scoped connector reads returned 403. See [the staging investigation](../stages/05-deploy/output/vercel-staging-20261024.md).

For the multi-binary Rust build error, see [Rust binary selection and runtime blockers](../backend/docs/VERCEL_BINARY_SELECTION.md). The API is the explicit Cargo default; initialization/reset targets require an operator-only feature. A successful binary selection does not establish native Vercel Functions compatibility for Actix.

## Hosting topology

| Component | Root | Target / command |
|---|---|---|
| Public web and admin dashboard | `frontend/` | Vercel Vite project; install `npm ci`; build `npm run build:production`; output `dist` |
| Actix API | `backend/` | Persistent container: `docker build -t footballheritage-api:<commit> backend`; listen on `0.0.0.0:$PORT`; managed HTTPS ingress |
| Python API | `pipeline/` | Private persistent service: `python -m uvicorn api.main:app --host 0.0.0.0 --port 5555`; provision dependencies/model artifacts separately |
| ETL, training, paper trials, Pegasus sync | `pipeline/`, `scripts/` | Existing persistent worker/systemd/Windows Task Scheduler infrastructure; durable data/model storage |
| Legacy chatbot | `chatbot/` | Private Node service, `npm ci --omit=dev`, `npm start`; optional if all clients use Rust RAG |
| PostgreSQL / Redis | External managed services | Separate application and pipeline credentials/databases; private network/TLS, backups and connection budgets |

The admin UI is a route within the existing frontend, not another build. If a separate admin domain is desired, attach it to this same Vercel project and include it in the API origin allowlist. Do not invent a second root directory or duplicate the admin application.

Set the frontend project's Node.js version to `22.x`, matching the added readiness workflow. Vite environment values are embedded at build time, so changing an API URL requires a rebuild.

`deploy/vercel-services.example.json` provides an optional combined-project configuration for a reviewed Vercel container proof of deployment. Its project root is the repository root; copy it to root `vercel.json` only when deliberately selecting that topology. It routes `/api/*` to the existing Actix container and everything else to the Vite service. The Docker entrypoint already binds to the platform's `PORT`. The standalone frontend configuration remains the default. The combined example is not deployment-verified; confirm the current service schema, account support, private upstream reachability, frontend security headers and process-local session behavior before using it.

Vercel documents [Rust Functions](https://vercel.com/docs/functions/runtimes/rust) using `vercel_runtime` handlers, and [Services](https://vercel.com/docs/services) with container runtimes. The [current Rust adapter](https://github.com/vercel/vercel/blob/main/packages/rust/src/standalone-server.ts) additionally supports whole-app HTTP servers through a standalone proxy without `vercel_runtime`; Actix is therefore not categorically incompatible. Confirm that the selected adapter supports that mode, with project root `backend` and entrypoint `src/main.rs`. Its missing `[build]` assumption is worked around in `backend/.cargo/config.toml`; see the binary-selection note. Scale-to-zero, instance replacement and process-local authentication/rate-limit state still require hosted verification. A persistent Docker service on Railway is the recommended fallback if the selected runtime lacks standalone support or its lifecycle is unsuitable: set service Root Directory to `backend`, use the existing `Dockerfile` and `/app/server` command, and honor the assigned `PORT`. Keep one replica until sessions and rate limits use shared storage. No Railway resource or deployment is created by these instructions; the local Docker build must pass first. A Node/Python Function cannot host the Rust binary by merely changing `vercel.json`.

## Environment configuration

Copy secret-free `.env.production.example` templates into your hosting provider's environment settings, not into git. `frontend/.env.example`, `backend/.env.example`, `pipeline/.env.example`, `chatbot/.env.example` remain development references. Browser build variables are public.

| Environment | Required settings |
|---|---|
| Vercel frontend | `VITE_API_URL=https://api.YOUR_DOMAIN/api/v1`; optional `VITE_SESSION_TIMEOUT`, `VITE_ENV=production`, `VITE_ENABLE_DEBUG=false` |
| Rust API | `APP_ENV=production`, database `DATABASE_URL` with TLS, random `JWT_SECRET` (at least 32 bytes), existing stable `ENCRYPTION_KEY` (exactly 32 bytes), `HOST=0.0.0.0`, host-provided `PORT`, `HTTPS_ENABLED=false` behind trusted TLS ingress |
| Rust origins | `ALLOWED_ORIGINS=https://YOUR_WEB_DOMAIN,https://YOUR_ADMIN_DOMAIN`; exact origins only, no wildcard/path/trailing slash; localhost allowed separately in development |
| Rust data sources | RAG, AI Picks and gateway use `DATABASE_URL` and an approved `PUBLICATION_STREAM_ID`. Python/Node service URLs and the legacy RAG database URL are development-only. `RAG_CHAT_MODE=grounded` or configured Gemini key/model. Provision the separate outbound gateway worker, additive schema and scoped grants before rollout; see `durable-gateway.md`. Deploy the frontend polling helper before switching the backend to pending-response contracts. |
| Python | `APP_ENV=production`, same internal token, its own `DATABASE_URL` and read-only `HERITAGE_DATABASE_URL` with TLS options; `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `PGSSLMODE=require` for legacy collectors; provider keys `FOOTBALL_DATA_ORG_API_KEY`, `THE_ODDS_API_KEY`, `CFBD_API_KEY`, `BALLDONTLIE_API_KEY` |
| Observability | `RUST_LOG=info`, `METRICS_ENABLED`, worker `LOG_LEVEL`; protect `/metrics` at ingress and route logs to your provider's private log sink |
| Legacy optional Node chatbot | `NODE_ENV=production`, `DATABASE_URL`, `JWT_SECRET`, `CHATBOT_INTERNAL_TOKEN` (at least 32 bytes, shared only with Rust), `GEMINI_API_KEY`, `ALLOWED_ORIGINS`; private ingress, optional Redis per existing service configuration |

`VITE_PIPELINE_API_URL` is obsolete: browser Python requests derive `/pipeline` from the normalized Rust API URL and forward the user bearer token. Both `https://api.example.com` and `https://api.example.com/api/v1` normalize to exactly one `/api/v1`. Never put provider keys/internal tokens/database passwords in `VITE_*`. The production validator rejects localhost and secret-like public variables. Keep `ALLOW_DEMO_WALLET_FUNDING=false`: no real payment integration is implemented.

The Docker build uses the checked-in SQLx offline cache and embeds migrations. It excludes `.env`, certificates, scripts, logs, backups and local targets. The API defaults to additive migrations at startup for compatibility. Persistent staging uses the dedicated `/app/migrate` binary with `MIGRATION_DATABASE_URL`, followed by `RUN_MIGRATIONS=false` and a non-owner `DATABASE_URL` for the API. Grant runtime DML/sequence permissions explicitly, revoke write access to `_sqlx_migrations`, and verify audit triggers remain effective. Review migrations during an approved release window with a backup. Do not rotate `ENCRYPTION_KEY` without a reviewed re-encryption migration: existing wallet balances depend on it.

## Deployment order

1. Finish the production checklist, commit/review the existing workspace work as well as this task's changes, and verify a clean checkout in CI. The initial working tree contained extensive pre-existing changes; do not deploy an incomplete commit set.
2. Provision staging PostgreSQL/Redis and private persistent service networking. Restore a sanitized test database, verify backups and rotation of previously exposed credentials.
3. Obtain release approval before any production database operation. Apply/review the additive feature migration first in staging. Verify seeded access, superadmin recovery and immutable audit history.
4. Deploy the private Python service with its internal token, provider credentials and existing model/data artifacts. Direct anonymous requests must return 403. Keep ingestion/training on persistent workers; do not schedule them through Vercel request handlers.
5. Build/deploy the Rust container on the approved persistent host. Configure exact origins, TLS ingress and secrets. Keep one replica. Verify `/health` and database-backed `/ready`; neither should disclose credentials. Constrain the public surface to Rust only.
6. Create/link the Vercel project with **Root Directory `frontend`**, framework **Vite**, and the commands above. Import `frontend/vercel.json`. Set the correct staging HTTPS API URL for Preview and the actual API URL for Production. Production builds fail when the URL is missing/local.
7. Create a preview deployment, test deep links (`/admin/features`, `/ai-picks/chat`), HTTPS assets, auth/logout/self-exclusion, admin role revocation, user restrictions, emergency disable, audit history and CORS preflight. Test from the browser's actual origin, not only curl without Origin.
8. After explicit human release approval, deploy/promote production and repeat smoke checks. Configure protected production branches and required checks. Pause/unlink automatic production domain assignment until approval; a plain push must not bypass the release process.

Vercel Git integration supplies build/deployment automation. `.github/workflows/production-readiness.yml` adds DB-backed policy tests, browser checks and a guarded production build with no production credentials. Existing CI remains in place. Configure required checks on the production branch. The optional manual preview workflow requires a protected `vercel-preview` environment, reviewed exact CLI version and repository IDs/token in GitHub settings. No workflow in this change promotes production.

## Rollback

Record the previous frontend deployment ID, API image digest, configuration versions and feature audit cursor before release. On a frontend regression, use Vercel's prior-deployment rollback after authorization; verify subsequent production auto-assignment behavior. Redeploy the prior API image if compatible with the additive schema. Keep feature tables and audit history: do not drop them or run destructive down migrations. Restore feature values through audited admin mutations, including clearing emergency restrictions explicitly. A previous API binary does not enforce the new feature policy: keep gated ingress/maintenance and do not roll back to it while restrictions are relied on. Pause affected workers separately. For database incidents, follow the provider's approved restore/PITR procedure; never overwrite production from a developer machine.

## Known limits

The container image and hosted networking require platform verification; no container engine or cloud release is implied by a local build. Process-local sessions expire on API restarts. Public guest content cannot enforce the identity of a logged-out user. Existing settlement gaps, funding-provider safety, migration credential separation, provider quotas, durable worker/model storage, historical-secret remediation and repository-wide Fallow findings remain release work. Feature switches are not a regulatory/compliance approval for real-money operation.

For isolated local staging configuration, exact commands, verification limits and rollback, see [LOCAL_STAGING.md](LOCAL_STAGING.md).
