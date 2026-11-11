# Updating sport results

Run these commands from `pipeline/` with the pipeline Python dependencies installed:

| Sport | Command |
| --- | --- |
| Football | `py -3 -m etl.update_results --days 7` |
| NBA | `py -3 -m etl.update_nba_results --days 7` |
| Men's NCAA basketball | `py -3 -m etl.update_ncaab_results --days 7` |
| WNBA | `py -3 -m etl.update_wnba_results --days 7` |
| NFL | `py -3 -m etl.update_nfl_results --days 7` |
| NCAA football (FBS) | `py -3 -m etl.update_ncaaf_results --days 7` |

The five new entry points also work as absolute paths from another directory:

```powershell
py -3 "D:\Github\FootballHeritage\pipeline\etl\update_nba_results.py" --days 7
```

For the new scripts, `--check` inspects local captures without HTTP requests or writes:

```powershell
py -3 -m etl.update_nba_results --check
py -3 -m etl.update_ncaab_results --check
```

NBA/NCAAB checks also report eligible settled forecasts and pending or unverified
finals. A final score alone does not create a forecast: settlement requires a
retained, eligible pregame prediction. Football's existing `--check` checks its
database's pending matches instead.

Use an explicit inclusive date range to capture a particular day or backfill:

```powershell
py -3 -m etl.update_ncaab_results --start-date 2026-11-07 --end-date 2026-11-07
```

By default the range starts `--days` before today's UTC date and includes today,
matching the Football updater's lookback convention. Thus `--days 1` requests two
calendar dates. The new collectors allow at most a 90-day difference between
start and end, and reject future end dates. Scoreboard date buckets follow the
provider's calendar; normalized kickoff timestamps and capture times retain UTC
offsets. Adjacent date overlap is deduplicated.

## Storage and consumers

Football retains its existing football-data.org/database workflow. The other
scripts fetch ESPN public scoreboard JSON using the existing pipeline request
timeout/retry settings; no ESPN API key is required. College basketball uses
group 50 and college football group 80. The scripts share
`etl/update_sport_results.py` and publish into:

```text
data/raw/results/<sport>/<UTC capture timestamp>/
  YYYYMMDD.json
  normalized.jsonl
  manifest.json
```

The manifest records request parameters, retrieval times, raw and normalized
SHA-256 hashes, scope, and score policy. It is published last. A failed collection
exits nonzero, writes `failure.json`, and publishes no manifest; prior completed
captures remain usable. The loaders verify committed hashes before accepting
rows. Repeated identical captures do not duplicate games in `load_games`;
conflicting finals are quarantined by its existing conflict checks. A corrupt
committed capture raises an error instead of being silently accepted.

`models.sport_data.load_games` reads these captures after its historical season
preference rules, making recent finals available to existing model readers and
the NBA/NCAAB settled-performance feed. These scripts do not update the Football
`matches` table, betting balances, or wallets. They do not train/promote models,
refresh forecasts, install a schedule, or deploy services.

## Final-score and timing policy

Only explicitly completed regular-season/postseason finals are retained.
Preseason, live games and all-star games are excluded. Scores must be nonnegative
integers. Scores include overtime; NFL tied finals are retained and marked
`INCLUDING_OVERTIME_TIES_VOID`, while tied basketball/college-football finals are
rejected. These are observed provider finals, not independently reconciled scores
or universal sportsbook settlement rules.

`result_available_at` is the actual retrieval time, never backdated to game day.
Historical downloads therefore cannot be treated as inputs available at an
earlier forecast cutoff. Successful collection does not establish forecast
accuracy or profitability. WNBA/NFL/NCAAF use the same tested collector but have
separate sport scopes; empty date ranges legitimately publish zero finals.
