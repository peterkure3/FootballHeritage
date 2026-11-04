# Free NBA archive acquisition and research training — 2026-10-15

Downloaded a free historical NBA moneyline/results archive with Scrapling and trained both history and odds-aware research estimators. The Odds API paid-plan restriction remains, but it does not prevent this separate archival experiment.

## Source and capture

- Primary public dataset: [Guy Dotan's UCLA thesis repository](https://github.com/guydotan/ucla-thesis), `data/nba_adv_complete.csv`.
- Underlying archive: Sportsbook Reviews Online. The original NBA archive URL returned 404 during this investigation; the public research copy remains downloadable.
- Downloaded the original CSV, repository license, README and [independent replication provenance notes](https://github.com/jacobburdier05/nba-moneyline-calibration/blob/main/data/README.md).
- Capture: `pipeline/data/raw/historical/nba/free_archive/20261015/`; `manifest.json` records URLs, retrieval time, sizes and SHA-256 checksums.
- Original CSV: 20,853,868 bytes, SHA-256 `4958bcd335fd4c45e20e5980ae7146e0e4eff74c19444acd9576ea564d3c7944`, matching the published reference checksum.
- No account, purchase, or Odds API credits used for these downloads. Scrapling checked the raw host's robots policy before collection.

The file contains 32,986 team records representing 16,493 games, October 30, 2007–March 11, 2020. Unlike the reduced matchup file described by the replication project, this complete team-level file contains both regular-season and playoff games. Measured counts come from the downloaded original, not the replication project's smaller subsets.

## Data checks

Each game must have exactly one home and one away record. Paired team IDs, names, dates, season type, scores and reciprocal odds must agree. Outcomes must agree with scores. American prices must be finite and have absolute value at least 100; they are converted to decimal prices. Missing prices stay missing rather than being imputed.

Excluded game `21201214` because its outcome and score disagree. This leaves 16,492 validated games and 16,491 complete moneyline pairs. The remaining game without prices remains available to the history estimator. Current-game box-score columns are never passed to the estimators: score history is rebuilt causally with a conservative two-day result-availability delay.

Odds observation times, bookmaker identity and opening/closing status are undocumented. Quote timestamps remain null. Nominal midnight game dates are explicitly marked DAY precision and are not presented as exact UTC tipoff times. These odds were not inserted into the verified public-quote capture directory and the production timestamp-matching rules were not relaxed.

## Training and evaluation

Research run: `20261015T165801405910Z`.

Artifacts: `pipeline/models/model_store/research/nba_archive/20261015T165801405910Z/`, containing `dataset.parquet`, `model.pkl` and `metrics.json`. Detailed evidence: `stages/03-build/output/nba-archive-training-20261015.json`.

| Partition | All games | Complete odds |
|---|---:|---:|
| Training | 10,032 | 10,031 |
| Tuning | 2,421 | 2,421 |
| Calibration | 1,682 | 1,682 |
| Test | 2,357 | 2,357 |

The same existing standardized logistic-regression selection and separate sigmoid calibration are used for history and market experts. History C=1.0; market C=0.1, selected on tuning games only. The test period runs April 16, 2018–March 11, 2020.

| Same held-out games | Accuracy | Log loss | Two-class summed Brier score |
|---|---:|---:|---:|
| History + odds | 67.59% | 0.5981 | 0.4113 |
| History only | 65.68% | 0.6173 | 0.4291 |
| Vig-free archive odds baseline | 67.33% | 0.5989 | 0.4115 |

The small descriptive improvement over archived implied probabilities is not a demonstrated betting edge. These figures are not directly comparable with the newer NBA-only candidate's 64.37%, because its held-out games are from a different period.

## Status and reproducibility

The model is marked `research_candidate`, `research_only: true`, `odds_observation_verified: false`, and `active: false`. It is stored outside the sport-model candidate catalog. The prior NBA candidate remains available unchanged. The archive's undocumented quote times prevent validating it as a point-in-time pregame backtest, and its history ends in 2020.

From `pipeline/`:

```powershell
.\.venv-scrapling\Scripts\python.exe ..\stages\03-build\output\fetch-nba-archive-20261015.py
py -3 ..\stages\03-build\output\train-nba-archive-20261015.py
py -3 ..\stages\03-build\output\verify-nba-archive-20261015.py
```

Verified source and model/dataset checksums, chronological coverage, model reload and valid probability rows. All six standalone behavioral checks passed in a fresh process, covering American-odds conversion, home/away alignment, conflict exclusion, incomplete pairs, missing odds and persisted market/history routing. Repository audit evidence is `nba-archive-fallow-20261015.json`; Fallow still reports existing frontend issues and a missing root node_modules warning. No production model, API or frontend code was changed.

Timestamped Odds API data still requires a funded paid key. Futures and season-win-total archives are different prediction targets and were not substituted for game moneylines. NCAA model training remains outside this NBA task.
