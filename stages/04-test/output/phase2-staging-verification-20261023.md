# Phase 2 release verification — 2026-10-23

**Outcome: native isolated staging verified; release-image and hosted-staging gates remain open. Production is not approved.** No production database was accessed, credentials rotated, production deployed, or real-money operations enabled.

## Repository integrity

The original `feature/footballheritage-frontend` checkout at `634da15` contained extensive pre-existing tracked/untracked changes. Its initial inventory is preserved locally in `staging-integrity-baseline-20261023.json`. Existing feature-management commits were `59c38df`, `b1a54db`, `a8b615b`, `ed6588b`, `39c52fa`, and `634da15`. They did not include every source dependency referenced by the current application.

A separate `release/staging-20261023` branch/worktree captures 230 selected runtime/config/test changes in `bd4ef43`, excluding 1,028 unrelated status entries. `docs/STAGING_SOURCE_INTEGRITY.json` records per-file provenance/hashes. Clean-checkout tests subsequently exposed one additional required runtime dependency, `_config/bookmakers.json`, now included. Research captures, model data, provider credentials and generated caches were not swept into a commit. The main checkout remains intentionally dirty; it is not the release artifact. This task also added its staging ignore rules and reduced its Rust development artifact size to address the reported disk error.

The release branch's final Git/clean-checkout evidence is recorded in `phase2-clean-checkout-20261023.json`. No branch has been pushed or production CI/deployment triggered. Local CI-equivalent results must not be described as a successful remote GitHub Actions run.

## Verification matrix

| Check | Result and limit |
| --- | --- |
| Rust feature/financial suite | 29 passed, 3 existing DB tests ignored; DB-backed tests actually ran against the new isolated test database |
| Full additive migration chain | Passed on native PostgreSQL 16; dedicated migrator reruns are idempotent |
| Runtime DB permissions | Six checks passed: no public-schema DDL, no audit TRUNCATE, no migration UPDATE, full migration chain, unique wallet owner, rejected audit UPDATE |
| Native Rust health/readiness | `/health` and `/ready` return 200 on configured loopback port 18888 |
| API staging acceptance | 40/40 passed; `staging-smoke-20261023.json` lists each assertion |
| Active Rust RAG chatbot | Real request, persistence, conversation reload and emergency denial passed using read-only synthetic prediction evidence and grounded mode |
| Python gateway | Real missing/wrong-token requests return 403; correct internal token and Rust gateway requests return 200 |
| Python regression suite | 269 completed, 14 gated skips, no failures after adding missing CI dependencies and runtime inventory |
| Frontend install/lint/typecheck | Passed; new test's missing `node:process` import was fixed without suppressing lint |
| Guarded production frontend build | Passed with canonical HTTPS staging API URL |
| Frontend policy unit tests | 3 passed, including exactly one `/api/v1` prefix and fail-closed unknown policy |
| Mocked feature browser regressions | 3 Chromium tests passed; explicitly separate from real API acceptance |
| Real browser acceptance | Passed: HTTPS login, nested admin deep-link/reload, selected-user override and confirmation, audit row, denied user's route/navigation, actual UI logout, old-token 401 |
| Native restart | Readiness, prior-session rejection and fresh login passed after a forced local process restart; this is not graceful OCI shutdown |
| Compose configuration | `config --quiet` passed with generated isolated credentials, no secrets printed |
| Legacy Node install/syntax/guards | Passed installation and syntax plus 2 guard/TLS tests; npm reported 90 vulnerabilities (5 critical, 13 high, 71 moderate, 1 low). This optional legacy service must remain undeployed pending remediation |
| Rust Docker image | **Failed**: no release binary produced; see container evidence below |
| Container PORT 8810, readiness, restart/signals | **Not verified** because no successful release image exists |
| Hosted Vercel/persistent-host acceptance | **Not deployed or verified**; user selected isolated local staging first |
| Fallow | Existing repository gate remains failing: root scan reported 405 findings with degraded root dependency resolution, 44 clone groups and 177 functions above threshold; not waived or disabled |

Local toolchains: Node 24.13.0, Cargo/Rust 1.99 toolchain, Python 3.12.10, PostgreSQL 16.15, Docker 29.8.2. CI/container definitions use different platform/runtime versions (including PostgreSQL 17 and pinned Rust 1.90); local passes do not establish that matrix. Trained model artifacts, live-provider data, external LLM calls, scheduled ingestion, performance and disaster recovery were not certified.

## Fixed blockers and changes

- `backend/src/handlers/auth.rs`, frontend API/store/hooks/admin navbar: logout now revokes the verified session, all UI logout paths call the server, anonymous/expired logout remains idempotent, and a regression test checks that other sessions survive.
- `backend/src/features.rs`, `feature_tests.rs`, `financial_tests.rs`: unconditional production demo-funding denial, production placement-write denial, real direct-API checks, role/current-admin revocation, emergency rules, maintenance recovery and immutable audit assertions. No opt-in environment flag can enable production funding.
- `backend/src/handlers/wallet.rs`, `20261023000001_unique_wallet_owner.sql`: balance GET performs no wallet creation; first deposits lock the owner, later writes lock the wallet, and one wallet per owner is enforced. Concurrent tests verify four initial deposits, four withdrawals and eight competing stake attempts without overdraft.
- `backend/src/handlers/monitoring.rs`: metrics require current database administrative authority.
- `backend/src/bin/migrate.rs`, `main.rs`, environment template: separate migration execution and non-owner runtime credentials, with legacy startup migration behavior retained unless `RUN_MIGRATIONS=false`.
- `frontend/src/features/FeatureControls.jsx`: search matches both raw identifiers and displayed names. Browser navigation waits for the app DOM rather than unrelated resource completion; no assertions were removed.
- `_config/bookmakers.json`, `pipeline/requirements-model-tests.txt`: restore the required registry and declare SQLAlchemy/psycopg2/BeautifulSoup/colorama imports needed by clean CI. SQLAlchemy stays on the existing 2.0 driver family.
- Legacy optional Node: internal token guard, verified database TLS defaults, redirect-safe Rust proxy and tests. No legacy service was required for the active Rust RAG acceptance flow.
- `deploy/staging/*`, Dockerfiles/ignore files, templates and runbooks: isolated staging topology, private upstreams, loopback ports, synthetic bootstrap, acceptance helpers and guarded process stops. `.staging/` secrets/artifacts remain ignored.

## Container failure evidence

The engine first failed pulling PostgreSQL with:

```text
write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db: input/output error
```

A normal Docker Desktop restart restored engine responses. Retrying the application image still failed:

```text
cp: cannot stat '/app/target/release/football-heritage-backend': No such file or directory
```

Neither `cargo --version` nor `rustc --version` produced output inside BuildKit's RUN step, although the step returned success before the missing artifact was detected. A minimal `FROM rust:1.90-bookworm` build invoking the compiler directly reproduces this without repository code. Running the same toolchain in a normal container prints `cargo 1.90.0`. A bounded legacy-builder diagnostic timed out. Do not bypass the artifact failure, fabricate a successful image digest, or treat native binaries as container build evidence.

Private raw logs remain under `.staging/` (`docker-api-build-final.log`, `toolchain-probe.log`, `toolchain-direct.log`); these may be shared only after review. Repair the build worker or rerun on a clean Linux host, then follow `docs/LOCAL_STAGING.md` for actual OCI/PORT/signal acceptance. No Docker storage prune, daemon reset or deletion of existing volumes was performed.

## Financial and security release status

Production deposits, withdrawals and bet placement are blocked. Balance reads cannot create funds. Synthetic non-production tests demonstrate row-lock/ledger concurrency behavior; they do not validate a real payment system.

Settlement/cancellation/void remains a **release blocker**. Legacy disabled admin settlement code refers to incompatible fields/statuses and lacks the verified encrypted-wallet lifecycle. It was not enabled. Required work includes trusted outcome evidence, transaction locking, immutable ledger postings, duplicate-result idempotency, partial failures/retries, PUSH/CANCELLED/void accounting and reconciliation tests. Verified payment-provider integration still needs authenticated webhooks, replay protection/idempotency, amount/currency/ownership checks, refund/chargeback handling, reconciliation and independent review. No real-money integration was enabled.

Historical bootstrap credentials/sample events remain in migration history. Full history/provider-secret scanning and authorized credential rotation are outstanding. Database owners can alter triggers; immutable audit protection was verified for ordinary runtime SQL, not as protection from privileged database administrators. Sessions and rate limits remain process-local, requiring one API instance and reauthentication on restart. Refresh/email-verification handlers remain legacy placeholders; they are not certified security flows. Hosted TLS, ingress, metrics collection, alerts, pool budgets, backup/restore and actual domains remain open gates.

The optional legacy Node dependency tree has critical/high audit findings. It remains outside default staging and must not be deployed until dependency remediation/verification or an explicitly reviewed retirement is complete. New ingress guards are not a substitute for that work. This task did not apply a potentially breaking blanket dependency upgrade to a service superseded by Rust RAG.

`npm audit --omit=dev` confirmed **87 production-dependency findings: 5 critical, 10 high, 71 moderate and 1 low**. Critical package entries were `fast-xml-parser`, `handlebars`, `protobufjs`, `proxy-addr`, and `websocket-driver`. The complete private JSON is `.staging/legacy-node-audit.json`; counts are registry results at verification time, not a complete historical/security certification.

## Disk-space incident

The user reported Actix proc-macro expansion failing with Windows error 112. Only `D:\Github\FootballHeritage\backend\target\debug\incremental` was removed after confirming its resolved path: 7.47 GiB of regenerable artifacts. Existing source and application binaries were preserved. D: free space increased to approximately 17.7 GiB at that check. Development/test profiles now use `debug=0`, `incremental=false`; compiler/lint checks remain enabled. Windows successfully loaded the exact reported `actix_web_codegen-64ff6fbd37e8e71a.dll` in a fresh process. A stale rust-analyzer IDE diagnostic may require restarting its language server. C: remains relatively constrained; no unrelated user data was removed.

## Release handover

Use `docs/LOCAL_STAGING.md` for exact commands, secrets/configuration, deployment order and non-destructive rollback. Stage 04's production gate is **not signed off**, and Stage 05 production deployment must not proceed. Required next evidence is a successful Linux release image and container acceptance, then approved isolated hosted staging with real domains/private services and repeat browser/API checks. The remaining production gates are maintained in `docs/PRODUCTION_CHECKLIST.md`.
