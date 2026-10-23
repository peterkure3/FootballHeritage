# Production checklist

No live production deployment or production database write is approved by this checklist.

Phase 2 verified an isolated **native local** environment on `release/staging-20261023`. Its 42 API checks and real browser flow passed. Docker image/runtime verification and hosted staging remain blocked; use [LOCAL_STAGING.md](LOCAL_STAGING.md) and the dated Phase 2 report for scope and evidence. The active chatbot is Rust RAG; Node is optional legacy infrastructure.

## Release gates

- [ ] Review and commit the pre-existing working tree changes separately; validate the complete release from a clean checkout.
- [ ] Assign the real web/admin/API domains. Require exact HTTPS origins and verify denied-origin preflight.
- [ ] Rotate previously exposed/bootstrap credentials and complete tracked-file/history secret scanning. Keep secrets out of logs and browser builds.
- [ ] Review historical bootstrap-account and sample-event seeding on a fresh database; exclude demo events and rotate/bootstrap accounts through an approved release procedure.
- [ ] Keep demo wallet funding blocked. Implement and independently review payment-provider verification, idempotency, reconciliation, ledger handling and concurrent money-operation tests before real-money launch.
- [ ] Complete bet settlement/void lifecycle review; existing commented-out admin settlement routes are not production-ready.
- [ ] Verify PostgreSQL backup/restore and pool budgets (Rust, RAG, Python, workers), TLS for every driver, least-privilege runtime credentials and approved migration execution.
- [ ] Verify additive feature migration on a staging copy and preserve existing intended access. Test current-role admin checks and last-superadmin recovery.
- [ ] Verify direct API requests fail when global, emergency, role or user restrictions deny access; unknown keys deny and mutations create immutable audit history.
- [ ] Keep Python/Node private. Verify missing/incorrect internal tokens fail even if requests supply an allowed Origin.
- [ ] Provision persistent models, raw snapshots, logs and workers. Confirm Pegasus/Windows/systemd schedules and failure alerts after deployment.
- [ ] Use one API instance until shared sessions and distributed rate limiting are implemented; account for forced reauthentication on restarts.
- [ ] Verify `/health`, `/ready`, restricted `/metrics`, safe errors, rate limits and observability under actual hosted networking.
- [ ] Run Rust tests with disposable PostgreSQL, frontend lint/typecheck/build/browser tests, Python gateway and existing pipeline suites; record baseline failures honestly.
- [ ] Run dependency/security scans and resolve critical/high findings. Repository-wide Fallow is not currently green.
- [ ] Keep the optional legacy Node service undeployed until its npm audit findings are remediated; initial install reported five critical vulnerabilities. The active Rust RAG chatbot does not require it.
- [ ] Verify Vercel SPA deep links, immutable hashed assets, CSP, production API URL validation and no source/server credentials in bundle output.
- [ ] Complete the Rust image build, container binding/readiness/graceful shutdown and hosted runtime smoke tests; local BuildKit compiler execution still fails after daemon recovery.
- [ ] Configure required CI/deployment checks, protected production branch and manual release approval. Record rollback image/deployment IDs and an operator.
- [ ] Obtain explicit production approval, deploy in order from the runbook and verify smoke tests. Roll back according to the documented compatibility limits.

See [audit](PRODUCTION_AUDIT.md), [feature policy](FEATURE_MANAGEMENT.md), [deployment runbook](VERCEL_DEPLOYMENT.md) and the dated verification report in `stages/04-test/output/` for evidence and remaining failures.
