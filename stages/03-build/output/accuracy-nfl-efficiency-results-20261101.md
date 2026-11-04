# NFL efficiency experiment: rejected

The existing efficiency features did not improve the paired reserved-period
results. Keep the efficiency artifact research-only and inactive. Production
and active registry are unchanged; nothing staged or committed. The accuracy
goal remains active through the frozen soccer/NBA prospective studies.

## Paired development comparison

Raw nflfastR sources were hash-verified, rebuilt, and matched the saved 855-game
feature matrix to 1e-12. All fixtures on/after November 23, 2025 were excluded
from development selection. Three expanding folds used nested tuning and
calibration blocks, with labels purged at each boundary. Both arms independently
selected C from [.01, .1, 1.] using only their tuning rows. NFL ties remain in
history but never become invented binary winner labels.

| Features | Paired targets | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| History | 541 | 57.671% | 0.673189 | 0.477238 |
| History + efficiency | 541 | 58.410% | 0.668812 | 0.474137 |

The efficiency arm gained four correct development predictions and passed the
predeclared promising criteria. This justified the frozen retrospective check,
not promotion. Development predictions and all fold selections are in
`stages/04-test/output/accuracy-nfl-efficiency-20261101/`.

## Original reserved-period comparison

The efficiency model stayed frozen. A history-only comparator was fitted using
the exact original purged train/tune/calibration partitions, independently
selected C on the original tuning block, and used the same 120 test targets.
Original efficiency test metrics replayed to 1e-12 before interpretation.

| Features | Correct / targets | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| History | 79 / 120 | 65.833% | 0.656953 | 0.462983 |
| History + efficiency | 74 / 120 | 61.667% | 0.662388 | 0.469402 |

Efficiency minus history, paired UTC-match-day bootstrap (2,000 resamples,
seed 42):

- Accuracy: −4.167 percentage points; 95% interval **−6.897 to −1.176 points**.
- Log loss: +0.005435; interval **−0.010389 to +0.016964**.
- Brier: +0.006419; interval **−0.007144 to +0.016607**.

Reject the efficiency candidate under this comparison. Do not retune it on this
same reserved period or start a prospective trial merely because development
metrics were positive. The saved history comparator is a research comparison
artifact, not an approved replacement for the main NFL model.

## Limits and verification

These are probabilities conditional on no final tie, with overtime included and
ties void for winner scoring. The original efficiency headline had already been
inspected; this validation is retrospective, not a fresh holdout. Both arms use
three recent seasons. Their scores cannot be compared directly to the main
long-history NFL model on its different corpus/test period. Historical result
and PBP availability are assumed, without archived observation receipts. The
bootstrap omits full cross-day/team dependence and model-selection uncertainty.
No current NFL accuracy or profitability improvement is established.

Twenty-one tests passed across the new nested-partition test and existing
gridiron/sport suites. Tests check delayed-label purging, tie treatment, and
same-game/future PBP exclusion. Python compilation and whitespace checks passed;
staging is empty. Fallow remains unavailable.

The research validation directory
`pipeline/models/model_store/research/accuracy_nfl_efficiency_20261101/`
contains the fitted history comparator, paired test predictions, report and
independent replay verification. Both restored estimators match their paired
CSV probabilities to 1e-12. No original model, capture or metrics file was
overwritten. The current-season collector supports an explicit 2026 PBP request,
but it was not run for this rejected feature candidate.

From `pipeline/`, use new output directories to reproduce:

```powershell
py -3 -m models.nfl_accuracy_research --bundle models/model_store/research/gridiron_sources/20261015T194812812329Z/nfl_efficiency --capture data/raw/historical/gridiron_sources/20261015 --output ../stages/04-test/output/nfl-efficiency-development-replay
py -3 -m scripts.validate_nfl_efficiency_accuracy --bundle models/model_store/research/gridiron_sources/20261015T194812812329Z/nfl_efficiency --capture data/raw/historical/gridiron_sources/20261015 --development ../stages/04-test/output/nfl-efficiency-development-replay --output models/model_store/research/nfl-efficiency-validation-replay
```
