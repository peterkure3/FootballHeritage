# Reproducible ML research

## Accuracy workstream (2026-10-31)

`models.accuracy_research` runs fixed history-only development experiments,
including an `--identities` arm using existing reviewed names. All archived odds
are excluded. These experiments explicitly use the inherited next-day result
availability assumption and do **not** pass the stricter verified-provenance
contract below. `scripts.validate_identity_accuracy` performs a separately frozen
retrospective comparison, preserving active models and registries. The first
identity candidate improved accuracy from 48.26% to 49.63% on 1,894 paired matches;
the reused holdout prevents a fresh-confirmation claim. See
`stages/03-build/output/accuracy-progress-20261031.md` for rejected experiments,
uncertainty, saved artifacts, tests and next work. Nothing was staged or committed.

These tools implement the October 23/30 research brief as experiments. They do
not publish models, change registries, or assert that a technique improves sports
prediction. Existing football/sport feature builders and trainers remain active.

## Availability contract

`models.feature_availability` requires explicit UTC-aware kickoff and forecast
cutoff timestamps. Prematch cutoffs precede kickoff; live cutoffs start at kickoff.
Each materialized feature needs its definition, source URL, raw snapshot SHA256,
verified `available_at`, `aggregation_cutoff`, and kind (`snapshot` or `rolling`).
Rolling features additionally declare every contributing game, kickoff, verified
result availability, and game ID. Cold starts use an empty dependency list.
The validator rejects current/future games and late or unknown inputs.

Retrieval timestamps establish when we captured a file. They do **not** establish
historical availability of its contents. Existing `CONSERVATIVE_TWO_DAYS` and
next-day policies remain assumptions: do not relabel them as verified. Existing
archive odds lack verified observation times and remain unsuitable for strict
prematch experiments. Unknown inputs must be excluded or separately labeled in a
sensitivity analysis. Do not synthesize historical timestamps to pass the gate.

## Controlled experiment command

From `pipeline/`:

```powershell
py -3 -m models.research_experiments --input research-input.json --output research-runs/run-001.json --seed 42 --trees 200
```

The input JSON contains:

- `classes`: ordered outcome names; `target` is their zero-based index.
- `snapshots`: `path` (relative to input), `sha256`, `source_url`, `retrieved_at`.
  Every snapshot is rehashed before training.
- `feature_groups`: disjoint column lists with required `basic`, and optional
  `opponent_adjusted`, `schedule_strength`, or `players` groups.
- `feature_definitions`: exact definitions keyed by column name.
- `rows`: globally unique `game_id`, `kickoff`, `cutoff`, `competition`, `season`,
  `target`, verified `target_available_at`/`target_availability_status`, numerical
  `features`, and `provenance` keyed by feature. Null is explicit missingness.
- Optional `stale_features` and `stale_provenance` on each test row: genuine
  earlier snapshots under the same definitions. No fabricated staleness.

`tests/test_research_safeguards.py::synthetic_dataset` supplies a complete schema
example, solely for verifying program behavior. A data adapter must derive
features with the existing builders and supply verifiable dependency records.
The gate cannot independently prove the truth of an adapter's source claims.

Each competition is isolated. The existing 60/15/10/15 date-blocked split reserves
the final 15% as the future holdout. Three expanding walk-forward evaluations run
inside development only. Training labels must be available before the next
evaluation cutoff. Preprocessing fits only on each training fold. Fixed-budget
logistic, LightGBM and XGBoost candidates compare basic features with **one** added
group at a time. Optional missing packages are reported, never substituted.
There is no calibration or ensemble weight fitting in this runner; existing
production trainers retain their separate calibration period.

The report records input/snapshot hashes, definitions, cutoffs, split dates and
game IDs, package versions, seeds, estimator configuration, per-season sample
sizes, log loss, summed multiclass Brier score, classwise calibration bins, and
individual holdout probabilities. Missing-group and multiplicative corruption
tests report probability degradation relative to clean input. Logistic uses
training-only median imputation; tree models use their missing-value handling.
Stale tests run only with verified earlier snapshots for every test row.

An improvement flag compares both test log loss and Brier with basic logistic.
It is descriptive, without a significance claim or promotion recommendation.
Repeated use consumes a holdout; preregister the next experiment and reserve a
new future period before changing models based on results. Real Elo probabilities
or an Elo-only logistic feature group can be supplied from the existing builders;
do not treat football Elo expected points as three-way outcome probabilities.

## Basketball PBP audit

```powershell
py -3 -m etl.audit_basketball_pbp --events-url <exact-parquet-url> --schedule-url <exact-parquet-url> --mapping mapping.json --output-dir data/raw/historical/nba/new-run
```

The mapping has `events` and `schedule` objects, each canonical-name -> provider
column. Events require `game_id`, `event_id`, `sequence`, `period`,
`clock_seconds` (total quarter seconds remaining), `home_score`, `away_score`.
Schedules require `game_id`, `date`, boolean `completed`, and final scores.
For the inspected hoopR ESPN asset use `game_play_number` for sequence,
`period_number` for period, and `start_quarter_seconds_remaining` for the clock;
the provider's `clock_seconds` is just the seconds component of its clock.

Raw bytes, retrieval time, URL, response metadata, hashes and mapping persist
before normalization. The audit checks duplicate IDs, source order, period/clock
validity, score progression, opening/terminal events, final scores and coverage
relative to the supplied completed schedule. It never sorts away ordering defects.
Clock rules currently cover NBA only. Missing intermediate events can escape
these structural checks. Semantic possession validation, player/team crosswalks,
substitution/lineup review, and independent schedule completeness remain required.
`possession_reconstruction_approved` stays false even if structural checks pass.

The dated NBA pilot scripts/report in `stages/03-build/output/` demonstrate actual
asset inspection; their raw inputs live in the pipeline raw-data directory.

## Monte Carlo output

`models.simulation_metrics` scores paired home/away final scores. The existing
soccer evaluator now persists every final-score pair, margin and total CRPS,
80/90/95% intervals, observed coverage, tail quantiles and conditional Monte Carlo
standard errors. Aggregate results include interval coverage and direct Poisson
baseline CRPS. Existing winner log loss/Brier remain available. Basketball can
reuse this scorer once a validated simulator exists.

Sampling error assumes independent runs conditional on a fitted model. It does
not quantify parameter, structural, or distribution-shift uncertainty. Coverage
must be aggregated over independent held-out games with sample counts and season
labels; one game's interval does not establish calibration. No conformal coverage
guarantee is claimed.
