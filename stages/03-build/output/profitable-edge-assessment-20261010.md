# Profitable edge assessment — 10 October 2026

**No profitable edge is established for any saved candidate or active production model.** The independent bookmaker ledger verifier reproduced all five comparisons with matched prices today. WNBA and NCAA women's basketball have no matched historical price evidence. The evaluation concerns saved sport candidates, not proof of active v2.0.0 performance.

| Candidate | Paper ROI | Fixture-day bootstrap 95% interval | Finding |
|---|---:|---|---|
| Soccer | +13.28% | -38.83% to +72.24% | Inconclusive; historical odds have no observation timestamps |
| NBA | -82.91% | -100.00% to -53.00% | Negative on available sample |
| NCAA men basketball | -10.25% | -56.40% to +50.00% | Inconclusive |
| NFL | -3.07% | -48.81% to +35.07% | Inconclusive |
| College football | -53.10% | -76.35% to -39.90% | Negative on available sample |

Source: `bookmaker-comparisons-20261009-final/results.json`. Verification: `py -3 -m scripts.verify_bookmaker_comparison --report-dir ../stages/03-build/output/bookmaker-comparisons-20261009-final`. All populated ledgers reproduced. Retrospective candidates have already been inspected; reuse is an audit, not a fresh final holdout. Accuracy and positive predicted EV alone do not demonstrate profit.

## Prospective soccer trial started

Candidate `20261009T100528981075Z/football`, version 2.1.0, remains inactive. Five forecasts were saved between 11:23:22 and 11:23:27 UTC, before their verified UTC kickoffs. Source quotes were captured directly from Bovada at 11:17:38 UTC. Training and source history precede that capture; history ends September 20. Model, metrics, dataset, and capture SHA-256 digests are retained in `epl-edge-trial-20261010.json`. No results are yet recorded, so profit and ROI are unavailable.

| Fixture | Paper selection | Quote | Model probability | Break-even probability | Estimated EV | EV with 2% payout reduction |
|---|---|---:|---:|---:|---:|---:|
| Arsenal–Leeds | Leeds | 7.00 | 16.92% | 14.29% | +18.46% | +16.09% |
| Aston Villa–Brentford | Draw | 3.50 | 31.01% | 28.57% | +8.55% | +6.38% |
| Chelsea–Bournemouth | Draw | 3.90 | 27.72% | 25.64% | +8.12% | +5.95% |
| Ipswich–Fulham | Fulham | 2.50 | 44.71% | 40.00% | +11.77% | +9.53% |

United–Tottenham: no selection meets the rule. Sunderland–Brighton: excluded because candidate teams lack training history. These are test selections, not validated betting recommendations. A favorite can be most likely to win while an underdog has positive model-estimated EV; neither calculation proves the model probability is correct. Quotes, execution, and lineups are unverified beyond the public capture; one-book coverage and stale historical inputs limit reliability.

## Fixed validation protocol

One primary prospective study: this frozen soccer candidate and English Premier League regulation-time 1X2 markets. Thresholds below are declared now, before settlement of these fixtures; they are practical screening requirements, not a statistical power calculation or a guarantee of profitability.

- Record every eligible fixture, including skipped selections, before kickoff. Preserve model/data hashes, actual quoted prices, observations and generated timestamps. Reject incomplete or suspended markets, quotes over 15 minutes old, ambiguous identities, missing history, or any post-kickoff forecast. Other bookmakers may be explored separately, but this primary study stays with Bovada.
- Freeze weights and policy: highest estimated EV per fixture, maximum one selection, one paper unit. Require at least 5% estimated EV after reducing the full decimal payout by 2%. Never optimize this threshold on prospective outcomes. A weights, price-selection, or policy change starts a separate study.
- Settle only against independently verified final regulation-time results matched to the exact teams and UTC kickoff. Store the result source, observation timestamp, and settlement in a separate artifact so forecasts remain intact. Wins earn `odds - 1`, losses `-1`; under the stress scenario wins earn `0.98 * odds - 1`, losses `-1`. Postponed/cancelled games follow the quoted bookmaker settlement rules and must be disclosed.
- First scheduled formal assessment: at least 200 settled selections across at least 60 distinct UTC fixture days. Freeze the assessment cohort before computing a seeded fixture-day bootstrap interval; do not repeatedly inspect intervals until one turns positive. Record all monitored results, but interim results do not establish an edge.
- Require the stressed ROI's 95% interval lower bound to exceed zero, with calibration diagnostics, paired market log-loss/Brier comparison, drawdown, and coverage disclosed. Report this as prospective **paper** evidence; an executable profitable edge additionally requires recorded real price availability and applicable costs/limits. Resampling days leaves team and season dependence, which must remain disclosed.
- Basketball and American football require their own independently declared studies with sport-specific settlements. If claiming superiority after searching multiple sport/policy studies, use multiplicity adjustment or a new untouched confirmatory sample. Do not promote candidates from today's four selections or old inspected backtests.

## Implementation and verification

`pipeline/scripts/record_edge_trial.py` validates normalized public snapshots, candidate dataset integrity and prequote training/history, calculates margin-removed bookmaker probabilities, break-even probability, ordinary and stressed EV, and writes exclusively to a new report path. It does not retrain models, place bets, alter fixtures, or change application odds. It can record future trial batches from fresh captures with the same candidate and policy.

Run from `pipeline/`:

```powershell
py -3 -m scripts.record_edge_trial --source data/raw/sportsbooks/<run>/odds_snapshots.jsonl --output ../stages/03-build/output/epl-edge-trial-<new-id>.json --candidate-id 20261009T100528981075Z --match-date YYYY-MM-DD
py -3 -m unittest discover -s tests -p test_edge_trial.py -v
```

Three targeted tests passed: EV stress, margin removal, and rejection of malformed distributions/prices. Full model/dashboard discovery ran 86 tests: 81 passed, five opt-in database integration tests skipped. Syntax compilation passed. Fallow 3.32.0's before/after audits passed with zero introduced findings; Python is outside its analysis coverage, and missing root node_modules degrades dependency classification. The first targeted invocation used a module path unsupported by this repository's test directory; rerunning with unittest discovery passed. Automatic scheduling, result collection/settlement, broader fresh bookmaker coverage, and a sufficiently large future sample remain required; this recorder alone cannot establish profit. The configured multi-book provider currently has no usage credits.
