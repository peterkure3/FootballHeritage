# NFL history and candidate validation

## Latest trained model

At the user's request, the selected history recipe was refitted as of November 1
in `pipeline/models/model_store/research/nfl_trained_20261101/`. The base model
uses 3,284 decisive games from seasons 2014–2025; 107 available 2026 games are
reserved for sigmoid calibration. Twelve ties remain only in feature history.
C=1.0 is frozen from the prior selection, with no new outcome-driven search.

`model.pkl` uses the existing 20-column sport-model input schema and history-only
routing. `metadata.json` records hashes, cutoff, partitions and limitations;
`verification.json` records independent reload/probability checks. The model is
inactive and outside the serving catalog. No production change, staging or
commit occurred. Its 2026 labels are now calibration data: the validation scores
below belong to the earlier pre-2026-trained artifact, not this latest refit.
It needs new independent results for performance evaluation.

Performance evaluation is recorded in
`stages/04-test/output/nfl-refit-performance-20261101/summary.md`. Historical
walk-forward replicas scored 679/1,044 (65.04%) versus 686/1,044 (65.71%) for
preseason comparators, with worse log loss/Brier. This evaluates the procedure,
not the actual November 1 artifact. Fourteen prospective predictions for that
artifact are frozen; none is settled at the initial assessment. Use
`scripts.assess_nfl_refit --trial ../stages/04-test/output/nfl-refit-performance-20261101`
from `pipeline/` after games finish. Thirty-four affected tests and independent
replica/forecast replays passed. No performance-based promotion is supported.

From `pipeline/`, reproduce with a new output directory:

```powershell
py -3 -m models.train_nfl_asof --recipe models/model_store/research/nfl_expanded_20261101 --calibration-from-season 2026 --output models/model_store/research/nfl-refit-new
```

One new split/cutoff test and ten existing sport-model tests passed for this refit.

The NFL research pipeline now has a verified 2014–2026 play-by-play corpus,
cached processing, season-based selection and an explicit reserved-season check.
Production serving and the active model registry are unchanged. Nothing from
this experiment was staged or committed.

## Data and artifacts

- Raw capture: `pipeline/data/raw/historical/nfl_accuracy_20261101/`.
  nflverse schedules plus 13 play-by-play parquet files; 14 verified inputs,
  no collection failures. Three older files were reused with their original
  retrieval metadata and verified hashes. Current-season data is partial.
- Prepared snapshot: `pipeline/data/processed/nfl_accuracy_20261101/`.
  3,403 completed games, all with both teams' play-by-play aggregates. Twelve
  ties remain in history. Cached aggregates and the 26-column feature matrix
  have source/file checksums.
- Candidate: `pipeline/models/model_store/research/nfl_expanded_20261101/`.
  `selection.json`, a frozen history estimator, development predictions,
  validation/reference reports, paired 2026 predictions and verification receipt.
- Shareable score exports: candidate `audit/nfl_score_history.csv` and `.parquet`.
  7,125 normalized score records from 2000–2026. The play-by-play corpus has
  598,931 raw play rows. Score exports omit archival betting prices.

Native fixture IDs are unique; source normalization handles franchise renames,
Eastern kickoff times/DST, neutral sites, incomplete games and ties. All source
and artifact checks are reproducibility checks, not proof that upstream data is
perfect. Historical score/PBP availability assumes two UTC days after the game
date; archived observation/revision receipts are unavailable. Quote observation
times are absent, so archival odds are excluded from these models.

## Efficiency

`models.nfl_history` verifies raw hashes and caches team-game aggregates keyed by
the play-by-play file hashes. Changed inputs invalidate the cache; changed cache
bytes fail verification. It explicitly normalizes text-column types for a stable
Parquet round trip. In this run raw aggregation took 1.570 s and cached loading
0.017 s, about **91× faster for aggregation**. This excludes initial source-hash
verification and is not an end-to-end pipeline speed claim.

Feature construction took 14.715 s once; development folds reuse its verified
matrix. Within each fitting fold, C candidates share a train-only scaler; the
chosen estimator is refitted on train+tune with a new scaler, then calibrated
separately. This optimized recipe matches the existing fitting recipe, rather
than sharing preprocessing across folds.

On the same 107-row prediction batch, the frozen reference's median was 8.765 ms
and the refreshed model's 4.307 ms (10 repetitions each, two training/runtime
threads). Artifact sizes were 3,440 and 3,280 bytes. These local timings depend
on environment/load; they are not a universal latency guarantee. The candidate
is a bare calibrated history estimator with 16 named inputs, not the reference's
20-column sport-routing wrapper. A serving adapter would need to honor that
contract; none was introduced.

## Stronger validation

Six expanding test seasons, 2020–2025, compare history (16 features), full
efficiency (26), compact history differences (5), and compact efficiency (10).
For test season Y: train before Y−1, tune on weeks 1–9 of Y−1, calibrate on its
remaining weeks, then test on Y. Labels unavailable at the next partition are
purged. Every arm scores identical targets. NFL ties remain in history and are
excluded from winner labels: probabilities are conditional on no final tie;
overtime is included and final ties void for winner scoring.

The fixed C grid is [.01, .1, 1.]. Candidate selection uses development log loss,
accuracy, Brier score and consistency across seasons. The decision and model
hashes were saved before evaluating 2026. No alternative passed all gates, so
the 16-feature history recipe was retained.

| Development, 1,688 paired targets | Accuracy | Log loss | Brier |
|---|---:|---:|---:|
| History | 64.159% | 0.642590 | 0.449762 |
| Full efficiency | 64.336% | 0.643812 | 0.451061 |
| Compact history | 64.336% | 0.642498 | 0.450319 |
| Compact efficiency | 64.218% | 0.642947 | 0.450320 |

Reserved 2026 has 107 decisive targets across eight NFL weeks (one tied game is
not scored). The pre-existing reference retains its 2000-start historical state;
only later games are appended. Overlaps must agree on native ID, teams, kickoff,
score and neutral-site policy. Its original 900-test-game metrics replay before
comparison. No refreshed history is silently fed through its old model.

| 2026 retrospective comparison | Correct | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| Frozen reference | 61/107 | 57.009% | 0.652876 | 0.463489 |
| Refreshed history | 61/107 | 57.009% | 0.649499 | 0.460286 |
| Train+tune prior | 53/107 | 49.533% | 0.699784 | 0.506601 |

Paired uncertainty resamples entire NFL season/week blocks (2,000 draws, seed
42), rather than treating games as independent. Refreshed-minus-reference
accuracy is 0 points, 95% interval approximately −5.71 to +5.74 points. Log-loss
difference −0.003377 has interval [−0.015662, +0.005685]. Brier difference
−0.003202 has interval [−0.014857, +0.005680]. None establishes a reliable gain.
The 10-bin home-win calibration diagnostic worsened from 0.0867 to 0.1111;
small-bin estimates on 107 targets are noisy. It was not a selection criterion.

Reports include weekly/season-type breakdowns and a seven-day availability
stress using fixed two-day-trained models, without refitting/retuning. The 2026
season was excluded from this selection, but earlier broad reports included some
2026 outcomes, so this is retrospective, not fresh prospective validation. The
comparison changes training/calibration freshness and data window together.
Bootstrap intervals omit complete team/cross-week dependence and model-selection
uncertainty. No accuracy improvement, profitability or promotion is claimed.

## Reproduction and checks

Run from `pipeline/`. Use new output directories to preserve frozen artifacts:

```powershell
py -3 -m etl.fetch_gridiron_sources --source nfl --pbp-years 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026 --output-dir data/raw/historical/nfl-new-capture
py -3 -m models.nfl_history --capture data/raw/historical/nfl-new-capture --output data/processed/nfl-new-history
py -3 -m models.nfl_season_validation train --data data/processed/nfl-new-history --output models/model_store/research/nfl-new-candidate
py -3 -m models.nfl_season_validation validate --output models/model_store/research/nfl-new-candidate
py -3 -m scripts.validate_nfl_2026_reference --reference models/model_store/candidates/sports/20261015T194812812329Z/nfl --candidate models/model_store/research/nfl-new-candidate
py -3 -m scripts.audit_nfl_candidate --capture data/raw/historical/nfl-new-capture --candidate models/model_store/research/nfl-new-candidate
```

The collector reuses matching cached files, so use a fresh timestamped capture
directory to refresh schedules/current-season assets. Never label a cached file
as newly downloaded. Later source updates may produce different results; the
original snapshot and verification receipt preserve the measured experiment.

Thirty-one local focused/regression tests passed, including source/cache
integrity, cache invalidation, week/season splits, label purging, calibration
exclusion, fitting equivalence, weekly bootstrap dependence, reference-state
preservation and prior-baseline leakage/zero-total rejection. Existing CI's
unittest discovery includes these tests; remote CI was not run. Python compile
and whitespace checks passed. Fallow and pyflakes were unavailable. The local
Parquet engine is recorded in `verification.json`; optional PyArrow is not
required when a working alternative engine is installed.
