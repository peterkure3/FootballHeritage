# Prediction model milestone 1

The v2.1 trainer builds isolated candidates. Its default strategy selects separately
calibrated market and history experts; `--strategy stacking` retains the previous
temporal stack for comparison. It does not overwrite or activate the
existing v2.0 model. Serving retains the old feature contract for that old artifact.
Candidate artifacts use the shared causal v2.1 feature builder when explicitly
activated through `MODEL_VERSION=2.1.0`.

From `pipeline/`:

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m models.train_model_v2 --dry-run
py -3 -m models.train_model_v2 --trees 200 --threads 2
py -3 -m models.train_model_v2 --strategy stacking --trees 200 --threads 2
py -3 -m models.evaluate --bundle models/model_store/candidates/<run-directory>
py -3 -m models.backtest --trees 200 --threads 2 --folds 3 --output models/model_store/candidates/<run-directory>/rolling_evaluation.json
py -3 -m models.import_historical --input <licensed-export.csv> --competition "Premier League" --season 2425 --provider <licensed-provider>
```

## Data and feature contract

- Slash-separated historical dates are day-first. ISO timestamps retain UTC time.
- Fixtures are deduplicated after parsing by UTC day and explicit team identities.
  Different same-day fixtures with the same teams are ambiguous and receive no
  joined offers. Matching never uses team-name substrings.
- Original historical files take precedence over normalized copies. Sample and
  synthetic files are excluded. Inconsistent final scores and outcome labels fail
  the run. Historical file-local IDs are not treated as provider match IDs.
- Only the latest cumulative processed snapshot is loaded. Its old team-only odds
  joins are discarded; historical B365 prematch columns supply the odds features.
  Historical columns do not establish an exact odds observation time: performance
  at a particular prediction horizon requires timestamped archived offers.
- New ETL joins use fixture day, team identities, and offers timestamped before
  kickoff. The latest valid three-way offer per bookmaker supplies the average.
- Results become available to features on the following UTC day. This conservative
  rule handles historical date-only records without guessing match finish times.
- Weighted form uses the last 10 completed matches with decay 0.9; original form
  uses 5; venue statistics use 20 with at least 5 observations; H2H uses 10.
  Training, replay, and candidate serving share these exact definitions.
- Missing/invalid odds use a consistent prior plus an explicit `odds_missing`
  feature. No fabricated odds count toward the market comparison.

## Evaluation contract

Distinct match days are partitioned chronologically: 60% training, 15% tuning,
10% calibration, 15% test. Same-day matches stay together. Stacking trains its
meta-learner on predictions from expanding chronological folds, then refits base
models on development data. The initial tuning report uses only the training
period; the final model uses train+tune. Sigmoid calibration uses only its separate
period. The final test period is untouched by fitting and calibration.

The default odds-aware strategy selects each expert independently from standardized
logistic regression (`C=0.01, 0.1, 1.0`) and a regularized histogram gradient booster.
Selection minimizes tuning-period log loss. Each selected expert is refit on
train+tune and sigmoid-calibrated on the separate calibration period. The history
expert excludes all odds-derived features and the missing-odds flag, while the market
expert uses only fixtures with observed odds for fitting, tuning, and calibration.
Inference routes by `odds_missing`; no test labels enter model selection. Training
fails explicitly if a market-selection period lacks observed odds for all classes.
Manifests preserve every candidate's tuning scores and report missing-odds test
metrics separately. Native fitting thread pools respect `--threads`.

Each candidate contains the model, encoder, feature list, metrics, and a frozen
canonical dataset with a SHA-256 checksum. Evaluation rebuilds the same features
and checks the dataset and feature contract before reproducing test metrics.
Reported metrics include log loss, multiclass Brier score (sum across classes),
accuracy, class calibration bins, confusion matrix, and competition breakdowns.
Market and model comparisons use exactly the same fixtures with complete odds.

The rolling evaluator fits a fresh model in each expanding window, reserving the
last 20% of development days for calibration and testing on the next date block.
With odds-aware selection, the preceding 20% is reserved for tuning. The stacking
strategy retains temporal out-of-fold fitting. Reports save separately and never
activate a model.

## Licensed historical imports

The importer accepts raw football-results CSVs or the canonical column schema.
It validates dates, team identities, final scores, outcome labels, and fixture
uniqueness, preserves the supplied provider and competition provenance, and uses
exclusive file creation to protect previous imports. It rejects sample files and
unfinished or duplicate fixtures. Season is a filename label, not a substitute for
the actual match dates. The imported data's usage rights must cover the intended
training and product use.

New downloads remain pending by user choice. The existing Football-Data.co.uk
downloader was not run: its [current usage terms](https://www.football-data.co.uk/data.php)
exclude commercial and AI-training use. No paid API requests were made.

## Serving and activation

The matchup API delegates to the batch prediction service and preserves its response
schema. It reports that hypothetical matchups lack a live market. Batch predictions
use the latest valid quote per bookmaker, and the daily fetch-and-sync script now
generates active-model predictions before syncing them.

The weekly trainer now produces a candidate rather than replacing production.
Review test log loss, calibration, odds coverage, and league breakdowns first.
Before activation, validate candidate serving against the local database and keep
the old bundle for rollback. Copy the reviewed model, encoder, features, and metrics
files into `models/model_store/`, set `MODEL_VERSION=2.1.0`, and restart the service.
Do not carry over a scaler from another bundle. This workflow does not claim that a
candidate beats the market or is profitable simply because training completed.

## Odds-aware candidate results (2026-10-08)

The auditable bookmaker comparison demo is generated with:

```powershell
py -3 -m models.market_demo --bundle models/model_store/candidates/20261008T170059291611Z --output-dir ../stages/03-build/output/bookmaker-demo
```

Choose a new output directory when rerunning; existing reports are protected from
overwriting. `demo.html` includes matched probability metrics, paired fixture-day
bootstrap intervals, a fixed 5% expected-return flat-stake simulation, and all
108 compared fixtures. CSV and JSON exports retain full probabilities and evidence.
The simulation returned 10.62 units on 80 bets (13.28% ROI), but its 95% day-bootstrap
ROI interval spans -38.83% to +72.24%. Probability-score intervals also span zero.
This does not establish a repeatable advantage over bookmaker probabilities.

Candidate `20261008T170059291611Z` and the prior 200-tree stacking candidate
`20261008T121429205367Z` have identical frozen dataset checksums. On the same 1,260
future fixtures, accuracy improved from 33.97% to 50.08%, log loss from 1.3215 to
1.0086, and Brier score from 0.7474 to 0.6034. Both experts selected logistic
regression with `C=0.01`. The 1,152 fixtures without odds scored 49.13% accuracy and
1.0178 log loss. The market expert's log loss on 108 odds-backed fixtures was 0.91025
versus the bookmaker baseline's 0.91010; this is no demonstrated market advantage.

Rolling-window accuracy improved from 51.54/53.88/44.29% to 53.16/54.17/51.08%;
log loss also improved in all three windows. Selection uses each window's own
tuning period. These historical windows were already inspected in earlier work,
so these are retrospective development comparisons, not a fresh final acceptance
test. Reserve a new future period before production promotion. The active v2.0
bundle and predictions were not changed. Full results and source changes are
recorded in `stages/03-build/output/odds-aware-prediction-model.md`.

Remaining work: backfill recent seasons and timestamped odds, broaden alias coverage
with provider IDs, integrate strictly lagged xG, evaluate alternative model families,
add betting simulations, further improve performance without odds, and automate promotion.
