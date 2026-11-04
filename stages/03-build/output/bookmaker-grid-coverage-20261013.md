# Full bookmaker grid and Champions League coverage — 13 October 2026

## Implemented

The canonical operational inventory is `_config/bookmakers.json`, containing all 54 requested bookmakers with preserved regional identities. The previous stage inventories remain historical collection records. The collector defaults to the canonical inventory, and the dashboard returns it in `bookmakers`. Grid columns now combine that inventory with any extra observed sources; columns no longer disappear when a competition or page has no linked quotes.

Headers disclose fresh linked prices, stale/incomplete prices, or no linked prices. Missing prices remain dashes. The footer explains that missing collected evidence does not establish that an operator lacks the fixture. Existing freshness, regulation-time market validation, margin removal, and estimated EV rules remain in place.

The betPawa collector now discovers both Premier League and UEFA Champions League identifiers from the published category directory, using a separate bounded query for each competition. The existing adapter still requires complete regulation-time 1X2 prices and rejects live, started, suspended, incomplete and unrelated competitions.

`pipeline/scripts/sync_bookmaker_grid.py` links source snapshots by explicit competition, reviewed team-name mappings and exact UTC kickoff. Ambiguous identities are rejected. The name mappings affect dashboard ingestion only; the captured source records and model features are preserved. The existing periodic regional refresh calls this step before its EPL-specific repair/import step, so Champions League quotes are no longer dropped by EPL-only ingestion.

## Live evidence

Direct collection: `pipeline/data/raw/sportsbooks/20261013T194640017533Z/`.

- 1,195 validated snapshots: Bovada 1,166 across football competitions, betPawa 29 across EPL/CL.
- 47 snapshots linked to canonical upcoming fixtures and inserted: 29 EPL and 18 Champions League. Reapplying the same capture inserted zero rows.
- Champions League: nine fixtures have fresh prices from both Bovada and betPawa. The dashboard contains 18 upcoming Champions League fixtures; the other nine have no captured quote in this run.
- The running API on port 5555 automatically reloaded and returned 54 catalog entries and 18 fresh CL quotes.

Source collection outcomes across all 54 inventory entries:

| Outcome | Count | Required next step |
| --- | ---: | --- |
| Validated snapshots collected | 2 | Continue refreshing and exact matching |
| Public response needs adapter | 24 | Implement and verify source-specific market parsers |
| Access denied | 8 | Obtain an accessible authorized feed/integration |
| Connection failed | 12 | Resolve source availability, routing or TLS issues |
| Source verification pending | 7 | Establish exact operator domains and regional offerings |
| No complete upcoming 1X2 on captured page | 1 | Verify fixture/date coverage; AbaBet's captured page is today-only |

The odds-provider-only run at `pipeline/data/raw/sportsbooks/20261013T195251011560Z/` returned HTTP 401, `OUT_OF_USAGE_CREDITS`, zero remaining credits, and zero request cost. It stopped after the first rejected request. Restoring provider quota is necessary to obtain prices for the mapped bookmakers through that integration. `--provider-only` now permits that collection without repeating all public-site requests; it is not enabled automatically in the periodic job.

The read-only AbaBet date probes continued returning the current day even when the published form's date and search fields were submitted. Its adapter was not broadened without verifying a working future-fixture date response. SportPesa and Fortebet could not be verified live in this run because their source requests failed. Their existing adapters remain intact.

Full per-book source outcomes, timestamps and URLs: `bookmaker-grid-coverage-20261013.json`.

Primary live operator evidence: [betPawa Uganda](https://www.betpawa.ug/) lists UEFA Champions League fixtures and full-time 1X2 markets. Coverage for all 54 operators was not assumed from that one site.

## Verification

- 38 Python tests passed across catalog/matching, dashboard (including rollback-only PostgreSQL), collectors and regional pipeline.
- Four Chromium grid checks passed, including all 54 columns across paging/filtering, missing prices, stale-price/EV rules, mobile overflow and real API data.
- Targeted ESLint, TypeScript and production build passed. Python syntax compilation and scoped whitespace checks passed.
- The first inventory browser test used an unsuitable label selector; it passed after switching to the observed combobox accessible name. All four checks passed together on the final rerun.
- Fallow was not installed locally; `npx --no-install fallow --summary` could not run. Source usage searches, focused tests, build/lint and real data verification were used.

All bookmakers are now represented in the grid. Full live-price coverage remains dependent on the source integrations and provider quota described above. No source prices were invented, no models were retrained and no bets were placed.
