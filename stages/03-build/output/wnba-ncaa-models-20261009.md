# Independent WNBA and NCAA basketball models

Trained three independent calibrated winner candidates: **WNBA**, **NCAA men's**
and **NCAA women's** basketball. They have separate weights, datasets, scoring
priors, tuning, calibration and test periods. No NBA model weights are reused.

Final run: `20261009T103733107847Z`, under
`pipeline/models/model_store/candidates/sports/`. Production model activation is
unchanged; these models are available through explicit candidate previews.

| Model key | Completed games | Held-out games | Accuracy | Fixed-prior baseline accuracy | Log loss |
|---|---:|---:|---:|---:|---:|
| `wnba` | 1,631 | 278 | 70.86% | 57.91% | 0.6008 |
| `ncaab` | 35,324 | 5,310 | 71.19% | 63.56% | 0.5452 |
| `ncaabw` | 32,757 | 4,869 | 74.94% | 59.75% | 0.4830 |

The baseline is the class-frequency distribution from each model's development
period, evaluated on that model's exact test fixtures. It is not a bookmaker
baseline. These retrospective results do not establish a profitable betting
strategy or an advantage over bookmaker probabilities. Historical odds coverage
is zero for WNBA and NCAA women and two fixtures for NCAA men; none can train a
market expert. All three candidates currently use history features.

## Data and scope

- WNBA: public ESPN yearly scoreboards for 2021–2026, explicitly completed
  franchise games in regular season and playoffs. Preseason, tied/missing final
  scores and future fixtures are excluded. The source includes All-Star events
  labeled regular-season; their `ALLSTAR` competition type is excluded. Legacy
  normalized captures are also filtered by their explicit Team ... roster names.
  Four otherwise eligible All-Star games were removed from training; six All-Star
  source events were identified, including events already excluded by other checks.
- NCAA: seasonal ESPN-derived releases for seasons ending 2021–2026 from
  SportsDataverse, documented by [hoopR's men's schedules](https://github.com/sportsdataverse/hoopR-mbb-data/blob/main/docs/datasets/schedules.md)
  and [wehoop's women's schedules](https://github.com/sportsdataverse/wehoop-wbb-data/blob/main/docs/datasets/schedules.md).
  Only explicitly completed regular-season/postseason games with valid unequal
  final scores are retained. These are source-covered college games, not a claim
  of exhaustive coverage across every NCAA division.
- Direct NCAA annual scoreboard probes were capped at 1,000 records and ignored
  offset/page arguments. Those diagnostic samples remain archived but are replaced
  by seasonal releases in training, avoiding a January-only training cohort.
- Main capture: `pipeline/data/raw/historical/basketball_leagues/20261009T102709967311Z/`.
  Raw JSON/parquet files, source URLs, retrieval times and checksums are preserved.
  `normalized.jsonl` and `manifest.json` provide the import contract. The earlier
  diagnostic capture is retained separately.
- Games are deduplicated by league and provider event ID. There are no conflicting
  score quarantines in the final three datasets. NCAA release records are kept
  separate from legacy odds-provider score IDs to avoid duplicate fixture labels.

Historical final-whistle observation timestamps are unavailable. A conservative
two-day result availability estimate is recorded separately from the actual
historical retrieval time, and only records whose availability estimate has passed
enter training. Future results and same-day results never update earlier features.
These estimates are not represented as exact historical observation timestamps.

## Model behavior

- Independent team/league Elo, recent wins, normalized points scored/conceded,
  margins, rest and recent game load. Score priors: WNBA 80, NCAA men 70, women 65.
- Neutral-court games remove the home Elo advantage in both training and previews.
- Logistic regularization is selected using tuning-period log loss. Refitting uses
  train+tune; sigmoid calibration uses an independent later period. Test results
  do not choose parameters. Both final-score outcomes include overtime.
- NCAA tests cover late 2025 through April 2026. The WNBA final test covers the
  latter part of its 2026 season. Complete split dates and probability/calibration
  metrics are in each candidate's `metrics.json` and the run's `report.json`.
- Each league is now present in its own development data. This replaces the prior
  NCAA test-only transfer evaluation with dedicated trained college models.
- Player injuries, roster changes and transfer information are not features yet.
  Prospective checks and adequate historical bookmaker prices are still needed
  before activation or claims about betting value.

The earlier diagnostic run `20261009T103029485354Z` included otherwise eligible
All-Star games in WNBA and is superseded by the final run above.

## Commands

From `pipeline/`, fetch source history and build independent candidates:

```powershell
py -3 -m etl.fetch_basketball_history
py -3 -m models.train_sports --sports wnba ncaab ncaabw
```

Preview a specific saved WNBA model:

```powershell
py -3 -m models.sport_predict --candidate-id 20261009T103733107847Z --sport wnba --league basketball_wnba --home "New York Liberty" --away "Las Vegas Aces" --kickoff 2026-10-20T00:00:00Z
```

NCAA men's uses `--sport ncaab --league basketball_ncaab`; women's uses
`--sport ncaabw --league basketball_wncaab`. Add `--neutral-site` for tournaments
or other neutral-court previews. Kickoff must be after the candidate's training
time. Team names must match known history for that exact league.

`POST /api/v1/sport-models/preview` accepts these same model and league keys and
`neutral_site: true/false`. `GET /api/v1/sport-models` lists candidate runs. Cross-
league requests are rejected. Saved datasets and models remain checksummed and
ignored by Git; no original source captures or active artifacts were replaced.

## Verification

59 behavioral tests passed, including completed-game filtering, league/gender
isolation, neutral sites, historical import checksums, All-Star exclusion and
replacement of truncated annual samples. Models reload in fresh processes;
WNBA, NCAA men and NCAA women have been checked through live preview endpoints.
The live smoke command is:

```powershell
py -3 scripts/smoke_sport_models.py --candidate-id 20261009T103733107847Z --basketball-leagues
```

It verifies three HTTP 200 predictions and a cross-league HTTP 422 response.
The isolated API is stopped after validation. Compilation and whitespace checks
passed. The root Fallow audit passed with no introduced findings, retaining its
missing root node_modules warning and inherited JavaScript findings; Python
behavior is verified separately by training, tests and saved-model predictions.
