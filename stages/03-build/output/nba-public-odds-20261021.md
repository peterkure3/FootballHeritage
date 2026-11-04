# Public NBA odds collection and validation — 21 October 2026

Accepted capture completed **21 October, 00:48:42 Kampala time** (20 October, 21:48:42 UTC). These are timestamped quotes, not verified executable offers or guaranteed returns.

## Result

**34 complete overtime-inclusive moneyline pairs across 17 distinct NBA fixtures** were accepted: 17 Cloudbet pairs and 17 betPawa Uganda pairs. All matched a unique game in the independent BALLDONTLIE schedule by canonical NBA team identity, home/away orientation, exact UTC kickoff and scheduled/not-postponed state. The independent date-window capture contains 56 games, including past or in-progress games that are not eligible for these prematch prices. This is bounded moneyline coverage, not a complete NBA schedule or all bookmaker markets.

The live `/api/v1/betting-intel/nba` snapshot was verified with 17 experimental candidate forecasts, 34 de-vig rows, 29 positive gross model-EV comparisons and zero nominal arbitrage combinations. EV comparisons include multiple bookmakers for the same game and are not 29 independent recommended wagers. The historical model has not demonstrated a proven betting edge. Player props were not collected in this run.

Raw/public source directory and accepted data:

- `pipeline/data/raw/nba_public/20261020T214831986060Z/manifest.json`
- `pipeline/data/raw/nba_public/20261020T214831986060Z/validated_fixtures.json`
- `stages/03-build/output/nba-public-verification-20261021.json`

## Sources and exclusions

| Source | Observation | Publication |
|---|---|---|
| Cloudbet public basketball page and public NBA feed | HTTP 200; enabled BACK selections in `basketball.moneyline`, `period=ot&period=ft` | 17 complete pairs |
| betPawa Uganda public page, basketball directory and NBA event query | HTTP 200; NBA/USA directory identity; `Moneyline - FT incl OT`; both sides unsuspended | 17 complete pairs |
| Bovada public NBA page and feed | HTTP 200, but feed cache Age exceeded the two-minute price-response allowance; an earlier observed Age was 452 seconds | Rejected from final publication |
| Betika public page/global directory | Page and directory available; Uganda API robots policy returned 403 and could not be verified | No odds harvested from the denied origin |
| BALLDONTLIE NBA games | HTTP 200 using the configured local key; 56 date-window games in final validation capture | Independent fixture verification |
| BALLDONTLIE NBA current odds | Both `/nba/v2/odds` and documented `/v2/odds` returned HTTP 401 Unauthorized | No provider odds ingested |
| BALLDONTLIE NBA opening odds | `/nba/v2/odds/opening` returned HTTP 401 Unauthorized | No opening odds ingested |

Entitlement evidence is in `nba-balldontlie-access-20261021.json`. A successful games request confirms that the configured header/key works for that endpoint; account subscription settings were not inspected. No subscription was purchased and no key was persisted in captures or reports.

Source contracts were checked against the [BALLDONTLIE NBA documentation](https://docs.balldontlie.io/#get-betting-odds), [Cloudbet market documentation](https://cloudbet.github.io/wiki/en/docs/sports/api/markets/) and [Bovada basketball rules](https://www.bovada.lv/help/common-faq/basketball-betting-rules). Scrapling retrieved the public pages and their anonymous published price feeds; no login, private account session or executable bet placement was used.

## Validation and pipeline changes

`etl.nba_public_parsers` rejects non-NBA competitions, live/started games, unknown teams, incomplete or duplicate selections, suspended markets, LAY quotes, incompatible periods, zero available maximum stake and invalid prices. Bovada decimal prices must agree with their American representation. Team matching uses reviewed aliases, never fuzzy similarity. Cloudbet abbreviations are translated before matching to the independent schedule.

`etl.fetch_nba_public_odds` uses the existing robots-aware Scrapling transport, retains page/feed bytes, UTC retrieval times, HTTP Date/cache Age and SHA-256 checksums, and records rejected source responses. Price responses over two minutes old in cache or with stale/future HTTP dates are ineligible. Static page caching alone does not establish the freshness of its separate price feed. The price timestamp means observed at retrieval; it is not a claim that the bookmaker changed the price at that instant.

Only independently matched fixture/market pairs enter `validated_fixtures.json`. The intelligence loader checks both normalized-data and underlying-source hashes and refuses captures older than 30 minutes. The normal intelligence policy also rechecks per-quote age, pre-kickoff state, complete markets and opposing-leg time skew. Available source failures remain visible as partial coverage.

The same independent schedule check withheld **31 older stored NBA fixture entries** that did not match a unique scheduled game. These were not declared definitively false and were not deleted from the database. They are excluded from the published NBA snapshot and retained under `nba_fixture_exclusions` in `data/processed/betting_intel/snapshot.json`. Public-source string timestamps and reviewed model-history name aliases are now supported by offline candidate inference. No active model was promoted or retrained.

The existing recurring regional refresh now invokes the NBA collector through the workspace's `.venv-scrapling` interpreter before publishing intelligence. It does not silently switch to another transport if Scrapling is unavailable. This updates the existing refresh entry point; it does not install a new schedule.

Manual refresh, from `pipeline/`:

```powershell
.\.venv-scrapling\Scripts\python.exe -m etl.fetch_nba_public_odds
py -3 -m etl.betting_intel
```

## Verification

- 13 NBA parser, cache, identity, integrity and candidate timestamp/alias regression tests passed.
- All 24 existing betting intelligence tests passed.
- Existing regional pipeline suite: 16 passed; one database-gated test skipped.
- Targeted Python compilation passed.
- Independent raw replay and live HTTP verification passed: all 68 published selection prices equal the accepted source evidence; de-vig probabilities were recomputed with decimal arithmetic; model EV formulas and probability sums were reproduced.
- Repository Fallow baseline and post-change audits remain failing on broader existing JavaScript/TypeScript findings, with incomplete root dependency resolution. Fallow does not validate Python scraping logic; no clean repository audit is claimed.

Coverage and freshness limits remain explicit. Fixture validation does not independently verify bookmaker acceptance, limits, taxes, settlement exceptions or price execution. No bets were placed.
