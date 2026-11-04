# Sportsbook odds for 18 October 2026

Collected with the existing Scrapling HTTP transport and football 1X2 adapters. The requested “tomorrow” was fixed to Sunday 18 October in Africa/Kampala when collection started on 17 October. Window: 17 October 21:00 UTC through 18 October 21:00 UTC, end exclusive.

Capture completed at 17 October 19:32:27 UTC / 22:32:27 EAT. Across 46 configured sources, seven produced 1,545 complete prematch regulation-time football odds snapshots across all dates. Exactly 900 snapshots fall within the requested Kampala calendar day:

| Sportsbook | 18 October snapshots |
|---|---:|
| Bovada | 892 |
| betPawa | 4 |
| SportPesa | 4 |

Each snapshot contains home/draw/away decimal prices, fixture kickoff, observation time and raw source reference. “Snapshots” are bookmaker market listings, not a count of uniquely reconciled fixtures across all sources.

## App update

Twelve quotes were linked to four existing Premier League fixtures by reviewed team identity, competition and exact kickoff. Stored prices and timestamps were read back and verified. Repeat ingestion inserted zero duplicates. The first import completed before a timezone-formatting exception in the verification output; the corrected duplicate-safe rerun verified all 12 stored quotes. Its `database_inserted: 0` describes that repeat pass, while `database_verified: 12` records the successfully stored capture.

- AFC Bournemouth vs Sunderland AFC — 16:00 EAT
- Leeds United vs Manchester United — 16:00 EAT
- Brighton & Hove Albion vs Crystal Palace — 16:00 EAT
- Nottingham Forest vs Arsenal — 18:30 EAT

The remaining 888 captured quotes lack a match to the app's currently stored fixture catalog; they remain available in the export. The live dashboard returned HTTP 200 and all four fixtures. Other displayed books are separate scheduled captures and are not attributed to this Scrapling run. No predictions, paper-trial decisions, model artifacts or completed results were changed.

## Source coverage

Seven collected sources; 22 public responses need adapters; four crawl-policy exclusions; four connection failures; two access denials; six sources lack verified URLs; one returned no complete upcoming 1X2 prices. Four of the seven collected books had quotes on other dates but none for the requested day. No paid provider fallback was requested.

PowerShell reported native stderr as an error while redirecting Scrapling's INFO logs. The collector nevertheless produced its completed source report and dataset; those outputs were parsed and validated independently.

## Evidence

- Original capture: `pipeline/data/raw/sportsbooks/scrapling-tomorrow-20261018-20261017-01/`
- Date-filtered export: `pipeline/data/raw/sportsbooks/scrapling-tomorrow-20261018-20261017-01/tomorrow-20261018-EAT/odds_snapshots.jsonl`
- Summary and verified prices: `stages/03-build/output/scrapling-tomorrow-20261018.json`
- Dashboard response: `stages/03-build/output/scrapling-tomorrow-dashboard-20261018.json`
- Filtering/import verification script: `stages/03-build/output/import-tomorrow-scrapling-20261018.py`
