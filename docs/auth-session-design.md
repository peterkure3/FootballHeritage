# Durable application sessions

Status: additive implementation with independent-process HTTP verification; no hosted release or runtime
credential change. Sessions are Neon-owned application state, excluded from every
pipeline publication allowlist and grant.

The prior validator required an instance-local DashMap entry. The application
entrypoint now constructs `AuthService` with its existing SQLx pool. Registration
and login persist a session before returning the unchanged JWT/user response.
JWT issuer, audience, signature, subject, session ID and expiration remain checked.
An async database validator atomically refreshes activity only when the exact
session belongs to that user, is unrevoked, has not expired or exceeded the idle
timeout, and the user is active/unlocked. A different process needs no shared RAM.

`20261026000002_persistent_auth_sessions.sql` adds `auth_sessions` with a user FK,
TIMESTAMPTZ creation/activity/expiration/revocation and an active-user index.
The app role requires SELECT/INSERT/UPDATE on this table; the publication worker
receives no access. No new database credentials are created by the migration.
Migration-owner credentials remain separate. Session retention/deletion is not
automated yet; review cleanup/index usage before sustained production traffic.

Registration inserts the account, zero-balance wallet, responsible-gambling limits
and session in one transaction. JWT creation precedes commit; success logging and
registration metrics follow commit. Failure does not leave a partially initialized
account. Password hashing, wallet encryption, zero balance, role defaults and
financial calculations are preserved.

Successful login metadata reset/increment and session creation also commit
together, with an active/unlocked-user recheck under the database row lock.
Failed-password count and lock-threshold evaluation are one atomic UPDATE;
independent API instances cannot evaluate the threshold against a stale snapshot.
The real HTTP fixture verified five concurrent failures across two processes,
an exact count of five and rejection of a correct password while locked (423).

Protected JWT middleware, feature identity, admin/superadmin middleware, logout
and legacy chat all use the async session check. Revocation applies to the exact
verified session across instances; other sessions stay valid. Missing/invalid/
revoked/idle-expired credentials remain unauthorized. Authentication storage
outages return unavailable responses instead of a false expired-session response.
Logout does not claim success when session storage is unavailable.

Memory-only `AuthService::new` remains for existing isolated tests. Production and
normal API startup use `.with_database(pool)`. The synchronous validator fails
closed when attached to persistent storage; it cannot bypass a database failure
through a warm-memory cache. The unused standalone signature-only JWT helper was
removed after mapping its only runtime caller (legacy chat) to durable validation.

Tests must prove independent services/pools, process restart, exact logout,
unrelated sessions, user association, idle/absolute expiry, suspension/lock state,
database failure and registration rollback. Run `scripts/run_session_tests.py`
for disposable schema checks and `scripts/verify_auth_http.py` for the real server
entrypoint in independent test processes. These refuse remote database targets
and never stop an operator's running backend. `HTTP_WORKERS` permits explicit
worker count (positive integer); test processes use one worker.

Executed HTTP proof: registration 201, login 200, profile 200 from another process
and after cold restart, revoked token 401, separate session 200 and repeated logout
200. A deliberately rejected session insert left all four account setup table
counts unchanged; the same registration then succeeded with exactly one new
account/wallet/limits/session. The fixture ran with Python HTTP configured at a
closed loopback port. Full fresh SQLx initialization/replay passed all 20 migrations.

The pre-existing refresh and email-verification endpoints are stubs that return
messages without implementing those flows. This migration does not claim to
complete them or add an identity provider. Record and resolve their intended
contracts before claiming full authentication readiness.
