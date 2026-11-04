# Local prediction API database repair — 2026-10-24

The Rust gateway returned `503 UPSTREAM_UNAVAILABLE` for the fixture feed.
The private Python API was reachable and internal tokens matched. A direct
authorized request returned `503 Prediction database is unavailable`.

A read-only connection diagnostic found that local `pipeline/.env` contained a
`DATABASE_URL` without a database name. This setting overrides `DB_NAME`, so
SQLAlchemy connected to `postgres` and the fixture query failed with
`relation "matches" does not exist`. The existing `football_betting` database
contained the expected table and 1,662 matches.

Updated only the database path in the local `DATABASE_URL` to `football_betting`,
preserving credentials and all other settings. Restarted the identified local
Python API and its reloader with hidden windows and local log files. No schema
changes, data ingestion, training, or database mutations were performed.

Verification through the Rust gateway:

- `/prediction-dashboard/fixtures?page=1&page_size=6`: HTTP 200, six items,
  18 upcoming fixtures total.
- `/prediction-dashboard/operations`: HTTP 200.
- `/prediction-dashboard/paper-trials`: HTTP 200.
- Chromium loaded the local frontend and invoked its actual `predictionService`:
  browser request returned HTTP 200 with six items and 18 fixtures total, confirming
  the browser-to-Rust-to-Python path and CORS. No additional test account created.

The original fixtures error was caused by local database selection, separate
from the earlier frontend localhost/IPv4 API routing conflict.
