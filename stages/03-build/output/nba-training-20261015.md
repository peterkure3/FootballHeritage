# NBA training — 2026-10-15

Trained and saved an NBA-only calibrated winner candidate using the existing sport trainer. Candidate ID: `20261015T163645187197Z`.

Artifacts: `pipeline/models/model_store/candidates/sports/20261015T163645187197Z/basketball/` (`model.pkl`, `dataset.parquet`, `metrics.json`). Parent `report.json` makes the run discoverable in the existing sport-model catalog. Detailed evidence: `stages/03-build/output/nba-training-20261015.json`.

## Data and fitting

- 8,114 completed NBA games, October 16, 2018 through June 9, 2026.
- Excluded 472 NCAA games. The source loader quarantines one contradictory NBA fixture.
- The recent Scrapling capture's completed games are preseason and were not added to this training corpus. Upcoming games are not training labels.
- Chronological partitions: 5,058 training, 1,256 tuning, 711 calibration, 1,089 test games. Test period: January 14, 2025 through June 9, 2026.
- Standardized logistic regression, tuning selected C=0.1; development refit on 6,314 games followed by separate sigmoid calibration.
- The optional odds-based expert could not train: zero complete timestamped prematch moneyline joins. The saved winner model uses historical features.

| Held-out metric | NBA candidate | Development-prior baseline |
|---|---:|---:|
| Accuracy | 64.37% | 53.44% |
| Log loss | 0.6327 | 0.6924 |
| Two-class summed Brier score | 0.4413 | 0.4992 |

## Verification

Training completed successfully. Confirmed NBA-only training and dataset league scope, model/dataset SHA-256 hashes, artifact reload, and valid prediction probabilities summing to one. All 10 `test_sport_models.py` checks passed, covering causal history, league isolation, invalid outcomes, conflicting scores, artifact routing and persistence. A separate `models.sport_predict` process was used for the final reload check.

Fallow audit exited 1 with existing frontend unused-code, duplication, complexity and styling findings, and a missing root node_modules warning. No frontend or production training code was modified for this run. Fallow does not validate Python training behavior.

The artifact is a candidate (`active: false`); it has not been promoted to the active prediction source. History ends in June 2026. Evaluation is retrospective and excludes the current season's new game, roster and injury information.

Reproduce from `pipeline/` (creates a new timestamped candidate):

```powershell
py -3 ..\stages\03-build\output\train-nba-20261015.py
```

Preview the saved candidate:

```powershell
py -3 -m models.sport_predict --candidate-id 20261015T163645187197Z --sport basketball --league basketball_nba --home "Boston Celtics" --away "Los Angeles Lakers" --kickoff 2026-10-17T00:00:00Z
```
