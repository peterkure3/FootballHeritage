# Odds-aware prediction candidate — 2026-10-08

## Outcome

Addressed missing-market distribution shift: only five of 6,202 training fixtures
lacked odds, compared with 1,152 of 1,260 held-out fixtures. The former temporal
stack consequently made poor forecasts when supplied its missing-market prior.

The default trainer now selects separate market and history experts. Each searches
three regularized logistic configurations and one regularized histogram gradient
booster using only tuning-period log loss. Selected experts refit on train+tune
and calibrate separately on the calibration period. The history expert excludes
all market features; the market expert uses observed prices only. Predictions route
by odds availability. The shared 39-feature v2.1 input contract remains compatible
with candidate serving. `--strategy stacking` retains the earlier implementation.

## Reproducible candidate

Bundle: `pipeline/models/model_store/candidates/20261008T170059291611Z/` (ignored).
Both selected experts: standardized logistic regression, `C=0.01`.
Model version: 2.1.0; feature schema: 2.1.0; status: candidate.

Run from `pipeline/`:

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m models.train_model_v2 --trees 200 --threads 2 --strategy odds-aware
py -3 -m models.evaluate --bundle models/model_store/candidates/20261008T170059291611Z
py -3 -m models.backtest --strategy odds-aware --trees 200 --threads 2 --folds 3 --output models/model_store/candidates/20261008T170059291611Z/rolling_evaluation.json
py -3 -m compileall -q models tests
```

Training generates a new timestamped bundle; rolling output uses exclusive creation.

## Historical comparison

The new bundle and earlier 200-tree candidate `20261008T121429205367Z` have
identical frozen dataset SHA-256 checksums. These results compare candidates under
the same chronological splits; old v2.0 random-split metrics are not comparable.

| Metric, 1,260 future fixtures | Earlier stack | Odds-aware candidate |
|---|---:|---:|
| Accuracy | 33.97% | 50.08% |
| Log loss (lower is better) | 1.3215 | 1.0086 |
| Multiclass Brier score (lower is better) | 0.7474 | 0.6034 |

Without odds: 1,152 fixtures, accuracy 49.13%, log loss 1.0178.
With odds: 108 fixtures, accuracy 60.19%, log loss 0.91025.
Matched bookmaker baseline: accuracy 59.26%, log loss 0.91010.
This candidate has not demonstrated better probability quality than the market.

| Rolling future window | Earlier accuracy | New accuracy | Earlier log loss | New log loss |
|---|---:|---:|---:|---:|
| 2021-01-02 to 2022-04-20 | 51.54% | 53.16% | 1.0057 | 0.9939 |
| 2022-04-21 to 2023-12-10 | 53.88% | 54.17% | 0.9788 | 0.9758 |
| 2023-12-11 to 2026-09-20 | 44.29% | 51.08% | 1.0599 | 0.9952 |

Each window fits, selects, and calibrates using its own prior date periods. Existing
historical test results informed this engineering investigation; these comparisons
are retrospective development evidence. A newly reserved future period is needed
for final acceptance. No production activation or profitability claim follows.

## Verification

- All 28 Python behavioral tests passed, including six new checks for routing,
  odds-input independence, test-label isolation, serialization, feature order,
  missing-market training failure, and rolling model selection.
- Frozen-dataset evaluation reproduced the saved candidate's accuracy, log loss,
  and Brier score exactly. Python compilation passed.
- The saved candidate produced finite probabilities summing to one for all 28
  upcoming fixtures returned by the current serving query. All lacked observed
  odds and used the history expert. This exercised the existing feature-serving
  path with an enforced read-only PostgreSQL connection; no stored predictions
  changed. Results are saved as `serving_smoke.json` inside the candidate bundle.
- Fallow's initial and final root audits passed with zero newly introduced dead-code,
  complexity, or duplication findings. Its missing-root-node_modules warning
  limits JS dependency accuracy; Fallow does not establish Python model correctness.
  Python correctness is covered by the behavioral and artifact checks above.
  `git diff --check` also passed.

## Scope and next work

Changed `models/selection.py`, `models/train_model_v2.py`, `models/backtest.py`, and
`tests/test_model_selection.py`. Updated the model runbook and codebase index.
Existing unrelated workspace changes were preserved. The active v2.0 artifact,
model configuration, stored predictions, and backend RAG settings remain unchanged.
No external data download or paid data API calls were made.

Next: licensed recent-season and timestamped odds coverage; broader explicit team
identities; a fresh future acceptance period; class calibration and league-specific
evaluation; deployment review with rollback. This deliverable does not sign off or
advance the overall stage gate.
