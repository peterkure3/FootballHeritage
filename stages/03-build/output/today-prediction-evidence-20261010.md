# Today’s prediction evidence — 10 October 2026

**No profitable edge established.** All six accessible EPL fixtures are final. Active v2.0.0 picked 3/6 winners (50%). Frozen candidate v2.1.0 picked 2/5 winners (40%); Sunderland was excluded for missing training history.

| Fixture | Active pick | Pick probability | Draw probability | Final score | Correct |
|---|---|---:|---:|---|---|
| Arsenal FC vs Leeds United FC | home_win | 82.2% | 11.0% | 2-1 | Yes |
| Sunderland AFC vs Brighton & Hove Albion FC | away_win | 39.6% | 30.6% | 0-2 | Yes |
| Chelsea FC vs AFC Bournemouth | home_win | 52.5% | 30.2% | 5-1 | Yes |
| Ipswich Town FC vs Fulham FC | away_win | 36.0% | 32.7% | 2-1 | No |
| Aston Villa FC vs Brentford FC | home_win | 34.7% | 31.1% | 2-2 | No |
| Manchester United FC vs Tottenham Hotspur FC | home_win | 70.1% | 23.4% | 1-1 | No |

## Frozen value policy, declared before kickoff

| Fixture | Selection | Recorded odds | Profit in paper units |
|---|---|---:|---:|
| Arsenal vs Leeds United | away_win | 7.00 | -1.00 |
| Aston Villa vs Brentford | draw | 3.50 | +2.50 |
| Chelsea vs Bournemouth | draw | 3.90 | -1.00 |
| Ipswich Town vs Fulham | away_win | 2.50 | -1.00 |

**Four units staked; 3.5 returned; −0.5 net; ROI −12.5%.** With the declared 2% payout reduction, ROI is −14.25%. United had no eligible value selection. Forecast weights and selection thresholds remain frozen.

## Probability comparison

| Cohort | Log loss (lower is better) | Multiclass Brier score (lower is better) |
|---|---:|---:|
| Active v2.0.0, six matches | 0.9248 | 0.5743 |
| Candidate v2.1.0, five matches | 1.0140 | 0.6163 |
| Frozen Bovada probability baseline, same five matches | 0.9803 | 0.5814 |

The candidate was worse than the bookmaker baseline on both probability metrics today. The active model uses a different six-game cohort, so these rows do not establish which model is better.

## Coverage and verification

- The account-wide official `/matches` endpoint returned zero in its TIER_ONE scope. The accessible `/competitions/PL/matches` endpoint returned all six EPL fixtures. Empty global scope is not evidence that no other games occurred.
- The database has six dated football fixtures for today, each with a valid pregame prediction. No additional dated football forecasts were available for today. Existing sport model previews are not a frozen prospective trial.
- Independently checked capture hashes, exact provider IDs/teams/UTC kickoff joins, pregame timestamps, probability sums, all six outcomes, accuracy/log loss/Brier arithmetic, and four paper bet settlements. Frozen trial import and dashboard enforce the immutable trial checksum.
- Active forecasts use the latest valid stored prediction before kickoff, which may differ from the one shown at the user’s 14:27 EAT bet placement. Five latest forecasts have saved regional audit provenance; Arsenal’s older forecast lacks that audit record. The exact displayed model remains unconfirmed.
- Results were saved in separate trial settlement receipts and this audit. No active model, application match rows, training data, or selection thresholds were changed.
- No post-result predictions were generated or counted. No retrospective threshold search was treated as fresh evidence.
- The frozen prospective protocol requires at least 200 settled selections across 60 distinct fixture days before its formal assessment, with a positive lower bound on the stressed ROI interval and calibration/market comparisons. Current progress: 4 selections, 1 day.

## Evidence files

- Detailed audit: `today-prediction-evidence-20261010/20261010T184739148023Z-evaluation.json`
- Flat forecast ledger: `today-prediction-ledger-20261010.csv`
- Official source: https://api.football-data.org/v4/competitions/PL/matches?dateFrom=2026-10-10&dateTo=2026-10-10
- Web corroboration: https://www.skysports.com/football/aston-villa-vs-brentford/report/559495 ; https://www.tntsports.co.uk/football/premier-league/2026-2027/live-ipswich-town-fulham_mtc21883056/live.shtml ; https://www.tntsports.co.uk/football/premier-league/2026-2027/live-sunderland-brighton-hove-albion_mtc21883173/live.shtml

## Next evidence collection

Continue the existing daily regional collector before kickoff; it captures prices, appends active forecasts with provenance, extends the frozen Bovada candidate study for unseen fixtures, and refreshes prior pending results. Do not retrain or change the frozen study in response to these six outcomes. A new model or policy needs a separate trial. Broader league/sport evidence requires forecasts and quotes recorded prospectively before evaluating results; completed games cannot be converted into new forward predictions.
