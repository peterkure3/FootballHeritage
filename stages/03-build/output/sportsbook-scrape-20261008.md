# Sportsbook collection — 8 October 2026

Attempted all 20 requested sources with anonymous public HTTP requests. Captures
were observed at approximately 17:46 UTC. Export contains **2,084 football 1x2
price snapshots from 12 sportsbooks**, each with three decimal prices, source
provenance, original observation timestamp and a future kickoff.

## Collection routes

- **Direct public Bovada feed:** 1,706 complete upcoming regulation-time markets.
  Only scheduled, non-live GAMEEVENT events and explicitly open 3W-1X2 markets
  with regulation period 100 were exported. Competitor IDs are checked against
  selection IDs. Raw data contains no explicitly virtual/simulation league labels;
  that label check is not independent verification of every listed fixture.
  Coverage spans countries, league levels, women and youth competitions; league
  IDs and country are retained to support subsequent training scope filters.
- **Existing The Odds API feed:** 378 snapshots from EPL and Champions League,
  including 37 Bovada observations. These are separate source observations and
  must not be counted as additional unique matches. Explicit open/suspended flags
  are unavailable, so these records retain UNKNOWN availability.
- Two provider requests consumed four quota credits. No further requests were
  made to normalize the saved direct capture.

| Bookmaker | Snapshots | Route |
|---|---:|---|
| DraftKings | 38 | Provider |
| FanDuel | 38 | Provider |
| BetMGM | 28 | Provider |
| Caesars | 0 | Public HTML only; no provider prices returned |
| theScore Bet (requested ESPN BET) | 28 | Provider key espnbet |
| Fanatics | 0 | Direct HTTP 403; no provider prices returned |
| bet365 | 0 | Direct HTTP 403; configured provider mapping has no football coverage |
| BetRivers | 38 | Provider |
| Hard Rock Bet | 38 | Provider |
| Circa | 0 | Public betting-menu page; no complete extracted 1x2 quotes |
| SuperBook | 0 | Connection failed |
| Bally Bet | 38 | Provider |
| Betfred | 37 | Provider UK feed |
| BetOnline | 28 | Provider |
| Bovada | 1,743 | 1,706 direct + 37 provider |
| MyBookie | 20 | Provider; direct target returned HTTP 404 |
| BookMaker | 0 | Public lines host connection failed |
| Heritage Sports | 0 | Direct HTTP 403 |
| EveryGame | 10 | Provider |
| SportsBetting.ag | 0 | Public HTML; price script requests returned access challenges |

Regional availability and executable bet acceptance were not verified. Public
HTML HTTP 200 responses are not treated as successful price collection. Protected
responses were preserved for diagnosis, without retrying to bypass denial.
The in-app browser runtime failed to connect, so JavaScript-dependent prices
could not be inspected in this run. The eight uncovered books still need a
working permitted price source and parser; this run does not establish coverage
for them.

## Files

Run directory: `pipeline/data/raw/sportsbooks/20261008T174556306527Z/`

- `odds_snapshots_complete.jsonl`: complete derived export, 2,084 records.
- `normalization_report.json`: collection routes, counts and source status for all
  20 books, including normalization time separate from original observation time.
- `odds_snapshots.jsonl` and `source_report.json`: unchanged initial provider export
  and original run report.
- `raw/`: preserved anonymous site responses and provider event payloads.

Raw runs are ignored by Git. No database import, model training or active model
change was performed. These are current observations, not historical closing
prices; results and fixture mapping are still needed for prospective evaluation.

Validation passed for all 2,084 records: unique snapshot IDs, three distinct
selections, finite decimal prices above one, observation before kickoff, existing
raw capture references and exact per-book report counts. All 37 Python behavioral
tests passed, including rejection of live, started, non-game, suspended,
wrong-period and mismatched-selection records. Python compilation and patch
whitespace checks passed.

## Reuse

From `pipeline/`, collect a new direct-only run:

```powershell
py -3 -m etl.scrape_sportsbooks
```

Add `--provider-fallback` to request the configured feed for EPL and Champions
League, or supply explicit `--sports soccer_epl ...` football provider keys.
Every run gets a new directory and refuses to overwrite an existing output.
For older captures made before the direct parser was added:

```powershell
py -3 -m etl.scrape_sportsbooks --normalize-run data/raw/sportsbooks/RUN_ID
```

This command creates derived files once and makes no network requests. New runs
already include parsed direct prices in their main JSONL export.
