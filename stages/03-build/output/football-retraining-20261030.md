# Football model retraining — 30 October 2026

Completed isolated global and Premier League candidate training. Serving artifacts and registries were not changed.

| Candidate | Completed matches | Held-out matches | Accuracy | Baseline accuracy | Log loss | Baseline log loss |
|---|---:|---:|---:|---:|---:|---:|
| Global odds-aware experts | 11,366 | 1,864 | 48.23% | 42.81% | 1.02086 | 1.07545 |
| Premier League history model | 2,747 | 429 | 47.79% | 41.26% | 1.03870 | 1.09159 |

Baseline means the smoothed outcome frequencies in the training and tuning periods. It is not a bookmaker benchmark. Lower log loss is better. These scores do not establish betting profitability or improvement over the active model; the active model's old validation period is different.

## Artifacts and reproducibility

- Global: `pipeline/models/model_store/candidates/20261030T200921372082Z/`
- Premier League: `pipeline/models/model_store/league_models/20261030T204820117364Z/PL/`
- Detailed audit: `football-retraining-20261030-verification.json` beside this report, including dataset and model SHA-256 hashes.
- Replay: `py -3 stages/03-build/output/verify-football-retraining-20261030.py` from the workspace root.
- Training commands from `pipeline/`:
  - `py -3 -u -m models.train_model_v2 --threads 2 --trees 200`
  - `py -3 -u -m models.train_football_leagues --leagues PL --threads 2`

Both paths use chronological training, tuning, calibration and test periods. Selection uses tuning log loss; estimator weights use training plus tuning; sigmoid calibration uses the following period. The final test period remains outside parameter fitting. Historical features within the test period use only earlier results, representing sequential forecasts.

The global test spans 28 November 2025 to 30 October 2026. Only 47 of its 1,864 test fixtures have complete imported odds, so the overall score mainly measures the history expert. The Premier League test spans 14 September 2025 to 25 October 2026. Its selected estimator is logistic regression with C=1.0; its parameter-fitting development period ends 1 December 2024 and calibration ends 13 September 2025.

## Changes and verification

Premier League fitting initially succeeded but dataset serialization failed because `provider_match_id` combined numeric and string identifiers. The league trainer now serializes this opaque metadata as nullable text. The successful rerun saved and reloaded the full dataset and model.

Artifact replay rebuilt causal features from each saved dataset and reproduced accuracy, log loss and Brier score within 1e-12. Focused checks passed: seven league forecast integrity tests and 29 feature pipeline, model selection and training resource tests.

## Scope and limits

Inputs include rolling team form, Elo, past goals, head-to-head records and home/away performance. The Premier League candidate excludes market features because historical archive observation times are not verified. The global trainer accepts imported offers only for exact fixture kickoffs and pre-kickoff observation timestamps.

The current FootyStats and Understat aggregate xG snapshots were not attached retrospectively to historical fixtures: doing so would leak later information. Match-level historical xG is still needed to retrain and validate an xG-specific model. These outcome classifiers do not incorporate confirmed lineups or weather, and do not output expected goals. No new bookmaker scrape or weekend betting-edge claim is part of this retraining run.

Fallow was unavailable locally (`fallow` missing; `npx --no-install fallow --summary` could not resolve an installed package). Repository searches and direct inspection were used to trace the training paths. Existing changes in `run_soccer_simulation.py` and `shared/CODEBASE_INDEX.md` were preserved.
