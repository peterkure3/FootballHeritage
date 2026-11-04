# Prediction model milestone 1 — 2026-10-08

Implemented fixture/data repair, a shared causal candidate feature pipeline, and
chronological evaluation. The existing active model remains v2.0.0. New v2.1.0
training outputs are isolated candidates; training no longer replaces production.

## Changes

- Canonical date parsing before fixture deduplication; explicit team aliases rather
  than substring matches; sample exclusion; original historical files preferred over
  normalized copies; preservation of completed results over partial snapshots.
- Odds matched to an unambiguous fixture day with prematch timestamps. Live inference
  averages the latest valid quote from each bookmaker. Old snapshot odds joins are
  excluded from candidate training.
- Shared Elo, exponentially weighted form, five-match form, 20-match venue history,
  and ten-match H2H features; results become available on the following UTC day.
  Missing odds are explicit and use the same defaults during training and serving.
- Chronological 60/15/10/15 train/tune/calibration/test periods, chronological
  out-of-fold stacking, independent sigmoid calibration, probability scoring,
  class calibration bins, and competition/market comparisons.
- Candidate bundles preserve a frozen dataset and checksum. Evaluation reproduces
  held-out metrics independently. Complete-model rolling evaluation is available.
- Matchup API delegates to the batch service, with artifact schema/count guards.
  Daily ingestion now generates predictions before backend sync; incomplete batches
  fail rather than silently syncing stale predictions.
- Licensed-export importer validates completed fixtures and preserves provenance,
  rejects samples and duplicates, and refuses to overwrite existing imports.

## Verification

- 17 behavioral tests pass via `py -3 -m unittest discover -s tests -v`.
- Pipeline syntax compilation and scoped `git diff --check` pass.
- Real local PostgreSQL read and latest-quote upcoming-fixture query pass (9 fixtures).
- Temporary Uvicorn server: `/api/v1/predict-matchup?home_team=Arsenal&away_team=Chelsea`
  returns HTTP 200 with active model v2.0.0 and probabilities summing to one.
- Read-only candidate inference produces finite normalized probabilities for all 9
  upcoming fixtures. No predictions were saved and no active artifact was replaced.
- Full 200-tree candidate trained successfully; independent frozen evaluation
  reproduces every saved metric within 1e-12 (largest difference 2.78e-17).
- Three complete-model rolling evaluations (200 trees, 2 threads) finish successfully.
  Candidate artifacts and frozen data are confirmed gitignored.

## Candidate evidence

Bundle: `pipeline/models/model_store/candidates/20261008T101609223478Z/` (gitignored).

| Measure | Result |
|---|---|
| Completed canonical fixtures | 10,107 |
| Fixtures with historical odds | 8,950 |
| Training / tuning / calibration / test | 6,202 / 1,726 / 919 / 1,260 |
| Test period | 2024-05-12 through 2026-09-20 |
| Test accuracy | 33.97% |
| Test log loss | 1.3215 |
| Test multiclass Brier score | 0.7474 |
| Test fixtures with odds | 108 of 1,260 |
| Model accuracy on odds-covered subset | 62.96% |
| Market accuracy on the same subset | 59.26% |
| Model / market log loss on the same subset | 0.9090 / 0.9101 |

This small odds-covered subset does not establish a betting edge or justify
activation. Most of the future test fixtures lack odds, creating a distribution
shift from the historical training corpus. The previous random-split calibrated
accuracy is not a valid comparison with this held-out future evaluation.

## Rolling evidence

The complete ensemble is fitted and independently calibrated anew in each expanding
window. Market comparisons use only fixtures with complete odds in that window.

| Future period | Test fixtures | Overall accuracy | Model log loss on odds-covered fixtures | Market log loss on same fixtures |
|---|---:|---:|---:|---:|
| 2021-01-02 to 2022-04-20 | 2,662 | 51.54% | 1.0052 | 0.9711 |
| 2022-04-21 to 2023-12-10 | 2,806 | 53.88% | 0.9788 | 0.9698 |
| 2023-12-11 to 2026-09-20 | 2,179 | 44.29% | 0.9737 | 0.9620 |

Lower log loss is better. The candidate does not beat the market baseline in any
rolling window. These results reinforce keeping it inactive. Full metrics are in
the bundle's `rolling_evaluation.json`. No hyperparameters were tuned against these
results; subsequent experiments require a separately reserved final evaluation.

## Remaining work and limits

The user selected "Finish import tooling; leave licensed backfill pending".
Recent-season and timestamped odds backfill remains pending until an appropriate
source/export is provided. The existing external downloader was not run. Historical
B365 columns do not establish a precise prediction horizon. Broader provider team
identity mappings, robust performance without odds, lagged xG integration, betting
simulation, and automated promotion remain future work.

CI configuration was updated; remote CI was not run. Daily fetching/database writes
and deployment were not executed. Existing unrelated backend edits were preserved.
This deliverable does not advance or sign off the overall stage gate.
