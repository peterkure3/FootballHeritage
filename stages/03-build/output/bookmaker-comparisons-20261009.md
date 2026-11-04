# Basketball and football bookmaker comparisons — 2026-10-09

The comparison ran across seven saved model candidates. **None establishes a
bookmaker advantage.** The final dashboard is
[`bookmaker-comparisons-20261009-final/index.html`](bookmaker-comparisons-20261009-final/index.html).
Its JSON results include per-bookmaker scoring; CSV ledgers retain every matched
fixture, source capture, quote, model forecast, selected book and settled paper bet.

| Model | Matched games | Model accuracy | Bookmaker accuracy | Model log loss | Bookmaker log loss |
|---|---:|---:|---:|---:|---:|
| NBA | 14 | 85.71% | 100.00% | 0.51545 | 0.37213 |
| NCAA men basketball | 10 | 80.00% | 70.00% | 0.48477 | 0.49515 |
| WNBA | 0 | Unavailable | Unavailable | — | — |
| NCAA women basketball | 0 | Unavailable | Unavailable | — | — |
| NFL | 63 | 58.73% | 60.32% | 0.69358 | 0.64367 |
| College football, FBS participant | 170 | 78.82% | 86.47% | 0.46714 | 0.33229 |
| Soccer | 108 | 60.19% | 59.26% | 0.91025 | 0.91010 |

Lower log loss is better. Model and market always score the same games. These
conditional sample accuracies differ from each model's full historical test
accuracy and should not be substituted for that overall metric.

## Paper policy

The rule is fixed at a minimum predicted 5% EV, at most one flat-unit selection per
fixture. Two-way sports use the best actual quoted price among books from one
selected capture. NFL final ties void bets; none of the matched NFL fixtures tied.
Soccer retains its existing historical B365 price policy. No threshold or stake
optimization occurred during this comparison.

| Model | Bets | Profit, units | Paper ROI | Fixture-day bootstrap 95% ROI interval |
|---|---:|---:|---:|---|
| NBA | 11 | -9.12 | -82.91% | [-100.00%, -53.00%] |
| NCAA men basketball | 8 | -0.82 | -10.25% | [-56.40%, +50.00%] |
| NFL | 58 | -1.78 | -3.07% | [-48.81%, +35.07%] |
| College football | 143 | -75.93 | -53.10% | [-76.35%, -39.90%] |
| Soccer | 80 | +10.62 | +13.28% | [-38.83%, +72.24%] |

Returns assume the stored quote could have been obtained. Quote availability,
regional access, account/stake limits, exchange commissions, fees and slippage
are unverified. These are indicative paper results, not realized trading returns.

## Probability evidence and uncertainty

The paired comparison resamples entire UTC fixture days, using 4,000 bootstrap
draws with seed 42. Positive log-loss advantage means market log loss minus model
log loss, so positive favors the model.

| Model | Fixture days | Log-loss advantage | Paired 95% interval |
|---|---:|---:|---|
| NBA | 4 | -0.14333 | [-0.22499, -0.04411] |
| NCAA men basketball | 4 | +0.01038 | [-0.03033, +0.18558] |
| NFL | 16 | -0.04991 | [-0.17524, +0.04928] |
| College football | 15 | -0.13485 | [-0.18702, -0.09101] |
| Soccer | 14 | -0.00015 | [-0.04115, +0.02824] |

NBA and NCAA men have only four fixture-day clusters; their estimates are unstable
and unrepresentative of a full season. College football's market baseline is
substantially better on this sample. NFL's interval spans zero. NCAA men's small
accuracy lead and soccer's positive paper return do not establish an advantage.
Resampling fixture days does not remove all team/season dependence, and searching
across multiple leagues is not a single pre-registered prospective test.

## Matching, timing and sources

- NBA candidate: `20261009T100528981075Z/basketball`, restricted to NBA games;
  soccer: the same run's football candidate.
- WNBA and NCAA basketball candidates: `20261009T103733107847Z`.
- NFL and college football candidates: `20261009T144354530070Z`.
- All candidates use frozen, checksummed datasets and saved model weights. No
  retraining, production promotion or real bets occurred.
- Two-way comparisons use stored The Odds API capture files: 47 NBA, 36 NCAA men,
  16 NFL and 16 college football files inspected. WNBA and NCAA women had no stored
  capture files for their league keys, so no price comparison was manufactured.
- College football school-plus-mascot bookmaker names map to historical school
  names through ESPN's public team directory and the stored ESPN team IDs. Only
  unambiguous exact directory aliases are accepted; no fuzzy team matching.
- NBA matching uses exact team/kickoff keys or an identical 32-character provider
  event ID with exact teams, within a six-hour kickoff adjustment limit. This
  resolves recorded tip-off minute changes. Date-only NBA history is excluded:
  7,766 of its 8,114 historical rows lack exact kickoff instants. The first strict
  kickoff-only pass is retained separately; this report uses the final ID-verified
  pass.
- One synchronized capture supplies all books for a fixture; no mixture of books
  observed on different days. Market probabilities normalize each book's inverse
  decimal odds separately, then average fair probabilities across books. Betting
  uses actual individual book quotes, not synthetic averaged odds.
- Legacy captures contain local wall time without a timezone. Their actual UTC
  observation is bounded using worldwide offsets UTC+14 through UTC-12. A quote
  is accepted only if the latest possible capture precedes kickoff. Model history
  stops before the earliest possible capture's UTC day. Provider price update
  times are checked but never substituted for actual observation times.
- Prediction rest features use the kickoff stated in that capture, not a later
  corrected tip-off. Result availability is the candidate dataset's conservative
  historical estimate. No results arriving between capture and kickoff enter
  the forecast.
- NFL outputs are conditional on no final tie, matching a ties-void two-way market.
  Calibration ends before every accepted quote-time forecast. The candidates were
  fitted retrospectively and previously inspected, so this is not fresh final
  validation.
- Soccer uses the established 108-game historical B365 comparison. Its odds have
  no precise observation timestamps; it is reported as a separate weaker evidence
  track, not as a synchronized snapshot comparison.

The model-versus-market figures differ from the initial training report's odds
subset because this comparison freezes history at quote time and normalizes each
book separately. The original full-test reports remain intact.

## Verification and repeat commands

All **74** behavioral tests pass, including two-way probability scoring, paper
policy math, timezone bounds, team-ID ambiguity rejection, synchronized quote
selection, stable event-ID matching, and protection against post-quote outcomes.
Compilation passed. Fallow 3.32.0's new-findings audit passed with its inherited
JavaScript findings; it does not analyze these Python models.

`scripts/verify_bookmaker_comparison.py` independently reproduced exported model/
bookmaker metrics, checked selected prices against each actual book offer, checked
paper profits and pregame bounds, and verified input capture checksums. Soccer's
metrics and ledger totals reproduced, with its untimestamped historical price
limitation retained. Evidence: the final directory's `verification.json`.

Run from `pipeline/`, choosing a new output directory to preserve the audited run:

```powershell
py -3 -m models.sport_market_demo --output-dir ../stages/03-build/output/bookmaker-comparisons-next
py -3 -m scripts.verify_bookmaker_comparison --report-dir ../stages/03-build/output/bookmaker-comparisons-next
py -3 -m unittest discover -s tests -v
```

Primary identity source:
[ESPN college team directory](https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=1000).
Its captured response, source URL and checksum are retained in the report.
