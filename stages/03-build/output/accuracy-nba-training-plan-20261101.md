# Bounded NBA training experiment

Freeze before execution: use the saved NBA-only dataset with SHA-256
`2d70f568131c3f3e4e76a32848711a5324d1e05698f37d88068adbdc60753bc1`.
Exclude every fixture on or after the saved final test boundary, January 14,
2025. Do not use the newly captured 2026 results or final-test outcomes to select
models. Existing final-test metrics have already been inspected; later reuse is
retrospective, never a fresh holdout claim.

Compare exactly three configurations on identical existing causal history
features and three expanding development-only date folds:

1. StandardScaler + logistic regression C=0.1, the selected baseline setting.
2. The same logistic regression with training weights decaying with a fixed
   730-day half-life, relative to the latest training date; normalize mean weight
   to one so regularization scale remains comparable.
3. HistGradientBoosting: 150 iterations, 15 leaves, 30 samples per leaf,
   L2=10, no early stopping, seed 42.

For each fold reserve the last 20% of development days for sigmoid calibration.
Fit preprocessing only on training rows. Purge labels not available before
calibration or test boundaries. Features use the existing result-availability
policy and next-UTC-day floor. Missing odds remain excluded. No parameter sweep.

A configuration is promising only if pooled accuracy increases, log loss and
Brier score both decrease, and accuracy improves in at least two of three folds.
These are development selection criteria, not a deployment authorization or
statistical significance claim. Preserve predictions for paired uncertainty
analysis. Write new research outputs only; do not alter production artifacts,
registry, frontend or database. Nothing staged or committed.

Data limits: this frozen corpus has uneven historical coverage (only 67 records
dated 2020). Availability timestamps are inherited dataset assumptions, without
archived historical observation receipts. Exclude unsupported live accuracy and
profitability conclusions. Fallow is unavailable in the current environment;
direct repository searches and source inspection were used instead.
