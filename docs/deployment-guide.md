# Deployment preparation

Status: no new deployment. See the existing `VERCEL_DEPLOYMENT.md` and
`PRODUCTION_CHECKLIST.md` for historical configuration; the new offline pipeline
architecture supersedes their Python gateway topology only after complete parity.

Confirmed 2026-10-26: existing Vercel roots remain `frontend` and `backend/src`,
with READY deployments of `d8aaa59`; Preview API env scopes are incomplete.
The additive publication migration was tested only on isolated Neon child
`codex-publication-contract-20261026`. Its staging parent remains unchanged.
The user retained the current Neon project as staging and deferred production
project selection. Do not repurpose or promote staging implicitly.

1. Identify the exact existing Vercel frontend/backend projects, branch roots,
   Production/Preview env scopes and deployed commit. Historical root settings
   differ from repository root assumptions; inspect before editing.
2. Confirm the installed Rust adapter supports the existing Actix standalone
   server, or verify an Actix-preserving adapter/container on a preview. Official
   [Rust runtime docs](https://vercel.com/docs/functions/runtimes/rust) currently
   describe `vercel_runtime` entrypoints; source notes about another adapter need
   deployed-version verification. Do not rewrite Actix from a documentation guess.
3. Use portable CPU flags, locked dependencies and checked-in SQLx offline
   metadata. Build the intended API binary only. Honor the supplied PORT and host
   binding required by the actual adapter. A successful build is not a smoke test.
4. Apply reviewed additive migrations on a Neon development branch with direct
   migration credentials. Verify existing SQLx migration checksums. Never run
   migration-owner credentials inside public functions; set RUN_MIGRATIONS=false.
5. Set backend DATABASE_URL to a TLS-verified Neon pooled endpoint with a
   restricted application role. Bound per-instance and aggregate connection use;
   verify statement/prepared-query behavior against the actual pooler version.
   Keep the migration URL direct. Register the publication source using the
   migration role; the sync worker cannot register itself.
6. Configure exact HTTPS ALLOWED_ORIGINS, secure JWT/encryption settings and
   separate preview secrets. No Neon credentials belong in VITE_* variables.
   VITE_API_URL targets Rust only. API rewrites must precede SPA catch-all routes
   if sharing an origin; current separate-host frontend fallback is appropriate
   only with the separate API base.
7. Complete Rust publication adapters before disabling gateway configuration.
   Verify every migrated endpoint with Python stopped: existing data, pending
   prediction, stale evidence, authentication, authorization, AI pick history/chat,
   empty data, pagination, CORS, unknown routes and health/readiness. Check actual
   HTTP responses and invocation logs for 500/503/FUNCTION_INVOCATION_FAILED.
8. Verify cold starts, DB suspension/reconnect, timeouts, error sanitization and
   instance-local rate limiting limits. Public metrics must not expose secrets.
9. Record the preview URL, immutable deployment IDs, smoke results and database
   branch/reconciliation state. Request approval for the exact production release
   and any required credential changes only when this evidence is reviewable.

The Python pipeline, local PostgreSQL, training and scheduler stay on Windows.
No tunnel, public FastAPI endpoint or inbound Windows database port is required.
