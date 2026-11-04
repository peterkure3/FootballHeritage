# Active model run — Champions League, 20 October 2026

Read-only inference executed at approximately 17:35 UTC / 20:35 EAT. No model was trained, promoted or replaced. No database predictions or bets were written.

Verified artifact through the serving loader: v2.0.0, CalibratedClassifierCV, isotonic calibration, 38 features. The saved training manifest reports trained_at 2026-10-04 and calibrated accuracy 55.01%; this historical metric was read, not independently reproduced today. No claim of current profitability follows from it.

Used the existing build_feature_vector and model.predict_proba serving path with the configured database. Inputs use arithmetic mean prices from each bookmaker's latest complete stored snapshot, matching the batch serving approach. Output records the individual quotes and feature vector so the inputs are reviewable. Database connections were forced read-only. The inference verifies finite probabilities summing to one.

Database audit: 1,570 completed football records; latest completed fixture dated 19 October; zero completed fixtures dated at or after the inference cutoff. This global freshness does not establish team-level completeness. Some named teams' latest exact-name history ends on 13–14 October, despite known more recent domestic games. Legacy functions use wildcard names without candidate-model alias normalization.

| Fixture | Home | Draw | Away | Raw winner |
|---|---:|---:|---:|---|
| Roma–Slovan | 66.42% | 33.58% | 0.00% | Roma |
| Porto–PSV | 34.46% | 27.45% | 38.09% | PSV |
| Liverpool–Villarreal | 47.13% | 25.91% | 26.96% | Liverpool |
| City–AEK | 72.86% | 20.52% | 6.62% | City |
| PSG–Barcelona | 55.03% | 0.00% | 44.97% | PSG |
| Napoli–Bodo | 48.91% | 17.34% | 33.75% | Napoli |
| Stuttgart–Atletico | — | — | — | Withheld: no stored complete odds |

These six fixtures are scheduled for 19:00 UTC. The early Sabah fixture was also computed but is explicitly flagged as past scheduled kickoff: it is not a live forecast. Fenerbahce was withheld for missing odds. No default odds were substituted.

## Interpretation

The earlier odds-only Napoli recommendation is not supported by this model: fair odds are approximately 2.045 against best stored Napoli 1.71 (gross model EV -16.36%). The model's best stored value discrepancies include Villarreal at 6.14 (26.96%, gross EV +65.55%) and Bodo at 4.80 (33.75%, +62.00%). These are raw unvalidated model discrepancies, not accepted betting edges; data coverage and calibration concerns preclude confident recommendations.

PSG's 55.03% would imply gross EV +35.94% at stored 2.47, but the same output assigns exactly zero to a draw. Roma's output also assigns exactly zero to an away win. Isotonic calibration can produce boundary outputs; this alone does not prove corruption, but these football probabilities require calibration assessment before staking.

Exact-name coverage is particularly sparse for Slovan (two completed matches), AEK (two) and Porto (two). This is not proof those clubs lack history: alternate names and missing competitions may hide available form. Stored quotes mostly have timestamps near 17:25 UTC, with some near 17:08; actual accepted bookmaker prices and stake limits were not verified.

## Artifacts

- Reproducible runner: `run-ucl-model-20261020.py`.
- Full generated output: `ucl-active-model-20261020.json`.

Run completed twice with identical probabilities; second execution records calibration type and explicit quality flags. Probability validity checks passed. No independent historical calibration/ROI test was performed. Recommended disposition: use these as diagnostic forecasts; do not treat the large apparent EV values as established profit opportunities.
