# NBA training results

This goal turn produced a research candidate with better retrospective metrics.
Production models, active registry, datasets and serving paths are unchanged.
Nothing staged or committed. The goal remains active: prospective accuracy
evidence is still needed. No profitability conclusion is supported.

## Development selection

Three expanding date folds excluded all fixtures on or after January 14, 2025.
Training and calibration labels were purged at their next partition boundaries.
All models used identical history features, except the explicit inactivity policy.
The last 20% of development days calibrated each model using sigmoid calibration.

| Fixed configuration | Paired predictions | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| Logistic C=0.1 baseline | 5,220 | 64.061% | 0.634786 | 0.444205 |
| Training weights, 730-day half-life | 5,220 | 63.755% | 0.635042 | 0.444470 |
| Small gradient boosting | 5,220 | 61.245% | 0.656639 | 0.464534 |
| Inactivity reset + baseline logistic | 5,220 | 64.387% | 0.632777 | 0.442436 |

Recency weighting and gradient boosting were rejected. The separately predeclared
inactivity follow-up clears rolling history after 90 days without an available
result and regresses Elo halfway toward 1500. It gained 17 correct predictions;
fold accuracy improved in two folds and tied in the third. Both experiment files
contain exactly identical baseline predictions. Their last scored development
fixture is January 13, 2025.

The threshold and regression amount were fixed before execution, with no sweep.
Multiple experiments were selected on these development folds; their scores are
selection evidence, not independent confirmation. Coverage is uneven, including
only 67 records dated 2020. The reset can respond to missing source history as
well as true inactivity, and does not establish knowledge of roster changes.

## Frozen retrospective validation

The policy was frozen in `accuracy-nba-inactivity-validation-plan-20261101.md`
before evaluating the original 1,089 reserved fixtures. Original final-test
metrics had already been inspected, so this is retrospective validation.
The candidate uses the original fixed C=0.1 and exact saved train+tune and
calibration partitions; no test-period retuning occurred.

| Model | Accuracy | Log loss | Brier |
|---|---:|---:|---:|
| Original frozen NBA model | 64.371% | 0.632703 | 0.441262 |
| Frozen inactivity candidate | 65.014% | 0.624121 | 0.434421 |

The candidate made seven more correct predictions. Paired differences, with
2,000 UTC-match-day bootstrap resamples, seed 42:

- Accuracy: +0.643 percentage points; 95% interval **−0.774 to +2.014 points**.
- Log loss: −0.008582; 95% interval **−0.014187 to −0.002463**.
- Brier: −0.006841; 95% interval **−0.011671 to −0.001798**.

The accuracy interval includes zero. Probability metrics look promising, but
these intervals do not include all cross-day dependence or model-selection
uncertainty. This does not establish a future accuracy gain or justify promotion.

Artifact: `pipeline/models/model_store/research/accuracy_nba_inactivity_20261101/`
contains a history-only pickle, report, paired predictions and replay verification.
Its input contract is `nba-inactivity-90-50-research-1.0`; using the existing
production features with this pickle would violate the experiment. Do not load
it into the active sport-model registry. The existing NBA freshness trial tests
a different hypothesis with identical weights and ordinary features; its results
cannot be counted as prospective confirmation for this new candidate.

## Checks and reproduction

Twenty-three tests passed across the new NBA research tests and existing
sport-model and basketball suites. They cover delayed-label purging, unfitted
preprocessing exclusion of calibration rows, fixed recency weights, unchanged
ordinary features and exclusion of current/same-day/future scores. A same-day
test initially used fixtures that canonicalization correctly deduplicated; it
was corrected to use distinct opponents and then passed.

The original frozen model's three metrics replayed to 1e-12 before comparison.
The independent verification refits the baseline recipe and restores the saved
candidate, checking their paired probabilities against the recorded CSV to
1e-12. Source/model hashes are recorded. Python compilation and diff whitespace
checks passed; the staging area is empty. Fallow is unavailable.

From `pipeline/`, use new output directories to reproduce:

```powershell
py -3 -m models.nba_accuracy_research --bundle models/model_store/candidates/sports/20261015T163645187197Z/basketball --output ../stages/04-test/output/nba-training-replay
py -3 -m models.nba_accuracy_research --bundle models/model_store/candidates/sports/20261015T163645187197Z/basketball --output ../stages/04-test/output/nba-inactivity-replay --inactivity
py -3 -m scripts.validate_nba_inactivity_accuracy --bundle models/model_store/candidates/sports/20261015T163645187197Z/basketball --output models/model_store/research/nba-inactivity-validation-replay
py -3 -m unittest discover -s tests -p test_nba_accuracy_research.py
```

Next: record a separate prospective paired trial for this exact frozen feature
policy and model, with the same available input history in both arms. Continue
the already frozen soccer and NBA freshness studies without mixing hypotheses.
