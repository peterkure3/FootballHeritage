# Paired NFL efficiency experiment

Freeze before execution. Corpus: the existing 855-game research snapshot with
dataset SHA-256 `105fd348d6e9a906c0fe817e5eb7dce3edda4c63945c08c7115f0955be6d0444`.
Rebuild nflfastR aggregates from hash-verified captured 2023–2025 parquet files
and require exact agreement with the saved feature matrix. Exclude all fixtures
on/after November 23, 2025, the existing 120-game reserved-test boundary.

Compare history-only features versus the same history plus the existing lagged
EPA/success-rate features. No new feature invention, market odds, extra model
families or parameter sweep. Each arm uses standardized logistic regression.
Select C from the existing [.01, .1, 1.] grid by tuning log loss within each
expanding development fold. Refit train+tune and sigmoid-calibrate independently.

Use three expanding date folds. Partition each development block into 60%
training days, 20% tuning days, 20% calibration days. Purge labels unavailable
before the next partition. Retain ties in history, exclude ties from supervised
winner targets, and evaluate probabilities conditional on a non-tied final.
Both arms score exactly the same targets. No test outcome influences selection.

An efficiency gain is promising only if pooled accuracy improves, log loss and
Brier both decrease, and accuracy improves in at least two of three folds. Save
per-fixture probabilities, selected C values, boundaries, source/code hashes and
all metrics. This is development selection, not fresh confirmation or deployment.
If rejected, do not retune this same reserved period to manufacture a gain.

The archived play-by-play has no verified historical observation receipts. Its
availability inherits the game snapshot's assumed conservative delay; this
does not establish the date on which historical EPA revisions were available.
Recent-season sample size and incomplete coverage limit conclusions. The saved
61.67% efficiency headline cannot be compared to the main model's 64.56% on a
different corpus. Production and registry stay unchanged. Nothing staged or
committed. Fallow remains unavailable; existing code/search evidence was used.
