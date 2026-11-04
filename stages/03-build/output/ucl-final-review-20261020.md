# Champions League history and calibration review — 20 October 2026

The isolated candidate is `ucl_europe_reviewed_20261020`, using the project's v2.1 feature and expert-selection pipeline. The active v2.0.0 model was not replaced. These forecasts are experimental; they are not validated profitable bets or guaranteed wins.

## Data and coverage

The requested scope was the last three seasons plus current season for all 18 clubs, including domestic leagues, cups and Europe. Collection substantially expanded coverage, but **all-competition coverage is incomplete**. Records or access for Europa League, Conference League and several domestic cups were unavailable; archive scores whose regulation-time interpretation was uncertain were excluded. No all-history completion claim is supported.

The repaired training dataset contains 19,005 unique completed fixtures across its full historical span, not 19,005 matches involving only tonight's clubs. Captures include 10,355 domestic CSV rows, 2,789 deduplicated archive fixtures (partially overlapping those CSVs), 129 official Slovan/Glimt domestic results, and 539 official regulation-time Champions League results across 2023–2026. These source counts overlap and must not be added together. Coverage per club and source provenance are in `ucl-history-review-20261020.json` and `pipeline/data/raw/ucl_history_20261020/`.

Club and opponent aliases were reconciled in this isolated candidate. Contradictory results are rejected, fixture duplicates removed, and the one-senior-fixture-per-club-per-day check passed. Those checks establish internal consistency, not independent verification of every source row. Labels stop before 20 October; live features use the pre-match causal feature contract.

## Calibration and independent test

Training, tuning, calibration fitting, calibration selection and testing were separated chronologically. Unchanged logistic probabilities beat sigmoid and isotonic alternatives on the calibration selection block for both market and history experts, so the final candidate retains those probabilities. This is a calibration review, not a claim that adding a calibration transform always improves predictions.

On 3,522 held-out fixtures (21 November 2025 through 19 October 2026): accuracy **52.75%**, log loss **0.979966**, multiclass Brier score **0.583829**; zero boundary probabilities. On the same 2,608 fixtures with odds, model log loss was **0.973391**, versus market **0.973767**. The 95% fixture-day bootstrap interval for model-minus-market log loss was **[-0.003281, +0.002485]**, which includes zero. There is no demonstrated advantage over market probabilities. These are broad historical tests, not a dedicated Champions League-only profitability backtest, and do not account for realized betting costs.

The old model's zero Slovan-win and PSG-draw probabilities were reproduced through its isotonic calibrators. New candidate output was not repaired by arbitrary probability clipping. Saved model/data hashes, reload predictions, chronological separation and saved test metrics were independently checked. Seven new checks and 26 existing model/identity/form tests passed (33 total). The repository-wide Fallow audit remains failing in a working tree with hundreds of other changes; it also scans captured HTML and does not validate Python modeling logic. It is not a clean repository gate.

## Late-fixture forecasts

Snapshot: **2026-10-20T18:16:31.148444+00:00** (UTC; add three hours for Kampala). Home/draw/away refer to regulation time. “Recent” means stored quote age at most 30 minutes, not an independent check that a bookmaker will accept the price. Stuttgart–Atlético has no recent stored quote and uses the history expert.

| Fixture | Home | Draw | Away | Inputs |
|---|---:|---:|---:|---|
| AS Roma – ŠK Slovan Bratislava | 92.5% | 5.2% | 2.3% | Recent stored odds + history |
| FC Porto – PSV | 68.0% | 19.7% | 12.3% | Recent stored odds + history |
| Liverpool FC – Villarreal CF | 64.9% | 22.3% | 12.8% | Recent stored odds + history |
| Manchester City FC – PAE AEK | 87.6% | 8.5% | 3.9% | Recent stored odds + history |
| Paris Saint-Germain FC – FC Barcelona | 42.3% | 21.3% | 36.5% | Recent stored odds + history |
| SSC Napoli – FK Bodø/Glimt | 61.7% | 22.0% | 16.3% | Recent stored odds + history |
| VfB Stuttgart – Club Atlético de Madrid | 41.4% | 25.1% | 33.5% | History only |

The two early fixtures are omitted from this pre-match table because they had already started. Full probabilities, feature vectors, timestamps, bookmaker quotes and theoretical fair prices are retained in `ucl-reviewed-forecasts-20261020.json`.

## Price arithmetic and decision

- AS Roma – ŠK Slovan Bratislava: 0.82% nominal gross return; reciprocal sum 0.991827.
- FC Porto – PSV: 0.18% nominal gross return; reciprocal sum 0.998233.
- Manchester City FC – PAE AEK: 1.56% nominal gross return; reciprocal sum 0.984651.

These are **nominal quote combinations, not verified executable arbitrage**. Bookmaker availability, consistent settlement rules, limits, taxes, commissions and simultaneous acceptance were not verified. Exact quoted legs and equal-payout allocations are in `ucl-final-price-audit-20261020.json`. No bet was placed.

The largest positive model EV among the recent stored prices is the Liverpool–Villarreal draw at 5.04 (model probability 22.29%, gross theoretical EV +12.35%). Napoli at 1.75 is +8.04%, and Porto at 1.57 is +6.78%. These estimates inherit the model's uncertainty and incomplete competition history; they are review candidates, not established edges. No stake or accumulator recommendation is justified by this validation.

Remaining work before promotion: complete and verify missing competition coverage, evaluate Champions League and relevant club/league subgroups with adequate samples, and run a forward paper trial using executable prices and net returns. No statistic can ensure a winning wager.
