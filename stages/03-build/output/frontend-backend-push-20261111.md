# Frontend and backend publication

Publish the pending sport prediction workspace, navigation and basketball settled
performance changes on `feature/footballheritage-frontend`.

## Scope

- Frontend: shared sport prediction cards, two-way bookmaker grids, sport-scoped
  model tools, NBA/NCAAB performance views, sport navigation and responsive layout.
- Rust: publish the read-only settled-performance gateway route and its test.
- Python dependencies: scheduled fixtures in intelligence responses, retained
  pregame forecasts, settled-performance API, matching gateway contracts/prewarm,
  and verified recent-final result loaders with sport CLI entry points and tests.
- Snapshot refresh retains forecasts; unrelated market-collector, training,
  automation, research and CI edits remain outside this commit.

## Verification

- Frontend `npm run lint` and `npm run build`: passed. Build includes type checking.
  Existing Zod/Rollup annotation warnings remain non-fatal.
- Chromium regression selection: 73 passed, 5 skipped, 1 failed. The failure was a
  stale assertion expecting previous access-error wording. Updated it to assert
  the existing `Connection interrupted` heading; reran all four feature-management
  tests successfully. Skipped cases require explicit live-service configuration.
- Python: `py -3 -m pytest tests/test_nba_grid_duplicates.py
  tests/test_betting_intel.py tests/test_sport_performance.py
  tests/test_update_sport_results.py tests/test_gateway_publication.py -q`
  from `pipeline/`: 55 passed, 8 subtests passed. Two existing UTC deprecation
  warnings remain.
- Rust: `SQLX_OFFLINE=true cargo test
  settled_performance_route_is_read_only -- --nocapture` from `backend/`: passed.
  Existing sqlx future-compatibility warning remains.
- Staged whitespace check: passed. Both gateway manifests publish the same route.

This publication does not deploy the services or promote any candidate model.
