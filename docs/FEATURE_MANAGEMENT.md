# Feature management

The existing administrator dashboard exposes `/admin/features`. Search by key or description, filter by category, select a user by email/name and use the controls in each feature card. Every mutation asks for confirmation and records the administrator UUID, target, old value, new value and UTC time. Audit pagination uses the last returned ID. A user override set to **Inherit** removes the override.

## Registry and defaults

Migration `backend/migrations/20261022000001_feature_management.sql` adds `feature_flags`, `user_feature_overrides`, `role_feature_rules` and `feature_audit_logs`. All existing product features start globally enabled, with explicit allowed rules for existing roles and guests. Maintenance starts inactive. Unknown identifiers deny access; they cannot be created through PATCH. Add a reviewed registry migration and backend/frontend route mapping when adding functionality.

Registered keys: `registration`, `ai_picks`, `ai_chat`, `predictions`, `intelligence`, `best_picks`, `player_props`, `parlays`, `betting`, `wallet`, `wallet_funding`, `sports`, `fpl`, `college`, plus platform control `maintenance`. Sports and league browsing share `sports`; this version does not provide per-competition data filtering. No subscription entitlement schema or verified payment integration existed, so no speculative subscription/payment-provider flags were introduced.

## Evaluation order

1. Validate any supplied bearer token and reload the user's current database role, active status and lock status. Invalid/expired/revoked sessions deny access. Requests without a bearer token use `guest` policy only for routes that already support public access.
2. Unknown feature keys deny. Policy database failures deny with 503; no stale backend cache grants access.
3. Global `enabled=false` or `emergency_disabled=true` denies everyone. Superadmins have no bypass.
4. Active maintenance (`maintenance.enabled` or its emergency restriction) denies product features unless their `maintenance_allowed` is true. Missing maintenance configuration fails closed.
5. Explicit user restriction (`enabled=false`) denies.
6. Explicit role restriction (`enabled=false`) denies. A user allow never overrides this restriction.
7. Otherwise use explicit user allow, then role allow, then the feature's explicit `default_enabled`.
8. Independently, production wallet funding is always unavailable. `ALLOW_DEMO_WALLET_FUNDING` cannot enable it. Production POSTs to `/betting/bets` and `/parlay/place` are also blocked before handlers execute until the financial lifecycle is independently verified. Read-only history and calculations retain their existing feature policy.

Feature controls add restrictions to existing authorization. They do not grant an anonymous caller access to an authenticated wallet/betting endpoint. Public content remains accessible according to the guest policy; a per-account restriction cannot identify an anonymous visitor. Use guest restrictions when content must require login or be unavailable publicly. Security/account operations, logout, refresh, profile/password management and self-exclusion remain outside product maintenance restrictions. Admin feature controls stay reachable so administrators can recover from maintenance; they still require current database admin authorization.

An emergency change affects new checks immediately. A request already admitted before a toggle may finish. These switches do not cancel in-flight transactions, workers or external jobs. Emergency incident procedures must pause workers/ingress separately if needed.

## API

All paths below have prefix `/api/v1`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/me/features` | Effective boolean access only; supports existing guest browsing |
| GET | `/admin/features` | Registry and role rules |
| PATCH | `/admin/features/{key}` | Set `enabled`, `emergency_disabled`, or `maintenance_allowed` |
| GET | `/admin/users/{id}/features` | User effective access and explicit overrides |
| PATCH | `/admin/users/{id}/features/{key}` | `{"enabled":false}`, true, or null to inherit |
| PATCH | `/admin/features/{key}/roles/{role}` | Set `{"enabled":false}` or true for guest/user/admin/superadmin |
| GET | `/admin/features/audit?before_id=123` | Up to 100 immutable audit entries |

Global mutation example: `PATCH /api/v1/admin/features/ai_chat` with `{"emergency_disabled":true}` and an administrator bearer token. Disabled product requests return HTTP 403 and `{"error":{"code":"FEATURE_DISABLED","message":"This feature is currently unavailable."}}`. Effective responses contain no internal descriptions, role rules or audit data. All feature reads use `Cache-Control: no-store`.

Each mutation locks the feature row, rechecks/locks the administrator and writes the audit entry in the same transaction. An audit failure rolls back the change. The audit trigger rejects updates/deletes, and actor UUIDs are retained even if accounts later disappear. Application credentials must not be database owners/superusers: database owners can bypass database-level protections. The users trigger rejects removing/deactivating/demoting the last active superadmin; remaining alternatives must also be unlocked.

## Enforcement boundaries

`backend/src/features.rs` supplies the evaluator and Actix application middleware. It guards wallet deposits/withdrawals, betting, AI, props, parlays and analytics before their handlers run. `backend/src/pipeline_gateway.rs` guards browser requests to `/api/v1/pipeline/*` and forwards only to the configured Python origin. Non-read-only operations and refresh queries require current administrative access; production pipeline execution via requests is blocked. Python requires `PIPELINE_INTERNAL_TOKEN` whenever configured and always in production. Keep both Python and the legacy Node chatbot on private ingress; do not expose an alternate public hostname that bypasses Rust.

Frontend policy lives in `frontend/src/features/`. Feature route boundaries and navigation use effective booleans; failure hides restricted links and prevents route contents mounting. Permissions refresh every 15 seconds and on focus; mutations invalidate relevant queries immediately in the administrator's client. Other sessions can display old navigation until their next refresh, while backend checks enforce current restrictions immediately. Session expiry uses the existing login redirect. Already displayed content is not erased from browser history or caches by a feature restriction.

## Verification

From `backend/`: set `SQLX_OFFLINE=true` and `FEATURE_TEST_DATABASE_URL` to a disposable PostgreSQL database, then run `cargo test --locked --bin football-heritage-backend`. Database tests create a unique schema and leave it in the disposable database; never point this variable at production. From `frontend/`: `node --test tests/production-policy.test.mjs` and `npx playwright test tests/feature-management.spec.js --project=chromium`. From `pipeline/`: `py -3 -m unittest discover -s tests -p test_gateway_access.py -v` after installing test requirements.
