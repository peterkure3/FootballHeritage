# NFL history, efficiency and validation plan

User scope: collect NFL history, make the NFL candidate more efficient, improve
validation. No staging/commits; production models stay unchanged.

Capture official nflverse schedules and play-by-play for 2014–2026 in a new
directory. Reused 2023–2025 files must retain their verified hashes and original
retrieval metadata. Keep archival odds outside model inputs. Export normalized
completed games and audit season coverage, native IDs, team identity, ties,
missing play-by-play and data availability. Collection timestamps are not proof
of historical observation times; result/PBP timing is an explicit assumption.

Improve offline processing with a source-hash-keyed aggregate cache and feature
matrix computed once per dataset. Benchmark raw versus cached aggregation and
record exact agreement; do not claim speed gains without measured timings.

Freeze four logistic feature sets before evaluation: original history (16),
existing history+EPA/success features (26), compact history differences (5), and
compact history plus EPA/success differences/coverage (10). Fixed C grid
[.01, .1, 1.], seed 42. No other model families or test-driven parameter changes.

Use expanding season folds 2020–2025 for development selection. For test season
Y, fit on seasons before Y−1, tune on weeks 1–9 of season Y−1, and calibrate on
the remaining weeks of Y−1. Purge labels unavailable at the next partition.
Retain ties in history but exclude them from binary winner labels. Score
identical fixtures for every arm. Persist boundaries, selections, paired
predictions, calibration metrics and timing. Bootstrap paired differences by
NFL season/week, rather than treating individual games as independent.

A new quality candidate must improve pooled development log loss, not worsen
accuracy or Brier, and improve log loss in at least four of six seasons. Among
eligible candidates choose lowest log loss; otherwise retain history baseline.
Save this decision and fitted models before scoring the reserved 2026 season.
2026 is excluded from this new selection procedure, but earlier long-model
aggregate reports included some 2026 data, so label it retrospective, not fresh.

Evaluate the frozen choice versus baseline on available 2026 targets, including
weekly uncertainty, calibration and season-type/coverage breakdowns. Repeat an
explicit seven-day availability sensitivity check without retuning. Measure
artifact size and prediction timing on the same batch. Historical gains and
better computation do not establish live accuracy or profitability. Publish no
picks and make no automatic promotion.
