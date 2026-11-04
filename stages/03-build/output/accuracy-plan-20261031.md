# Accuracy improvement experiment 1

Goal: improve deterministic match-winner forecasting, beginning with soccer.
No staging/commits, model promotion, registry edits or production changes.

Baseline inspected: global candidate `20261031T192153116992Z`, 1,894 test
matches, 48.36% accuracy. Only 52 have recorded odds; 1,842 use its history expert.
The final period has already been inspected and is not a fresh confirmation set.

Freeze this experiment before scoring: use only dates before the saved candidate
test start. Three expanding date-blocked folds; within each earlier training
window reserve the last 20% of days for calibration. Compare the existing
history-only logistic C=.01 plus sigmoid calibration with two fixed candidates:
the same logistic with added context and a 150-iteration histogram gradient
model (15 leaves, minimum leaf 30, L2=10), also with separate calibration.
No hyperparameter search and no class-weight/threshold tuning on evaluation rows.

Added context: competition identity; previous-day-only 5/30-game scoring rates,
opponent Elo exposure, rest days, and league home/draw/away rates. Features and
preprocessing may consume only earlier UTC days. All archived odds are excluded.
The next-day final-result availability rule is an assumption inherited from the
existing corpus, not verified historical availability. Results are retrospective
sensitivity evidence and cannot pass the strict research provenance gate.

Report paired per-fold accuracy, log loss, Brier, odds coverage, forecast rows,
and prediction-time invariance tests. An exploratory candidate is promising only
if aggregate accuracy rises without worsening aggregate log loss or Brier, and
the gain is not confined to a single fold. Freeze the output before looking at
any newer results. Confirmation requires prospective forecasts after this run.
Do not present training overlap or reused holdouts as unseen evidence.
