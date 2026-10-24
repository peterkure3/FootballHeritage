# Vercel staging diagnosis — 2026-10-24

## Authenticated follow-up — current findings

The user completed device authorization. Global Vercel CLI **65.2.0** is installed and `vercel whoami --non-interactive` confirms **`peterkure3`**. GET-only CLI inspection now succeeds for both explicitly scoped projects. Earlier authentication and hosted-access blockers described below are historical; connector authorization is separate from the working CLI session.

| Item | Confirmed hosted state |
|---|---|
| Frontend root / preset | `frontend` / `vite` |
| Backend root / preset | **`backend/src`** / `rust`; recommended package root is `backend` |
| Production branch, both projects | **`feature/footballheritage-frontend`**, so a push to this branch can trigger production deployments |
| Hosted Node.js | `24.x`, both projects |
| Frontend `VITE_API_URL` | Exists in **Production only**; no Preview or branch-specific entry returned |
| Other frontend variable names | `VITE_ENV`, `VITE_SESSION_TIMEOUT`, `VITE_ENABLE_ANALYTICS`, `VITE_ENABLE_DEBUG`, all Preview + Production |
| Backend environment | 37 variable names returned, **all Production-only**; `DATABASE_URL`, `RAG_DATABASE_URL`, auth/encryption keys, origins and pipeline token names exist |
| Missing explicit backend settings | **`APP_ENV`**, **`RUN_MIGRATIONS`**, `DB_MAX_CONNECTIONS`, `ALLOW_DEMO_WALLET_FUNDING` |
| Latest existing frontend deployment | `READY`, `dpl_HCeNKYnuDKYn5D9SQriQn4jXKmFs`, commit `3eae0b3` |
| Latest existing backend deployment | `ERROR`, `dpl_5fhxaLCTjrweSYTNCRkuVtY5Pni6`, commit `3eae0b3` |

Project-level build/install/output overrides are null; the frontend's checked-in `vercel.json` supplies its production validator/build command and `dist` output. No local project links were created. Values were not decrypted or saved: `hosted-configuration-redacted.json` contains only selected project settings, environment names/types/scopes and deployment metadata. The production API URL's value/endpoint and the database URLs remain unverified.

### Actual hosted build logs

The earlier frontend error `dpl_BtjTUS5CYdaaFs9JjzynMToDnb7L` fails in the production environment validator with the exact `VITE_API_URL` error reproduced locally. More recent existing frontend deployments are `READY`; this is evidence that their builds completed, not proof that browser/API integration works. The missing Preview variable is still a confirmed separate configuration gap.

The latest failed backend log shows **16 compile-time SQLx macro errors**, `error communicating with database: Connection refused (os error 111)`, from `cargo build -p football-heritage-backend --bin football-heritage-backend --quiet --release`. This establishes the current compiler failure separately from the earlier binary-selection and adapter-table errors. Current project root `backend/src` should be corrected to `backend`, but the API did not return a historical root for this failed deployment, so that setting is not asserted as the cause of these 16 SQLx errors.

Added `[env] SQLX_OFFLINE = "true"` to **`backend/.cargo/config.toml`**. Cargo builds now default to the checked-in `.sqlx` cache without requiring a live database or a shell-provided offline flag. Cargo's normal environment precedence is retained for separately authorized query-cache maintenance. The manifest, lockfile, application source and migrations are unchanged. Check/build verification explicitly removed the shell's `SQLX_OFFLINE` and supplied a dummy database URL. A forced `cargo rustc` probe and database-free unit tests are recorded in the follow-up logs.

The first forced executable recompile hit Windows `Access is denied` while replacing the existing `.exe`; it did not establish a compiler error. The running/locked executable was left alone. A fresh `cargo rustc --locked --profile check --bin football-heritage-backend -- --cfg sqlx_offline_build_probe` then **passed**, re-evaluating the SQLx macros with the dummy URL and no shell offline override. All 31 database-free unit tests also pass with the Cargo offline default.

Before any backend runtime invocation, configure **`APP_ENV=production`** and **`RUN_MIGRATIONS=false`** deliberately in the appropriate hosted scope. Absent these, source defaults to development behavior and boot-time migrations. No function URL, `/health`, `/ready`, or frontend flow that could cold-start the backend was invoked. This prevents an otherwise read-only-looking smoke test from executing migrations against restored data. The missing demo-funding flag defaults to false; keep it explicitly false rather than enabling funding.

Recommended hosted changes, not performed: correct the backend root, supply the runtime safeguards, review the intended production branch, and add the real API URL to Preview if staging should use Preview. The branch's current production designation means Preview-only values will not configure its normal Git-triggered builds. Do not push/redeploy merely to test these findings without the user's deployment approval. No cloud setting, deployment, promotion, Neon data, role or schema was changed during this follow-up.

Sanitized existing build logs are saved as `hosted-frontend-error.log` and `hosted-backend-error.log`. The older backend `READY` deployment yielded no build log output; readiness alone is not treated as proof of a functioning API.

## Scope and verified environment

Worked on `feature/footballheritage-frontend`, based on `3eae0b3`, in `D:\Github\FootballHeritage`. The requested `C:\FootballHeritage` directory contains only `backups`, not a Git checkout; the user confirmed the D: workspace. Existing migration changes, `frontend/.env`, and prior index entries were preserved. No commit, push, deployment, promotion, environment-variable mutation, database connection, migration, backup/restore, wallet tool or real-money enablement was performed during this investigation.

### CLI, links and hosted access

- The global npm installation is incomplete: there is no usable `vercel` command on PATH and its package directory lacks `package.json`. `npm list -g vercel --depth=0` reports `vercel@` without a version.
- `npx --yes --package=vercel@65.2.0 vercel --version` works and reports **65.2.0**. This uses npm's cache; it does not repair the global installation.
- The pinned CLI's `whoami --non-interactive` reports **Logged out**, exit 1. No automatic login or temporary deployment was attempted. Node is 24.13.0 locally; deployment CI uses Node 22.
- No `.vercel/project.json` or `.vercel/repo.json` was found at the root or in the three services. No project was automatically linked.
- The connected Vercel catalog confirms these projects in `team_PbpiKdM3J9zfUN4UpZnixHZy`:

| Service folder | Catalog project | Project ID | Local link / hosted root verification |
|---|---|---|---|
| `frontend/` | `football-heritage-frontend` | `prj_T0Aus4LHcFJJRMNKtmdVXLRbd5ad` | No link; intended root `frontend`; actual hosted root unverified |
| `backend/` | `footballheritage-backend` | `prj_0r4mFmPbEpDGrvHKLPK76tXuKxdh` | No link; intended root `backend`; actual hosted root unverified |
| `pipeline/` | No matching pipeline project in the returned football catalog | — | No link or deployment configuration verified |

Project-details and environment-list requests with `decrypt=false` returned **403 team authorization required** for both projects. A team-consent link was supplied in conversation. The actual hosted framework/build settings, production branch, deployment logs, environment-variable names, scopes and branch overrides therefore remain **unverified**. Local examples and the required contracts below are not evidence that hosted variables exist. No environment values were printed or decrypted.

## 1. Frontend — React/Vite

### CLI login follow-up

After the user installed the global CLI, `vercel --version` and its package manifest both report 65.2.0 on Node 24.13.0. The earlier incomplete-global-install finding is historical. The user then reported `TypeError: fetch failed` during login. Follow-up probes found working DNS, no configured environment/WinHTTP/user proxy, successful certificate-verified Node fetch to `https://vercel.com/.well-known/openid-configuration` (HTTP 200), and successful HTTPS transport to the unauthenticated API endpoint (HTTP 403). Both default fetch and explicit IPv4 HTTPS completed. No certificate bypass, proxy change or DNS override was needed.

An actual `vercel login --non-interactive` retry, with browser auto-launch disabled via process-only `CI=true`, successfully reached the device authorization stage. Its approval link was supplied in conversation; authentication still requires the user's approval. The original transport error did not recur, so its exact cause remains unproven and may have been transient. `vercel-network.log` and the read-only `diagnose-vercel-network.mjs` preserve the non-secret transport evidence. No login tokens or device authorization codes are included in those files.

### Root cause and reproduction

`frontend/vercel.json` runs `npm run build:production`, which validates configuration before TypeScript/Vite. The real validator loads Vite's production environment files and process overrides. The local file has an HTTP development API URL. The baseline command failed with:

```text
Error: Set VITE_API_URL to the production HTTPS API origin or its /api/v1 URL.
```

This is an intentional configuration gate, not a Vite compiler failure. Missing values, HTTP/localhost URLs, credentials, query strings, fragments or an unsupported path fail validation. A value configured only in the backend project, Development scope, or the wrong Preview branch will not satisfy a frontend hosted build. The remote failure's exact missing/incorrect scope cannot be established without team access.

The API client normalizes an origin or `/api/v1` base to exactly one API prefix. Browser pipeline requests use `${API_BASE_URL}/pipeline`, behind the Rust gateway. A separate `VITE_PIPELINE_API_URL` is unused and must not expose a private upstream. The old API client could silently use localhost when production validation was bypassed.

### Changes made

- `frontend/src/utils/apiUrl.js`: added `productionApiBase`, sharing the validator's HTTPS/origin/path restrictions with the browser client.
- `frontend/src/utils/api.js`: production mode requires a valid configured URL; development retains its existing fallback. Session token handling and endpoint routes are unchanged.
- `frontend/scripts/validate-production-env.mjs`: uses the shared URL contract, distinguishes missing/invalid configuration, explains the frontend project and Preview/Production scope, and never echoes values. Secret-like public variable names remain forbidden.
- `frontend/.env.example`: removed the obsolete direct pipeline URL and documented the authenticated Rust gateway.
- `frontend/tests/production-env.test.mjs`: tests valid URL forms, rejected destinations, public-secret rejection, redacted errors, Vite file loading and process override precedence.
- `.github/workflows/production-readiness.yml`: runs the new configuration tests alongside existing production-policy tests.
- `docs/VERCEL_DEPLOYMENT.md`: documented diagnosis, local CLI/link status and the required hosted setting. No actual URL or `.env` file was changed.

### Tests and results

| Command / check | Result |
|---|---|
| Baseline `npm run build:production` | Expected failure with local HTTP config; log retained |
| `node --test tests/production-policy.test.mjs tests/production-env.test.mjs` | **7 passed**, zero failures |
| `npm run lint` | **Passed** |
| `npm run build:production` with process-only `VITE_API_URL=https://api.example.test/api/v1` | **Passed** TypeScript and Vite; 1,930 modules transformed |

The `.test` URL proves build/configuration behavior only. It is not a deployed backend, and no request to that hostname was made. The build output is a diagnostic artifact and must not be published as a configured staging frontend. The normal production build must continue to fail until a real staging HTTPS API URL is provided.

### Remaining blockers and recommended fix

Authenticate the CLI or authorize the connector, verify the frontend project Root Directory is `frontend`, build is `npm run build:production`, install is `npm ci`, and output is `dist`. Deliberately link the frontend folder only after its project/team are confirmed. Set **public** `VITE_API_URL` in the frontend project's matching **Preview** environment for this staging branch, accounting for branch overrides. Use a separately reviewed Production value when production work is authorized. Do not bypass the validator or substitute the frontend URL, a fake backend URL, or the private FastAPI URL.

## 2. Rust backend — Actix/SQLx

### Root causes and compatibility

The previous binary ambiguity and `undefined … target` workaround are already present in `3eae0b3`: explicit `default-run`, explicit binaries, feature-gated maintenance tools and an empty Cargo `[build]` table. The upstream adapter's `cargoBuildConfiguration?.build.target` access assumes the table exists. It is an adapter assumption about valid Cargo configuration, not a Rust compiler error. No new manifest, lockfile, target or application rewrite was needed.

Current upstream `@vercel/rust` has whole-app **standalone HTTP proxy mode** for a selected Cargo binary without `vercel_runtime`. Actix can satisfy that mode by binding the assigned `PORT`. The older `api/` function-handler model uses a request bridge. Consequently, Actix is not categorically incompatible with Vercel, but the selected hosted adapter/version/entrypoint must be verified. Use `src/main.rs` or `football-heritage-backend`, never an initialization or migration binary. No successful hosted runtime acceptance or complete Windows Vercel prebuilt build is claimed.

The native API reads `HOST`/`PORT` and connects to PostgreSQL **before listening**. Migrations run by default unless `RUN_MIGRATIONS=false`. Authentication sessions and rate limits are process-local; instance replacement and multiple replicas need separate runtime verification/shared state. Those are lifecycle issues a compiler pass cannot resolve.

### Database and staging configuration

The redacted local inventory confirms `DATABASE_URL` selects `football_heritage`, `RAG_DATABASE_URL` selects `football_betting`, and the local JWT/encryption key lengths satisfy existing checks. However, both URLs are local, not Neon, and do not request TLS. `RUN_MIGRATIONS` is not explicitly disabled in that local file. This describes development configuration only; it does not contradict the user's restored Neon staging databases or verify hosted wiring. The service was not started with these files.

| Required staging setting | Contract |
|---|---|
| `APP_ENV` | `production`, to retain production controls even in a Preview deployment |
| `DATABASE_URL` | TLS connection to the existing **staging `football_heritage`** database with a restricted runtime role; pooled application URL where compatible |
| `RUN_MIGRATIONS` | `false`; no boot-time migration of the restored database |
| `JWT_SECRET` | At least 32 characters; staging-specific secret |
| `ENCRYPTION_KEY` | Exactly 32 bytes; must match the restored wallet data's existing key; do not rotate casually |
| `HOST`, `PORT`, `HTTPS_ENABLED` | `0.0.0.0`, platform-assigned port, `false` behind trusted HTTPS ingress |
| `ALLOWED_ORIGINS` | Exact staging frontend HTTPS origin(s), no wildcard, path or trailing slash |
| `PIPELINE_API_URL` | Reachable private FastAPI base ending in `/api/v1`; not localhost across separate hosts |
| `PIPELINE_INTERNAL_TOKEN` | At least 32 bytes, identical to the private pipeline service |
| `RAG_DATABASE_URL` | TLS read-only access to staging **`football_betting`**; direct connection for current session-setting callback |
| `RAG_CHAT_MODE` | `grounded` for the existing no-provider-key mode; provider credentials stay server-side if later enabled |
| `DB_MAX_CONNECTIONS` | Explicit budget accounting for all instances and the separate RAG pool (up to 5 additional connections) |
| `ALLOW_DEMO_WALLET_FUNDING` | `false`; no real payment integration enabled |

`RagAgent::from_env` issues session `SET default_transaction_read_only` and `SET statement_timeout` after connecting. Neon transaction pooling does not preserve arbitrary session state. Use a **direct** RAG connection with a database-enforced read-only role for this implementation. A future pooler adaptation needs reviewed transactional/role-level behavior; no role, grant, schema or database was modified. Any separately approved migrations would use the dedicated migrator and a direct credential, not the request-serving pool.

### Changes, tests and blockers

No Rust implementation/configuration change was necessary in this pass. Existing fixes and `Cargo.lock` were preserved.

| Command | Result |
|---|---|
| `SQLX_OFFLINE=true cargo check --locked` from `backend/` | **Passed** |
| `SQLX_OFFLINE=true cargo build --locked --bin football-heritage-backend` | **Passed**, Windows executable compiled; not executed |
| `SQLX_OFFLINE=true cargo test --locked --bin football-heritage-backend -- --skip database_policy_and_http_enforcement --skip financial_operations_are_serialized_and_balance_reads_do_not_create_wallets` | **31 passed**, zero failed, 3 ignored, 2 database-writing tests explicitly filtered |
| Local backend Docker build retry | Stalled before emitting diagnostics; stopped only the task's tagged build process |

SQLx 0.7.4 still emits its existing future-compatibility warning. The earlier investigation documented a zero-byte `rustup` executable inside BuildKit; see its retained logs. This retry does not establish a new compiler failure or a successful Linux image. Repair the local Docker build environment and obtain a successful locked Linux build before accepting an image. Verify hosted adapter/root/entrypoint and staging runtime/DB settings once authenticated. If standalone Vercel support is unavailable or lifecycle behavior is unsuitable, use the existing Dockerfile on a persistent **single-replica Railway service** rooted at `backend`, startup `/app/server`, without rewriting the API. Deployment remains approval-gated.

## 3. Pipeline — FastAPI

### Root cause / configuration findings

No specific hosted pipeline build failure or project is accessible. Source inspection confirms `pipeline/config.py` honors `DATABASE_URL`, while `heritage_config.py` honors a separate `HERITAGE_DATABASE_URL`; both preserve supplied TLS options. The local pipeline database path is correct, but its URL is local rather than Neon and no explicit `HERITAGE_DATABASE_URL` is configured. Local backend/pipeline internal tokens match. These local facts do not confirm staging secrets/scopes.

The current API is a private service: production middleware rejects requests without the strong shared `X-Internal-Token`. Browser traffic should continue through Rust. `pipeline/api/db.py` sets UTC through connection startup options; validate that configuration with the chosen hosted connection type. Direct connections avoid relying on transaction-pooled session behavior for existing session-sensitive paths.

### Changes and tests

No pipeline source, credential or database change was made. Removed only the obsolete browser-facing pipeline variable from the frontend example.

- Isolated production database configuration tests: **2 passed**, covering distinct URLs/TLS and special-character password encoding.
- In-process private-gateway tests: **3 passed**, covering missing/weak token rejection, matching internal token and development behavior.
- `compileall -q api config.py heritage_config.py`: **Passed**.

Tests use fake URLs and in-process fixtures; they do not connect to Neon. No full pipeline container build, model load, hosted request or database-backed smoke test is claimed.

### Remaining blockers and recommended fix

Provisioning/deployment is outside this diagnosis. Configure the chosen private persistent pipeline host with `APP_ENV=production`, a matching `PIPELINE_INTERNAL_TOKEN`, TLS `DATABASE_URL` for staging **`football_betting`**, and TLS read-only `HERITAGE_DATABASE_URL` for staging **`football_heritage`**. Keep the Rust upstream reachable privately. Audit legacy `DB_*`/`PGSSLMODE` consumers before running collectors.

The existing `pipeline/Dockerfile` requires **repository-root build context** (`docker build -f pipeline/Dockerfile .`), unlike the backend Dockerfile. Its Docker ignore rules exclude data and model artifacts, so those must be supplied through reviewed durable storage/mounts. Scraping/training/scheduling and filesystem artifacts require a worker/storage plan; an HTTP function deployment alone does not provide it. Do not expose the internal token as `VITE_*` or turn off middleware to make public calls succeed.

## 4. Neon staging databases

The two restored/validated databases are user-reported existing assets. This pass did not reconnect, revalidate their contents, run introspection SQL, create branches, alter roles or execute migrations. The confirmed code contract is two distinct databases/roles as mapped above. Actual staging URLs, role privileges, TLS reachability and restored-data encryption-key compatibility remain hosting verification items; no secret was requested in chat.

## Verification evidence and limitations

Logs and the redacted inventory command are in [vercel-staging-20261024/](vercel-staging-20261024/). Fallow summary reports existing repository-wide dead-code/duplication/health findings. The final repository-root audit exits 0: no new dead-code or duplication findings; its complexity warning is inherited `makeRequest`, not introduced by this change. Root `node_modules` is absent, limiting dependency classification. No broad cleanup was attempted.

Actual end-to-end hosting verification is blocked by unauthenticated CLI/team authorization, absent local project links, a real staging HTTPS API endpoint and a successful Linux image. Production checks were retained; no hosted setting was guessed or changed to bypass them.

Sources checked:

- [Vercel Vite deployment documentation](https://vercel.com/docs/frameworks/frontend/vite)
- [Current Rust standalone adapter implementation](https://github.com/vercel/vercel/blob/main/packages/rust/src/standalone-server.ts)
- [Neon transaction-pooling and session-state limitations](https://neon.com/docs/connect/connection-pooling)
