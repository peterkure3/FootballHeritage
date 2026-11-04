# ML research safeguards — October 30, 2026

Implemented an isolated research path from the October 23/30 brief. Production
models, serving registries, Rust APIs and PostgreSQL schemas were not changed.
No sports forecasting improvement or model promotion is claimed.

## Repository findings and reuse

- `models/features.py` already prevents current/same-day result leakage by
  emitting each UTC day's features before updating its state.
- `models/sport_features.py` queues results until their declared availability;
  collectors include explicit conservative two-day assumptions. Those assumptions
  are not historically verified availability and cannot pass the new strict gate.
- `train_football_leagues.py` already excludes unverified historical archive odds.
- `models/validation.py` supplies chronological date blocks, walk-forward folds,
  log loss, summed multiclass Brier score and classwise calibration bins. Reused.
- Existing soccer simulation already compares a direct Poisson baseline. Extended
  its evaluation output rather than introducing a competing simulator.
- Fallow could not run: npm's no-install invocation found no local package; the
  standalone executable was also absent. Existing Fallow reports cover primarily
  frontend modules and cannot establish Python architecture health. Repository
  searches and direct dependency inspection were used; no cleanup was attempted.

## Implemented

1. Executable `ForecastContract` and feature provenance checks: explicit forecast
   mode/cutoff, verified availability, input snapshot identity, definitions,
   aggregation cutoff, and causal rolling dependencies. Unknown or assumed
   availability fails, including current/future game contributions.
2. An explicit-mapping NBA PBP audit with immutable raw captures, SHA256 manifests,
   schedule coverage, event uniqueness/order, clocks, scores and terminal checks.
   Possession approval remains false pending semantic validation.
3. A research CLI using the existing date split and folds, isolating competitions
   and final future periods. Training labels must be available before validation
   or holdout forecasts. Training-only preprocessing; fixed-budget logistic,
   LightGBM and XGBoost; optional dependencies explicitly reported.
4. Basic versus one-added-feature-group comparisons on identical periods/budgets.
   Player/lineup groups pass only with verified provenance. No speculative feature
   definitions or sports embeddings were introduced.
5. Missing groups, multiplicative numerical corruption, and actual earlier-snapshot
   staleness experiments. Reports include probability degradation, fallback
   behavior, calibration bins, game-level forecasts and competition/season counts.
6. Paired final scores retained for every soccer simulation run, with margin/total
   CRPS, 80/90/95% interval coverage, tail quantiles, direct-baseline comparisons and
   conditional Monte Carlo standard errors. Evaluation cache version is now 2;
   version-1 cached results must be regenerated in a new output run.

Usage and the input/evidence schema: `pipeline/docs/ML_RESEARCH.md`.

## Measured NBA ingestion pilot

Source repository: https://github.com/sportsdataverse/hoopR-nba-data

Producer status: https://www.sportsdataverse.org/status

Actual public release assets (2027 is the provider's season-ending year):

| Asset | Release updated UTC | SHA256 |
|---|---|---|
| `play_by_play_2027.parquet` | 2026-10-30 12:03:07 | `290b0630a7fe4f7f1bfbf2a05f6648b22341f21eb87abd359adfb21bc5a6406e` |
| `nba_schedule_2027.parquet` | 2026-10-30 12:04:18 | `dd0f6186e41525f1f3f9a325dcb106982ffa4a96add84dba9c38cddf5100ba79` |

Raw snapshots, release metadata, retrieval timestamps and manifests:
`pipeline/data/raw/historical/nba/pbp_research_20261030/` (local data, do not commit).

The pilot has **36,332 regular-season events, 71 event games, 71 completed schedule
games**, zero missing/unexpected games and zero final-score discrepancies.
`game_play_number` passes order checks without sorting. The original provider
`sequence_number` regresses in **70 games**; retained separately as an audit
diagnostic, not silently repaired. The provider marks every score as `rebuilt`;
score reconciliation with the supplied schedule does not independently verify
every original event or official result. Player identity crosswalks, substitutions,
and possession boundaries remain unvalidated. Structural pass is not permission
to reconstruct possessions or use the pilot for production predictions.

Full evidence: `nba-pbp-audit-20261030.json`.
Reproduce offline: `py -3 stages/03-build/output/audit-nba-research-20261030.py`.
This is one current-season asset pair, not a historical coverage census. Older
seasons and additional asset classes still need their own audits.

## Verification and remaining work

Targeted command from `pipeline/`:

```powershell
py -3 -m pytest tests/test_research_safeguards.py tests/test_soccer_simulation.py tests/test_model_pipeline.py tests/test_sport_models.py tests/test_basketball_leagues.py -q
```

Checks cover adversarial leakage, snapshot mutation, provider column collisions,
NBA structural failures, chronological experiment execution, CLI report creation
and overwrite rejection, missing-input handling, score pairing, CRPS, and soccer
evaluation/aggregation integration. Python compilation also passed.

Final result: **71 tests passed, 10 subtests passed** in 15.39 seconds. The
installed candidate models also passed the three-class missing-feature check.
`git diff --check` passed. The final test iteration corrected an integer-valued
synthetic fixture to floating point before injecting NaN, as required by pandas;
the research input adapter already creates floating-point feature frames.

The experiment runner was exercised with synthetic inputs to verify behavior.
**No new real-sports holdout log loss/Brier/calibration improvement has been
measured.** Existing historical availability assumptions cannot legitimately be
turned into verified timestamps. Next required work is a provenance-producing
adapter for existing football/basketball builders, independently supported
historical availability evidence, and preregistered future holdouts. Then run
the defined feature/robustness experiments and report measured seasonal results.
The new gate is enforced by the research CLI; it has not been retrofitted into
every production collector/trainer. No calibration/ensemble method change,
new basketball possession simulator, or promotion recommendation was made.

Stage 03 remains open; this report does not assert completion of the entire
research programme or staging acceptance.
