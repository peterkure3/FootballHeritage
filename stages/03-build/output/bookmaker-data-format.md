# Bookmaker scraper data contract v1

Use UTF-8 JSON Lines (`.jsonl`): one JSON object per line. All example prices and
fixtures in the accompanying files are synthetic illustrations, not actual offers.

## Files

- `odds_snapshots.jsonl`: append one record per bookmaker, fixture, market and
  observation. Never replace an earlier observation when prices change.
- `match_results.jsonl`: separate final regulation-time results, with the time
  the completed result became known. Do not attach final results to prematch snapshots.
- Optional `team_mapping.json`: reviewed provider team IDs to canonical team IDs.
  Preserve raw names and IDs even after mapping.

## Required odds snapshot fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | `1.0` |
| `snapshot_id` | string | Unique immutable observation ID; UUID recommended |
| `provider` | string | Scraper/source ID, e.g. `scraper_examplebook` |
| `bookmaker` | string | Stable bookmaker slug, e.g. `examplebook` |
| `provider_event_id` | string | Event ID from this source; never a team-name-generated guess |
| `sport` | string | `football` for the current predictor |
| `competition` | string | Full competition name from source |
| `home_team`, `away_team` | string | Names exactly as published |
| `commence_time` | string | Published kickoff converted to UTC ISO 8601 |
| `observed_at` | string | UTC time the scraper actually observed this price snapshot |
| `source_updated_at` | string or null | Timestamp published by site; null if unavailable |
| `is_live` | boolean | Whether the source presents the market as in-play |
| `event_status` | string | `SCHEDULED`, `IN_PLAY`, `FINISHED`, `POSTPONED`, `CANCELLED`, `UNKNOWN` |
| `market` | string | `h2h` for football three-way match result |
| `period` | string | `FULL_TIME_90_MIN` for regulation time including stoppage time |
| `settlement_rule` | string | `REGULATION_TIME`; extra time and penalties excluded |
| `market_status` | string | `OPEN`, `SUSPENDED`, `CLOSED`, `UNKNOWN` |
| `outcomes` | array | Entire market captured together, with outcome prices/status |
| `source_url` | string | Exact public page/API URL; remove session tokens and credentials |

Each outcome contains `selection` (`HOME`, `DRAW`, `AWAY`), `odds_decimal`
(number >1 for an available offer), `status` (`OPEN`, `SUSPENDED`, `CLOSED`, `UNKNOWN`),
`line` (null for h2h), and `participant` (null for h2h). An unavailable outcome may
have `odds_decimal: null`; do not invent a replacement. Exclude incomplete markets
from model market features and fair-probability/edge comparisons.

## Valuable additional fields

| Field | Meaning |
|---|---|
| `country`, `season` | Competition identity; season as `2026/27`, not inferred from observation date |
| `provider_home_team_id`, `provider_away_team_id` | Stable source team identifiers |
| `canonical_event_id`, `canonical_home_team_id`, `canonical_away_team_id` | Null until a reviewed mapping exists |
| `provider_market_id`, outcome `provider_selection_id` | Source market/selection IDs |
| `market_name_raw`, outcome `selection_name_raw` | Unmodified displayed labels |
| `kickoff_raw`, `source_timezone` | Original kickoff text/timezone used for UTC conversion |
| `odds_raw`, `odds_format_raw` on each outcome | Original fractional/American/decimal price and format |
| `region`, `currency` | Geographic offer variant and applicable account currency |
| `min_stake`, `max_stake` on each outcome | Explicit advertised stake limits; null when unavailable |
| `commission_rate` | Explicit exchange commission fraction; null when unknown |
| `rules_url` | Market settlement rule reference |
| `scraper_version`, `scrape_run_id`, `raw_capture_ref` | Parser provenance and immutable raw capture reference |

Never record unknown limits/fees as zero. Promotions, boosts, exchanges and ordinary
sportsbook odds should have distinct offer/market identities so they are not mixed.

## Other markets

| `market` | `selection` | Outcome `line` | Notes |
|---|---|---|---|
| `h2h` | `HOME`, `DRAW`, `AWAY` | null | Current football predictor and bookmaker demo |
| `totals` | `OVER`, `UNDER` | e.g. 2.5 | Same total line for both selections |
| `spreads` | `HOME`, `AWAY` | e.g. -0.5, +0.5 | Signed handicap from each selection's perspective |
| `btts` | `YES`, `NO` | null | Store separately; current ingestion does not consume it |

Always preserve period and settlement rules. First-half, qualification, extra-time,
Asian handicap and three-way European handicap markets are different contracts.
For handicaps add `handicap_type` and preserve the source's exact rules; do not
collapse them solely because the line is equal. Quarter-line Asian settlement
requires half-win/half-loss handling and is outside the current 1x2 demo.

## Results file

Required: `provider`, `provider_event_id`, `sport`, `competition`, `home_team`,
`away_team`, `commence_time`, `status`, `score_period`, `home_score`, `away_score`,
`result`, `result_observed_at`, `source_url`.

For a completed 90-minute match use `status: FINISHED`,
`score_period: FULL_TIME_90_MIN`, integer scores >=0, and
`result: home_win | draw | away_win`. The outcome must agree with the scores.
Keep extra-time/penalty scores separately. Unfinished matches have null final scores
and null result; preserve postponed/cancelled status and kickoff revisions.
If a bookmaker publishes bet settlement, retain it separately from the football
result (including voids and corrections).

## Collection and validation rules

1. Capture all three HOME/DRAW/AWAY prices from the same market observation.
2. Store every observation as a new record. A bookmaker timestamp is not a substitute
   for `observed_at`; do not backdate data fetched after kickoff.
3. Training/backtests may only use snapshots observed before the prediction cutoff
   and kickoff, with an open prematch market. Retain suspended/live records for audit,
   but exclude them from prematch pricing features.
4. Use precise timezone-aware UTC timestamps, e.g. `2026-10-01T16:00:00Z`.
   Preserve raw timezone/text; unknown timezones or date-only kickoffs must be flagged,
   not silently converted to an invented kickoff hour.
5. Keep independent site IDs and explicit team mappings. Never join by substring
   team names alone, or compare HOME prices when home/away order is reversed.
6. Record the source competition and distinguish men's/women's/youth/reserve teams.
7. Save raw decimal prices. Margin removal and implied probabilities are derived
   during analysis; never overwrite observed prices with normalized probabilities.
8. Opening/closing prices should be derived from the observation history. A price
   captured after kickoff cannot retrospectively become a prematch closing price.
9. Preserve original source snapshots or responses for parser auditing; exclude
   credentials, cookies and account data from captures.

For a useful prospective demo, choose a prediction horizon (e.g. one hour before
kickoff), freeze model predictions at that time, retain the actual available prices,
then settle all predeclared fixtures. Scraping current prices cannot reconstruct
missing historical odds.

## Current pipeline compatibility

This is the recommended multi-site collection contract, not a new importer already
installed. `etl/ingest_oddsapi_offers.py` currently expects Odds API event/bookmaker/
market/outcome nesting, an enabled sportsbook registry entry, and provider `oddsapi`.
An adapter is needed for each new scraper source; merely placing these files in the
raw folder does not ingest them automatically. It currently handles h2h, totals and
spreads and normalizes selections to uppercase.

The predictor's wide football odds representation is:

```text
home_team,away_team,commence_time,bookmaker,updated_at,home_win,draw,away_win
```

For an adapter, map `updated_at` to the scraper's `observed_at` and retain
`source_updated_at` separately. Map HOME/DRAW/AWAY `odds_decimal` to
`home_win`/`draw`/`away_win`. Attach reviewed fixture IDs after event matching.
Only complete open regulation-time h2h snapshots enter this table. The existing
model joins use explicit identities and UTC fixture day, with prematch timestamps.
The simple wide table does not preserve the full snapshot/status/provenance contract,
so keep the JSONL archive as the source of truth.
