# Freeze for retrospective NBA inactivity validation

Development selection is complete: fixed 90-day inactivity threshold, clear
rolling histories, regress Elo halfway toward 1500; no other feature changes.
Use logistic C=0.1 with the original saved train+tune and calibration date
partitions. Do not retune on the reserved test period. Save a research-only
candidate with this explicit input feature contract, separate from production.

Compare the original frozen model and this candidate on the exact original
1,089 test fixtures, January 14, 2025 through June 9, 2026. Replay original
metrics before interpreting the comparison. Preserve paired predictions and
report match-day bootstrap uncertainty (2,000 resamples, seed 42). Report all
accuracy, log loss and Brier results, whether positive or negative.

Original final-test metrics have already been inspected; this is retrospective
validation, not a fresh holdout. Do not modify the policy after this test without
explicitly recording further development selection and losing confirmation
status. Production stays unchanged regardless of this single test. A small
improvement, source gaps, or confidence intervals spanning zero are insufficient
evidence for promotion. Prospective evidence remains necessary.
