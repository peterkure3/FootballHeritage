# Durable-session phase report

Source implementation completed; hosted rollout remains pending. The original
Neon staging parent, Vercel deployments and production credentials are unchanged.

## Changed files and behavior

* Added `backend/migrations/20261026000002_persistent_auth_sessions.sql`,
  `backend/src/sessions.rs`, `backend/src/session_tests.rs`.
* Updated `auth.rs`, `handlers/auth.rs`, `handlers/chat.rs`, `features.rs`, JWT and
  admin middleware, and `main.rs`. Runtime uses the shared SQLx pool for durable
  validation/idle activity/revocation; no warm-memory fallback grants access.
* Account, zero wallet, limits and session registration are atomic. Login reset/
  success metadata and session are atomic. Failed-count/lock threshold is a
  single database UPDATE. Current role checks remain server-side.
* JWT/user response shape, password hashing, encryption, zero balance, timeout
  configuration and exact-session/idempotent logout behavior are preserved.
  Storage failures remain unavailable, not falsely expired credentials.
* Added `scripts/run_session_tests.py`, `verify_migration_chain.py`,
  `verify_auth_http.py`, an explicit `HTTP_WORKERS` override and CI hooks.
* Fixed supervisor reconnect after a batch closes its destination; added
  `pipeline/tests/test_sync_supervisor.py`.

## Executed proof

* Rust suite: 37 passed, five ignored (three legacy DB cases, separately executed
  durable-session case, and an explicitly launched HTTP server fixture).
* Durable-session DB case: passed using independent services/pools, restart,
  exact revocation, another session, user association, idle/absolute expiry,
  suspended/locked users and storage failure during role lookup.
* Real HTTP on independent Rust processes: registration 201, login 200, profile
  from another instance 200, profile after process restart 200, revoked token 401,
  another session 200, repeated logout 200. Python HTTP was set to a closed port.
* Injected session-write failure: no account/wallet/limits/session count changed;
  same registration retried as 201 with exactly one of each record.
* Concurrent incorrect passwords across two API processes: count exactly five,
  lock persisted, correct password rejected while locked (423).
* Full fresh SQLx chain and replay: all 20 migrations passed in a disposable local
  database. Session DDL also committed only on the existing isolated Neon child;
  the staging parent still has neither new session nor publication schema.
* Python full suite: 287 passed, 30 skipped, 63 subtests passed, 48 existing
  utcnow warnings. Supervisor reconnect regression passed separately.
* Formatting/check/build and scoped Python lint passed. Strict Clippy still has
  35 existing diagnostics (36 at baseline); the unsafe unused signature-only
  helper was removed after its caller migrated to durable checks.

The HTTP test uses the same server entrypoint in a distinct test executable;
the operator's in-use Windows executable was not stopped/replaced. Test processes
and temporary databases were removed. A failed-test UUID schema was verified by
its exact test markers and removed; subsequent DB tests clean up even on panic.
CI changes are prepared, not yet executed on GitHub. No production benchmark is
inferred from functional checks. See `docs/auth-session-design.md`.

## Remaining work and next phase

Apply reviewed migrations and app-role grants before any new hosted runtime.
Validate hosted cold starts/TLS/pooling and current applied migration checksums.
Session cleanup/retention remains to be defined. Refresh/email-verification
endpoints remain pre-existing stubs; no complete flow is claimed for them.

Next: native AI Picks/RAG over published outputs, with a frozen cross-language
selection contract. Then complete remaining gateway domains, provider identities,
multi-sport publishing, Windows operations, real throughput/latency measurements
and preview verification. Production target remains deferred by user decision.
