# Latest NFL refit performance evaluation

The latest model uses every decisive completed snapshot game for base fitting or
calibration, including 2026. Do not report its calibration accuracy or the older
pre-2026 model's holdout score as its independent performance.

Check a fresh nflverse schedule/results capture for games after the model's
training timestamp. When none exist, record zero independent targets explicitly.
Freeze upcoming seven-day predictions before kickoff for later assessment; no
publishing, production change, staging or commits.

Historical evaluation will replay the same refitting procedure in seasons
2020–2025 at 06:15 UTC on the Sunday of week 8, matching the current training
point. Select C using only prior-season tuning data with the existing season
split/selection helper. Then train on previous seasons and sigmoid-calibrate
on current-season results available at the cutoff. Test only later games in
that season. Keep weights frozen while causal history updates before each game.

Compare midseason refit, preseason model, previous-season training prior and
available current-season calibration prior on identical non-tied targets.
Report accuracy, log loss, Brier, calibration bins, per-season counts and paired
season-block bootstrap intervals (2,000 resamples, seed 42). Save each replica
and paired predictions. Do not tune after inspecting these outcomes.

These are retrospective procedure estimates. Existing feature-family research
has inspected historical seasons; archived data revisions and assumed two-day
availability are not verified point-in-time receipts. Six season clusters do
not establish universal performance or profitability. The actual November 1
artifact still requires independent results after training.
