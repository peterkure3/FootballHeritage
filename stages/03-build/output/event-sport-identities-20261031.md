# Event sport and provider identity repair

Applied the idempotent canonical sport migration to the configured local backend.
All 4,499 event IDs and rows were preserved: SOCCER 3,177, BASKETBALL 1,312,
NFL 10. League evidence confirmed the 10 Football rows are NFL; the 347 football
rows are soccer. A database trigger normalizes future sport/league writes.
The migration also runs through the backend's normal migration chain on restart.

The old standardization utility incorrectly wrote FOOTBALL for soccer. It now
uses backend connection settings and the migration, previews with rollback by
default, and supports --apply.

NBA and football-data.org transforms now reconcile repeated snapshots by provider
ID and last_update before export. Football kickoff changes no longer create two
rows for one provider match. Conflicting teams for one ID raise an error. Raw
observations and bookmaker odds remain intact; repeated observations are expected.
The OddsAPI event writer now writes canonical sport labels.

Verification: four ingestion regression tests passed. Actual raw snapshot
transforms returned 461 NBA games and 1,539 football matches, each with zero
duplicate provider IDs (previously 1,219 and 8,961 raw observations respectively).
git diff --check passed. Fallow could not run because it is not installed.
Existing processed parquet files were not rewritten; the next transformation
exports reconciled data. Duplicate physical fixtures across different providers
were not merged, since they can have dependent bets and provider links.
