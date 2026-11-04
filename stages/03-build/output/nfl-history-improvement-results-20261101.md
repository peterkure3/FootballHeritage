# NFL history, candidate efficiency and validation results

Completed the requested NFL work without staging, commits or production changes.

- Collected 13 seasons of nflverse play-by-play (2014–2026), plus schedules;
  14 hash-verified input files, no download failures. Exported 7,125 score rows
  from 2000–2026 and retained 598,931 play rows.
- Prepared 3,403 model games with complete two-team play-by-play coverage and
  12 ties retained as history, excluded from winner targets.
- Measured aggregate caching at 1.570 s cold versus 0.017 s warm (~91× for that
  stage). Build the feature matrix once, reuse it across season folds, and reuse
  train-only scaling within each C search. Source/cache changes are checked.
- Added six season-based development tests, separate tuning/calibration, purged
  labels, week-block bootstrap, a reserved 2026 period, prior benchmark,
  calibration diagnostics and seven-day availability sensitivity.
- No alternate feature set passed all predeclared quality gates. The refreshed
  history candidate and frozen reference each got 61/107 correct in 2026.
  Refreshed log loss was 0.6495 versus 0.6529, but its uncertainty interval
  includes zero and the bin-calibration diagnostic was worse. No reliable
  predictive improvement or promotion is claimed.
- The refreshed prediction batch measured 4.3 ms versus 8.8 ms for the reference
  in this local run. This is environment-dependent, not an API latency promise.
- Thirty-one focused/regression tests passed. Source/model/feature replays,
  compilation and whitespace checks were executed; unavailable pyflakes/Fallow
  are not claimed as checks. Existing CI automatically discovers the new tests.

Data, candidate files, exact metrics/assumptions, environment and repeatable
commands are documented in `pipeline/docs/NFL_HISTORY_VALIDATION.md`. Core paths:

- `pipeline/data/raw/historical/nfl_accuracy_20261101/`
- `pipeline/data/processed/nfl_accuracy_20261101/`
- `pipeline/models/model_store/research/nfl_expanded_20261101/`
- Shareable scores: the candidate directory's `audit/nfl_score_history.csv`.

The candidate stays research-only. Historical observation timing is assumed,
2026 is partial and retrospective, and more prospective evidence is required
before considering production adoption. No markets/picks were published.
