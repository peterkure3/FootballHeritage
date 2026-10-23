# Isolated local staging

This is a local acceptance environment, not a production approval or hosted deployment. The active chatbot is the Rust RAG agent in `backend/src/rag.rs`, exposed through `/api/v1/ai-picks/chat`. Node `chatbot/` is legacy and optional. No real-money or external provider operations are enabled.

**Do not deploy the legacy Node profile:** its initial dependency audit reported five critical vulnerabilities. Its new token/TLS checks pass, but those checks do not remediate vulnerable dependencies. It is excluded from the default stack and unnecessary for Rust RAG.

## Source and topology

The review branch is `release/staging-20261023`. Its worktree is `D:\Github\FootballHeritage\.release\staging`. The original working tree remains dirty and must not be used as an implicit release artifact. `docs/STAGING_SOURCE_INTEGRITY.json` records the selected pre-existing source dependencies captured in `bd4ef43`; unrelated research, raw data and generated artifacts were excluded. The later required `_config/bookmakers.json` inventory is also included in this branch.

| Component | Container configuration | Native verification fallback |
| --- | --- | --- |
| Existing React web and nested `/admin` dashboard | Caddy serves the Vite production build, loopback HTTPS `18443` | Local HTTPS/SPA harness on the same port |
| Rust API and RAG | Non-root container; `HOST=0.0.0.0`, `PORT=8810`; host loopback `18888` | Windows executable bound to `127.0.0.1:18888` |
| Python API | Private internal Docker network, no published port | `127.0.0.1:15555`, internal token required |
| Database | PostgreSQL 17, isolated volume, loopback `15439` | New PostgreSQL 16 cluster under `.staging/postgres-native` |
| Ingestion | Explicit worker profile; no training/ingestion on startup | Not started |
| Legacy Node and Redis | Opt-in `legacy-chatbot` profile, private network only | Not required or started |

Serving uses `fh_api`, predictions use `fh_pipeline`, RAG uses `fh_readonly`, and a separate `staging_owner` credential runs migrations. These credentials belong only to newly initialized staging databases. Never substitute an existing database URL. Python currently needs broader access to Heritage data for existing queries; a dedicated read-only Heritage role remains a hosting hardening task.

## Native fallback: verified local path

Run PowerShell from the release worktree. Required local tools: Rust/MSVC, Node/npm, Python 3.12, PostgreSQL 16 under `C:\Program Files\PostgreSQL\16\bin`, and Git's OpenSSL. The helpers use fixed staging database names and loopback ports. They do not read production credentials.

```powershell
Set-Location 'D:\Github\FootballHeritage\.release\staging'
py -3 deploy/staging/configure.py
py -3.12 -m venv .staging/python
./.staging/python/Scripts/python.exe -m pip install -r pipeline/requirements-model-tests.txt uvicorn
py -3 deploy/staging/native_postgres.py
py -3 deploy/staging/rust_checks.py
py -3 deploy/staging/rust_checks.py build
py -3 deploy/staging/native_api.py
./.staging/python/Scripts/python.exe deploy/staging/bootstrap.py
py -3 deploy/staging/native_pipeline.py
Set-Location frontend
npm ci
$env:VITE_API_URL='https://staging.footballheritage.test:18443/api/v1'
npm run build:production
Set-Location ..
py -3 deploy/staging/native_web.py
py -3 deploy/staging/smoke.py
Set-Location frontend
$env:STAGING_ACCEPTANCE='1'
npx playwright test --config playwright.staging.config.js
Set-Location ..
py -3 deploy/staging/restart_check.py
```

`configure.py` retains an existing secret file without changing any values. Never print or commit `.staging/secrets.env`, keys, logs or session data. If the database already exists, do not repeat initialization: use `py -3 deploy/staging/native_postgres.py start`. Existing running services cause port conflicts; do not attach tests to an unrelated service.

The browser test resolves `staging.footballheritage.test` to loopback inside Chromium and accepts the temporary local test certificate. No hosts-file or trust-store changes are made. For manual inspection, `https://localhost:18443` serves the app, but its canonical API origin still requires local name resolution for `staging.footballheritage.test`. No TLS-verification exception is intended for a hosted environment.

Bootstrap registers synthetic accounts `admin`, `recovery`, `user`, and `restricted` at `staging.example.test`; their new random password is stored only as `STAGING_ADMIN_PASSWORD` in the private environment file. Two staging superadmins support recovery tests. The sole prediction fixture is explicitly synthetic, uses model version `staging-fixture`, and does not represent model-quality or live-provider verification.

The native API is a development-profile executable. It verifies source/runtime contracts but cannot establish Linux release-image correctness, OCI signal handling, or production performance. The HTTPS harness is test infrastructure, not a replacement for Vercel or the Caddy container.

## Container staging: blocked until the build worker is repaired

The Docker engine recovered after a normal Desktop restart, but its build worker still returns no compiler version/output and produces no Rust binary. The final image build fails at the artifact copy. A minimal pinned-toolchain build reproduces this independently of application source; `docker run --rm rust:1.90-bookworm cargo --version` works. Do not mark image build, configured container `PORT`, `/ready`, or graceful shutdown verified from native fallback results.

After repairing the worker or using a clean Linux build host, run:

```powershell
Set-Location 'D:\Github\FootballHeritage\.release\staging'
py -3 deploy/staging/configure.py
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml config --quiet
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml build api pipeline web
```

Only after successful image builds, stop the native fallback to release the same loopback ports:

```powershell
./deploy/staging/stop_native.ps1 -Service web
./deploy/staging/stop_native.ps1 -Service pipeline
./deploy/staging/stop_native.ps1 -Service api
py -3 deploy/staging/native_postgres.py stop
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml up -d postgres
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml run --rm migrate
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml up -d api pipeline web
./.staging/python/Scripts/python.exe deploy/staging/bootstrap.py
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml ps
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml exec -T api curl --fail http://127.0.0.1:8810/health
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml exec -T api curl --fail http://127.0.0.1:8810/ready
```

The native and container databases are separate; each receives synthetic bootstrap fixtures independently. Never reuse production volumes. Repeat browser acceptance. `smoke.py` currently targets the native Python loopback port for its private-service checks; for containers, run equivalent token checks from inside the private network rather than publishing Python. No worker is started by default. The worker profile currently performs only `--help`, not a scheduled ingestion acceptance run.

Container restart acceptance must record startup logs, readiness transitions, binding to `8810`, expected session loss, successful login after restart, and a successful migration rerun. Run `docker compose ... stop -t 40 api`, inspect its exit status/logs, then `docker compose ... up -d api`; verify shutdown completes within the grace period without a forced kill. This remains unverified.

## Hosted staging and Vercel preview

There is one Vite project rooted at `frontend/`; the admin is nested in this application. Build `npm run build:production`, output `dist`, using `frontend/vercel.json` for SPA routing, hashed asset caching and security headers. Do not create an unrelated admin application.

Hosted staging requires a persistent container host, separate staging databases/secrets, private Python ingress, persistent model/data volumes and an explicitly scheduled ingestion worker. Use the active Rust RAG chatbot; Node is optional legacy infrastructure. Keep one Rust replica while sessions/rate limits remain process-local. Do not expose direct Python inference publicly. Use exact real HTTPS origins in `ALLOWED_ORIGINS` and `VITE_API_URL=https://STAGING_API_HOST/api/v1`.

No connected Vercel staging project or persistent host was selected. No hosted deployment was performed. Once a staging project and API host exist, these are preview-only CLI commands (authenticated, reviewed CLI installation required):

```powershell
Set-Location frontend
vercel link
vercel env add VITE_API_URL preview
vercel pull --yes --environment=preview
vercel build
vercel deploy --prebuilt
```

Select the staging project during `link`; enter its actual HTTPS API URL when prompted. Never use `--prod` or promote/rollback a production domain under this staging authorization. Repeat all acceptance on the returned preview URL with that exact origin in API CORS, including denied-origin preflight and SPA deep links. Use the Vercel protected-deployment workflow when authentication protection is enabled.

## Rollback and stop

Before release, record Git commit, image digests, preview URL, configuration version and feature-audit cursor. Keep the prior compatible feature-enforcing API image and frontend deployment. The additive schema can remain; never drop feature tables, audit rows or wallet data as rollback. The unique-wallet index migration must fail safely if legacy duplicate owners exist: review duplicates before any production migration; never auto-delete balances.

For a preview regression, redeploy the recorded prior preview artifact with `vercel deploy --prebuilt` from its reviewed checkout/build. Do not use production rollback aliases for a staging incident. On the container host, run the following from this worktree after selecting its recorded compatible staging image:

```powershell
$stagingRollbackImage = Read-Host 'Recorded compatible staging API image digest or tag'
docker --context default image tag $stagingRollbackImage footballheritage-staging-api:phase2
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml up -d --no-build api
docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml exec -T api curl --fail http://127.0.0.1:8810/ready
```

Verify health/readiness and require users to log in again. Do not roll back to an API that bypasses restrictions while relying on feature controls.

To stop only native staging, run `stop_native.ps1` for `web`, `pipeline`, and `api`, then `native_postgres.py stop`. Native process stops are explicitly forced; they do not prove graceful container shutdown. To stop container staging, run `docker --context default compose --env-file .staging/secrets.env -f deploy/staging/compose.yml down` **without `-v`**. Preserve databases, secrets and audit history for diagnosis. Repair flags through audited admin mutations; pause workers separately. No destructive rollback or credential rotation is authorized.
