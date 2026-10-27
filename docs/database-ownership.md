# Database ownership and privileges

| Data | Owner | Pipeline publication |
|---|---|---|
| Raw feeds, historical training rows, features, experiments, model files | Local PostgreSQL / existing local files | Never bulk-copy |
| Approved fixture/prediction/quote aggregates | Local computation | Versioned publication to `published.records` |
| Approved model metadata / simulation results | Local computation | Explicit allowlisted bundle only |
| Accounts, passwords, sessions, roles, preferences | Neon application | Never overwrite |
| User picks, AI pick run history, conversations, messages | Neon application | Never overwrite |
| Wallets, transactions, subscriptions, bets, saved parlays | Neon application | Never overwrite |
| Admin feature policy, audit trails, transactional state | Neon application | Never overwrite |

The transport has hardcoded destination SQL for `published.records`,
`published.receipts`, and one timestamp column in `published.sources`. It never
accepts arbitrary table or column names. Existing `sync_to_backend.py` remains a
separate legacy writer; do not point it at production as a substitute for the new
transport or run both writers against the same domain during cutover.

Provision roles using migration credentials, separately from runtime secrets.
Do not use `neondb_owner` as the API or sync identity. Proposed grant contract,
to be reviewed/applied on a Neon development branch before production:

```sql
GRANT USAGE ON SCHEMA published TO fh_api, fh_sync_worker;
GRANT SELECT ON published.records, published.sources TO fh_api;
GRANT SELECT ON published.sources, published.records, published.receipts TO fh_sync_worker;
GRANT INSERT, UPDATE ON published.records TO fh_sync_worker;
GRANT INSERT ON published.receipts TO fh_sync_worker;
GRANT UPDATE(last_success_at) ON published.sources TO fh_sync_worker;
```

These statements do not create credentials. Existing inherited grants must also
be inspected: PostgreSQL privileges are additive. Verify a sync login cannot
SELECT/INSERT/UPDATE/DELETE user or financial relations. Do not grant it ownership,
schema CREATE, source registration, receipt modification, TRUNCATE, or DELETE.
Source registration is a migration/operator action; register the UUID reported by
`SELECT stream_id FROM fh_sync.identity` on the approved branch only.

Locally, keep ingestion and projection identities private. Source triggers run in
the ingestion transaction, so restricted source writers require the narrow
permissions needed to enqueue `fh_sync.dirty_fixtures`. The projection role needs
source SELECT, dirty-queue SELECT/DELETE, publication records SELECT/INSERT/UPDATE,
identity SELECT, outbox INSERT and sequence usage. The transport role needs local
identity/outbox/status SELECT, outbox/status UPDATE and advisory-lock access; it
does not need source-table or user-table access. Validate trigger permissions
under the actual restricted roles before enabling jobs.

New publication timestamps are TIMESTAMPTZ and emitted in UTC. Existing naive
football timestamps are explicitly interpreted as UTC, matching the current
pipeline contract; verify this against the live schema before installation.
Do not change financial types or convert historical timestamps destructively.

Durable application sessions are added by
`backend/migrations/20261026000002_persistent_auth_sessions.sql`. The application
runtime role needs `SELECT, INSERT, UPDATE ON auth_sessions`. The sync role gets
no grants on this table. Session expiry/revocation is checked in PostgreSQL across
API instances; no warm-memory cache can override it. See `auth-session-design.md`.

## Durable gateway roles

Keep `fh_gateway_worker` separate from `fh_sync_worker`. With approved migration
credentials, review inherited permissions before granting:

```sql
GRANT USAGE ON SCHEMA published TO fh_api, fh_gateway_worker;
GRANT SELECT ON published.gateway_jobs TO fh_api, fh_gateway_worker;
GRANT SELECT ON published.sources TO fh_gateway_worker;
GRANT INSERT ON published.gateway_jobs TO fh_api, fh_gateway_worker;
GRANT UPDATE(state,attempts,response,response_status,generated_at,fresh_until,created_at)
  ON published.gateway_jobs TO fh_api;
GRANT UPDATE(state,attempts,lease_token,lease_until,response,response_status,generated_at,fresh_until,created_at)
  ON published.gateway_jobs TO fh_gateway_worker;
GRANT USAGE ON SCHEMA public TO fh_gateway_worker;
GRANT SELECT(id,role,is_active,locked_until) ON users TO fh_gateway_worker;
```

The four-column account lookup rechecks queued administrator permission. It grants
no emails, credentials, sessions, financial access or account mutation. The fixture
sync role still has no account access. Gateway identities need no source mutation,
schema ownership, DELETE or TRUNCATE. Their protocol-column grants are distinct
from application-table writes.

For multiple installations, enable RLS on `published.gateway_jobs` and provision
policies for **both** API and gateway identities with `USING` and `WITH CHECK`
restricted to approved stream UUIDs. Provision policies and grants together;
enabling RLS without the API policy denies requests. Runtime roles must not own
the table or have BYPASSRLS. The local harness exercises the real worker SQL under
a NOLOGIN role with stream RLS and verifies forbidden account/session/wallet/
source/delete/truncate access. This does not verify an unprovisioned Neon login
or remote TLS. These documents perform no role or credential changes.
