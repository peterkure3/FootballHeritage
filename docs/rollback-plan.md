# Rollback and restoration

Before cutover record the old/new frontend and API deployment IDs, Git revisions,
all required env variable **names** and scopes, SQLx migration checksums, source
stream UUID, queue/receipt counts, reconciliation findings and backup identifiers.
Never record secrets in Git or logs. No production rollback has been exercised yet.

For a publication fault, stop the local transport first; preserve dirty rows,
outbox records, acknowledgments and destination receipts. Continue serving the
last valid published data with explicit freshness. Diagnose by canonical key and
SQLSTATE/error class. Retry reviewed parked events without changing identity or
versions. Never reset every checkpoint or delete receipts to make a queue drain.

For an API/frontend fault, restore the recorded compatible immutable deployment
pair. Leave additive publication schema/tables in place. Existing user/financial
state remains current. An older API that requires the user's local HTTP service
is not a valid production rollback target for the completed architecture.

For bad published sports data, publish a corrected higher version or an explicit
tombstone from the approved source. Do not edit old outbox payloads, lower record
versions or overwrite application tables. For a restored local backup, reconcile
identity/version history before restarting; new stream registration requires a
reviewed plan to prevent duplicate active sources.

Create encrypted local PostgreSQL backups and verify restoration into a separate
database. Verify Neon backup/PITR availability and the plan's actual recovery
window. Test restoration to a separate development branch and reconcile there.
Never restore an old full production backup over newer user transactions as a
sports-data repair. Production restore, destructive migration and credential
rotation require explicit approval. Document actual recovery time/data loss from
the rehearsal; no unmeasured RTO/RPO promise is made here.
