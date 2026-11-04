# NFL and college football source collection and models — 2026-10-15

Collected official nflverse/nflfastR files and authenticated CollegeFootballData (CFBD) games/lines, exported validated datasets, and trained five separately evaluated models. All saved artifacts and metrics were independently verified. No model was activated.

## Sources and coverage

Capture directory: `pipeline/data/raw/historical/gridiron_sources/20261015/`.

The checksummed manifest contains 32 successful source captures with no failures: one nflverse schedule CSV, three nflfastR play-by-play Parquet seasons, and 28 CFBD API responses (games and lines for each season 2013–2026). The CFBD collection made 28 authenticated requests. The supplied key is in ignored local `pipeline/.env`; it does not appear in the new code or training evidence.

| Corpus | Raw/processed coverage | Validated completed games | Complete moneyline pairs |
|---|---|---:|---:|
| NFL schedule | Raw seasons 1999–2026; fitted history September 2000–October 13, 2026 | 7,096 | 5,374 |
| College football | Seasons 2013–2026, through October 13, 2026 | 11,668 | 4,313 |
| nflfastR play-by-play | Seasons 2023, 2024, 2025, including postseason | 855 linked games | Not an odds source |

The NFL raw schedule has 7,548 rows including future games. There are 259 completed 1999 games without kickoff times; they remain in the raw CSV and were excluded from the fitted exact-time corpus. Future/unfinished games and results whose conservative availability is still in the future are also excluded. NFL franchise relocations use explicit aliases; the 16 final ties update team history but are excluded from two-way winner labels.

CFBD returned 33,266 raw game rows across all classifications. The fitted scope is regular/postseason games with at least one FBS participant, including FBS–FCS games; standalone lower divisions, unfinished/future games and exhibitions are excluded. Native game IDs, team IDs/names, kickoff and final scores validate joins to lines. There were zero odds identity mismatches and zero invalid prices. Stable school IDs preserve historical identity through renames. The raw API payloads retain additional supplied fields; current-game box scores and postgame/pregame provider ratings are not used as winner-model features.

The college odds export contains 36,416 per-provider records, including partial line records without moneylines. Providers include Bovada, Caesars variants, DraftKings, ESPN Bet, SugarHouse, William Hill, consensus, numberfire and teamrankings. Spread/total openings and final archived values are preserved where supplied. For model inputs, complete decimal home/away pairs are converted from American prices and aggregated by the median across available books for each native game ID. These aggregate prices are statistical features, not a claim of executable sportsbook prices.

nflfastR raw play counts: 49,665 (2023), 49,492 (2024), 48,771 (2025), totaling 147,928 rows. Run/pass plays with valid possession-team/EPA values produce 1,710 team-game aggregates containing offensive EPA per play, success rate and yards per play. The efficiency model uses rolling prior-game offense/defense EPA and success rates, with a conservative two-day availability delay. Same-game, same-day and future results cannot enter prior features.

Primary source references:

- [nflfastR play-by-play release documentation](https://nflreadr.nflverse.com/reference/load_pbp.html)
- [nflverse schedules and field dictionary](https://nflreadr.nflverse.com/articles/dictionary_schedules.html)
- [nflverse source schedules](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- [CFBD games and endpoint documentation](https://github.com/CFBD/cfbd-python/blob/main/docs/GamesApi.md)
- [CFBD historical betting-lines API](https://github.com/CFBD/cfbd-python/blob/main/docs/BettingApi.md)
- [CFBD exporter](https://collegefootballdata.com/exporter)

## Pro Football Reference limitation

The requested 2025 PFR games page returned HTTP 403. Sports Reference also publishes restrictions on using its content to train or support predictive machine learning without authorization. No PFR pages were harvested and no authentication or access restrictions were bypassed. The nflverse schedule's PFR box-score IDs are retained as cross-reference identifiers only; they are not a claim of PFR data collection. An authorized PFR export could be evaluated separately later.

## Saved models

History candidate ID: `20261015T194812812329Z`.

- Standard history candidates: `pipeline/models/model_store/candidates/sports/20261015T194812812329Z/{nfl,ncaaf}/`.
- Archive-odds research estimators: `pipeline/models/model_store/research/gridiron_sources/20261015T194812812329Z/{nfl,ncaaf}/`.
- nflfastR efficiency estimator: `pipeline/models/model_store/research/gridiron_sources/20261015T194812812329Z/nfl_efficiency/`.

Each model has its own estimator, dataset, feature contract, calibration, metrics and checksums. The efficiency estimator also retains its full feature matrix. Standard history candidates are discoverable through the existing `/api/v1/sport-models` catalog and preview endpoint; the research estimators stay outside that catalog.

All models use standardized logistic regression selected on chronological tuning data, then refit on train+tune and independently sigmoid-calibrated. Test results do not select parameters. Labels unavailable before the next partition are purged. History features include league-specific Elo, previous results, scoring/conceding, margins, rest and recent game load; neutral sites remove the home-field advantage term. The efficiency estimator adds lagged nflfastR metrics. There is no claimed quarterback, injury, lineup, weather, spread-target or total-target model.

| Model | Held-out games | Accuracy | Log loss | Development-prior accuracy |
|---|---:|---:|---:|---:|
| NFL history | 900 | 64.56% | 0.6352 | 55.22% |
| NFL history + archive odds | 900 | 68.00% | 0.6121 | 55.22% |
| College history | 1,676 | 74.52% | 0.5025 | 65.27% |
| College history + archive odds | 1,676 | 77.15% | 0.4664 | 65.27% |
| NFL recent-season nflfastR efficiency | 120 | 61.67% | 0.6624 | 51.67% |

NFL main test period: September 22, 2023–October 13, 2026. College main test period: November 6, 2024–October 13, 2026. The efficiency model uses 855 games from three recent seasons, with test games November 23, 2025–February 8, 2026. Its performance is not directly comparable with the longer-history NFL evaluation.

Archive market coverage by labeled partition:

| Sport | Train | Tune | Calibration | Test |
|---|---:|---:|---:|---:|
| NFL | 2,901 | 947 | 606 | 900 |
| College | 307 | 1,415 | 1,011 | 1,530 |

On the identical odds-covered test subsets, NFL archive-model accuracy is 68.00% versus 68.11% from vig-free archived prices, with log loss 0.6121 versus 0.6102. College accuracy is 74.97% for both, with log loss 0.5046 for the model versus 0.4940 for archived prices. The full college test also contains 146 games without prices, routed to history. The results do not establish improvement over bookmaker probabilities or a profitable betting strategy.

## Historical timing and status

Archival moneylines have no verified historical observation timestamps. Those fields remain null; collection time is retained separately as retrieval metadata. Archive odds are not injected into the timestamp-verified public-quote directory, and existing strict matching rules are not weakened. Models using them are explicitly research-only. The two API-visible history candidates contain no archive odds inputs and remain inactive. The nflfastR efficiency estimator is an additional inactive research artifact with a distinct feature contract.

NFL probabilities are conditional on no final tie and use `INCLUDING_OVERTIME_TIES_VOID`; they apply to a two-way winner market only if final ties void the bet. College outcomes include overtime. All results are retrospective.

## Exports and reproducibility

Under the capture's `normalized/` directory:

- `nfl_games_odds.csv` / `.parquet` and `ncaaf_games_odds.csv` / `.parquet`.
- `cfbd_quotes.csv`: provider-specific native-ID lines, openings and moneylines.
- `nflfastR_team_game_efficiency.csv` / `.parquet`.

From `pipeline/`:

```powershell
.\.venv-scrapling\Scripts\python.exe -m etl.fetch_gridiron_sources --source all --public-transport scrapling --output-dir data/raw/historical/gridiron_sources/20261015
py -3 -m models.train_gridiron_sources --capture-dir data/raw/historical/gridiron_sources/20261015
py -3 -m scripts.verify_sport_models --candidate-id 20261015T194812812329Z --sports nfl ncaaf
py -3 -m scripts.smoke_sport_models --candidate-id 20261015T194812812329Z --americanfootball-leagues
py -3 ..\stages\03-build\output\verify-gridiron-20261015.py
```

Collection caches checksummed files and resumes without repeating successful API requests. Use a fresh output directory for a new snapshot. Training always creates a new run. `--years`, `--pbp-years` and `--max-api-calls` bound collection. CFBD uses authenticated API requests; the public schedule uses Scrapling and official play-by-play assets use direct release downloads.

## Verification

- 29 behavioral tests passed: ten new source/EPA checks, nine existing American football checks and ten existing sport-model checks.
- All 32 source checksums passed. CSV/Parquet counts, unique native IDs and null archival observation timestamps verified.
- All five saved models reloaded in a fresh process; held-out metrics reproduced. nflfastR feature matrices were rebuilt from raw play-by-play and matched persisted matrices.
- Live isolated API: NFL and college previews HTTP 200 with normalized probabilities; wrong-league and unknown-team requests HTTP 422. Test server terminated afterward.
- Python compilation and whitespace checks passed. Optional pyflakes was unavailable; no package install was needed.
- Fallow before/after summaries match: two existing dead-code issues, 33 complexity findings and one clone group. Its gate remains failed on pre-existing frontend findings, with a missing root node_modules warning; it does not analyze Python behavior.
- Local credential file is Git-ignored. The actual key is absent from added code and training evidence.

Evidence: `gridiron-training-20261015.json`, `gridiron-verification-20261015.json`, the candidate's `verification.json`, and `gridiron-fallow-{before,after}-20261015.json` in this output directory.
