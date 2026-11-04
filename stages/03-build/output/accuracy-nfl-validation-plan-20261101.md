# Frozen paired NFL retrospective validation

The predeclared development efficiency ablation passed its promising criteria.
Freeze the existing 26-feature efficiency definition and original saved model;
do not retune it. Rebuild its exact input matrix from hash-verified raw play-by-
play and require its original 120-fixture metrics to replay to 1e-12.

Fit a history-only comparator using the exact same 855-game corpus and original
purged train/tune/calibration partitions. Select its C from [.01, .1, 1.] on
original tuning log loss, refit train+tune, and independently sigmoid-calibrate.
Use no test outcomes to select C, features, model family or calibration.

Score both on the same original 120 non-tied fixtures. Save paired probabilities,
all metrics and conditional-on-no-tie semantics. Quantify paired uncertainty with
2,000 UTC-match-day bootstrap resamples, seed 42. Retain ties in feature history.
Do not compare these metrics to the long-history main model on a different test.

Original efficiency metrics have already been inspected; this is retrospective,
not a fresh holdout. Historical postgame/PBP availability is assumed, not verified
by archived observation receipts. No production changes or promotion follow this
small retrospective comparison. No staged files or commits.
