# UCL edge recheck — 21 October 2026

Generated 2026-10-21T18:18:44.762056+00:00. Public prices observed 2026-10-21T18:16:36.606299Z, 2026-10-21T18:16:38.455832Z, 2026-10-21T18:16:38.904190Z.

Main conclusion: Sporting remains the stronger provisional single at 1.37 Ababet. Brugge has shortened from 1.94 to 1.88 and is downgraded to marginal/watchlist when assessed at its earlier frozen probability. No demonstrated profitable edge or certain winner is established.

| Home selection | Current odds | Current model chance | EV after winnings withholding | EV at frozen 21:01 probability | EV if current probability is 3pp too high |
|---|---:|---:|---:|---:|---:|
| Real Madrid | 1.27 ababet | 80.9% | -0.57% | -0.13% | -4.26% |
| Inter | 1.27 ababet | 82.3% | +1.16% | +0.81% | -2.53% |
| Bayern Munich | 2.44 betpawa | 46.5% | +3.47% | +5.23% | -3.20% |
| Club Brugge | 1.88 ababet | 59.2% | +3.49% | +0.45% | -1.76% |
| Aston Villa | 1.31 ababet | 81.3% | +2.71% | +2.46% | -1.08% |
| Sp Lisbon | 1.37 ababet | 79.3% | +4.22% | +3.68% | +0.27% |
| Betis | 1.70 ababet | 58.1% | -7.36% | -7.01% | -12.15% |

The probability stress is a sensitivity scenario, not a confidence interval. The model uses prices as input, so shortening odds can raise its probability without new independent team evidence. Holding the previous probability fixed isolates the offered-price effect. The set of accepted sources also changed: Bookmaker passed at 18:01 but was excluded at 18:16 under the conservative page Last-Modified rule. Changes in probabilities therefore include source-composition effects as well as actual price moves.

Historical features are identical between runs. All seven saved probability vectors were independently reproduced using the model’s label encoder; all 21 best-price/gross-EV calculations were rechecked. Official lineups were refreshed around 18:17 UTC and retained the same starting-player IDs. Explicit lineup/injury adjustments are still absent from the model.

Withholding calculation: effective return multiple = 1 + (gross decimal odds − 1) × 0.85. EV = probability × effective multiple − 1. [URA current guidance](https://ura.go.ug/en/witholding-tax/). This is the immediate payout deduction assumption, not a comprehensive personal-tax calculation.

Inter and Villa retain positive statistical estimates but remain passes due to unmodelled selection uncertainty. Bayern also has a positive estimate but missing Olise and Musiala are not explicitly modelled. Madrid is negative after withholding at 1.27. Betis home is negative before withholding.

Companion artifacts: `ucl-prices-lineups-validated-20261021.md`, `ucl-prices-lineups-tax-check-20261021.json`, `ucl-edge-recheck-model-20261021.json`. Captured odds do not establish bet acceptance, stake limits or final net bet-slip payout. No bet was placed.
