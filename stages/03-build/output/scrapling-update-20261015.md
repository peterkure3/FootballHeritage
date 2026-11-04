# Scrapling sportsbook data update — 2026-10-15

Fresh public sportsbook data was collected with **Scrapling 0.4.15**, using its
HTTP Fetcher and the existing football market parsers. No paid odds provider was
used. The isolated runtime is `pipeline/.venv-scrapling`; install requirements
are in `pipeline/requirements-scraping.txt`.

## Collection

The run covered the current 46-source inventory. It produced 1,190 prematch,
regulation-time 1X2 snapshots from seven sportsbooks:

| Bookmaker | Captured snapshots |
|---|---:|
| Bovada | 1,060 |
| betPawa | 38 |
| SportPesa | 20 |
| BookMaker | 18 |
| 1xBet | 18 |
| 22Bet | 18 |
| Cloudbet | 18 |

Other outcomes: 23 public responses need adapters, six sources were excluded by
crawl policy or an unavailable crawl-policy response, two denied access, two had
no complete upcoming prices, and six lacked a verified URL. Betika's robots URL
returned 403; Fortebet's policy excluded its endpoint. Their older stored quotes
were retained and were not presented as newly scraped data. No denial was bypassed.

Raw responses, timestamps, final URLs, page evidence, normalized snapshots, and
per-source statuses are stored in
`pipeline/data/raw/sportsbooks/scrapling-20261015-01/`.

## Database update and verification

- Grid ingestion inserted 80 quotes: 44 Premier League and 36 Champions League.
- Official EPL identity matching added four further quotes: **84 inserted quotes
  across 28 fixtures** in total. No fixture kickoff repairs were needed.
- Every inserted quote was independently checked against its captured price,
  fixture, operator, and timestamp. BookMaker's line ordering was mapped to the
  stored home/away orientation before comparing its prices.
- Repeating grid ingestion inserted zero duplicates.
- The training store received 60 EPL observations from three books. Its Parquet
  checksum and row count verified. These observations require final results
  before they can supply training labels.
- Backend synchronization processed 1,733 matches (1,272 soccer and 461
  basketball), with zero errors.
- Live dashboard HTTP GET returned 200, 38 fixtures, and 105 fresh quotes from
  nine bookmakers, including still-fresh quotes from earlier captures.
- The active model was not changed or retrained.

Machine-readable evidence is in `scrapling-update-20261015.json`. The reproducible
verification script is `verify-scrapling-20261015.py` in this directory.

## Reuse

From `pipeline/`, choose a new capture directory for each immutable collection:

```powershell
.\.venv-scrapling\Scripts\python.exe -m etl.scrape_sportsbooks --transport scrapling --output-dir data/raw/sportsbooks/NEW_RUN
py -3 -m scripts.sync_bookmaker_grid --capture data/raw/sportsbooks/NEW_RUN --apply
py -3 -m scripts.sync_verified_odds --capture data/raw/sportsbooks/NEW_RUN --match-date YYYY-MM-DD --output data/raw/sportsbooks/NEW_RUN/epl_sync.json --apply
py -3 sync_to_backend.py
```

The optional transport covers the main feed, market/category metadata, and all
pagination requests. The default requests transport remains available. Anonymous
public collection retains the current parser rules for complete prices,
prematch timing, and regulation-time markets. Unsupported responses do not become
invented or inferred quotes.

## Checks

31 tests passed: Scrapling transport (6), sportsbook scraping (10), network
adapters (6), supplied bookmaker adapters (9). Python compilation and
`git diff --check` passed. Fallow audit retained the preceding workspace-wide
finding counts (two dead-code findings, 14 complexity findings, one clone group);
root dependency analysis has reduced confidence because root `node_modules` is
absent. See `scrapling-fallow-20261015.txt`.
