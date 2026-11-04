# Champions League edge assessment — 20 October 2026

Research checked around 17:06–17:10 UTC / 20:06–20:10 EAT. Public web snapshots are research observations, not streaming or executable quotes. User requested broad public-bookmaker coverage. No bets placed. No production code or model changed.

## Decision

No executable arbitrage verified. Comparison pages expose theoretical candidates, but direct exchange observations contradict some advertised prices and show suspended markets. Do not combine these snapshots into an executable staking plan. No statistic can ensure a win.

## Fixtures

[UEFA fixture list](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fixtures-a/), corroborated by [PSG's fixture notice](https://www.psg.fr/en/content/fixtures-for-matchday-3-of-the-uefa-champions-league-psg-v-barcelonacalendrier-2026-2027).

Fenerbahce–Slavia Prague and Sabah–Dortmund: 19:45 EAT. Already past scheduled kickoff during research; exclude pre-match quotes.

All remaining fixtures: 22:00 EAT. Roma–Slovan Bratislava; Porto–PSV; Liverpool–Villarreal; Manchester City–AEK Athens; PSG–Barcelona; Napoli–Bodo/Glimt; Stuttgart–Atletico Madrid.

## Screening method

For decimal 90-minute 1X2 odds, S = 1/home + 1/draw + 1/away. Gross theoretical equal-return ROI = 1/S - 1. Positive values require simultaneous available back prices, identical settlement terms and adequate accepted stakes. Fees, tax, rounding, currency conversion and void rules remain additional constraints.

Use a single bookmaker's complete 1X2 line to derive a market benchmark: p_i = (1/O_i) / sum_j(1/O_j). Here Pinnacle lines were reported by OddStorm; they were not independently authenticated on Pinnacle. Proportional margin removal is a simple benchmark, not an independent calibrated prediction or proof of true expected value. Longshot estimates are particularly sensitive to margin-removal assumptions.

## Theoretical candidates — unverified

| Match | Home / draw / away | Listed providers | Gross ROI |
|---|---|---|---:|
| Napoli–Bodo | 1.82 / 4.30 / 4.90 | 1xBet / yabo / Betfair Exchange | 1.411% |
| City–AEK | 1.17 / 11.00 / 22.00 | 1xBet / Betfair Exchange / Betfair Exchange | 0.902% |
| Porto–PSV | 1.57 / 5.00 / 6.30 | 1xBet / Betfair Exchange / Saba Sports | 0.435% |
| PSG–Barcelona | 2.56 / 4.75 / 2.52 | Betfair Exchange / Sesame / 1xBet | 0.203% |
| Stuttgart–Atletico | 3.55 / 4.05 / 2.13 | Betfair Exchange / yabo / 1xBet | 0.192% |

Sources are the complete comparison pages linked below. Roma 1.14/11/28 and Liverpool 1.53/5/6.60 did not form gross arbitrages in their complete-table snapshots. An earlier Roma summary displayed 1.15; do not mix that with a later table.

At hypothetical 2% commission and rebalanced stakes, Napoli's advertised combination would yield about 1.072% before other costs; at 5%, about 0.548%. These figures are hypothetical because the back price was not verified. For City, commission must apply to aggregate net winnings from both exchange bets in the same market, not separately to each winning selection. Its rebalanced hypothetical ROI is about 0.658% at 2% commission and 0.279% at 5%. [Betfair charges](https://www.betfair.com/aboutUs/Betfair.Charges/) establish that commission is on net market winnings; the actual rate depends on the account.

### Direct check invalidates treating the Napoli candidate as confirmed

[Betfair Napoli–Bodo](https://www.betfair.com/exchange/plus/no/fotball/uefa-champions-league/napoli-bodo-glimt-spilling-36194557) returned a suspended market snapshot with these ladders:

- Napoli back 1.80/1.81/1.82, lay 1.84/1.85/1.86.
- Bodo back 4.30/4.40/4.50, lay 4.70/4.80/4.90.
- Draw back 4.00/4.10/4.20, lay 4.30/4.40/4.50.

Thus 4.90 was a lay quote in this observation, not a confirmed available back quote. This does not establish the cause of the aggregator discrepancy: stale data or different snapshots may also contribute. Replacing the advertised Bodo 4.90 with 4.50, while provisionally retaining the external home/draw quotes, gives S = 1.00423 and negative gross ROI of approximately -0.421%. That is a sensitivity illustration, not a synchronized market comparison.

[Betfair City–AEK](https://www.betfair.com/exchange/plus/no/fotball/uefa-champions-league/man-city-aek-athens-spilling-36194579) also returned a suspended snapshot with different prices. It cannot authenticate the comparison-page opportunity.

## Directional shortlist

These are conditional research candidates, not validated positive-EV bets. The benchmark uses the complete-table Pinnacle line in each cited comparison. All EV estimates below exclude tax and transaction costs.

| Selection | Observed price | Benchmark probability | Fair odds | Benchmark EV | Assessment |
|---|---:|---:|---:|---:|---|
| Napoli win | 1.82, 1xBet | 55.72% | 1.795 | +1.41% | Best modest-odds candidate; thin edge. Prefer 1.85+ for about 3.09% benchmark EV. |
| PSG–Barcelona draw | 4.75, Sesame | 21.68% | 4.612 | +2.99% | Speculative; needs independent corroboration. |
| Slovan Bratislava win | 28.00, 1xBet | 4.05% | 24.719 | +13.27% | Longshot discrepancy to investigate, not a high-confidence pick. Benchmark still implies about 96% losing probability. |

Liverpool win at 1.53 falls below benchmark fair odds of 1.565. City win at 1.17 falls below 1.187. Porto win at 1.57 is essentially fair against 1.569. Atletico win at 2.13 is essentially fair against 2.130. PSG win at 2.56 is slightly below 2.569 fair odds before exchange commission. A likely winner need not be a good price.

Official team news: [Liverpool](https://www.liverpoolfc.com/news/liverpool-v-villarreal-team-news-champions-league) confirms Frimpong and Szoboszlai unavailable; [Barcelona](https://www.fcbarcelona.com/en/football/first-team/news/4594024/medical-updates-on-eric-and-kounde) confirms Eric Garcia and Kounde unavailable. These are known information and may already be priced. They do not justify adding an arbitrary probability adjustment. Starting lineups were not verified during this research.

## Proposed statistic: Edge Survival Score (ESS)

This is a newly named composite decision rule, not a claim of a novel mathematical discovery or demonstrated forecasting advantage.

For a binary win/lose bet with stake returned in the decimal payout:

ESS = 100 × [p_low × O_net − 1 − k]

- p_low: conservative probability from predeclared plausible model/lineup scenarios, with uncertainty estimated from historical calibration. Use independent market consensus as a cross-check; exclude the offered bookmaker from that consensus. Do not invent a confidence bound from one quote.
- O_net: effective decimal payout after applicable profit commission. A standalone exchange back bet has O_net = 1 + (O − 1)(1 − c). A multi-bet exchange position needs outcome-level net-market accounting.
- k: other costs per unit stake, counted once. Outcome-dependent taxes/costs require explicit outcome cash flows instead of this simplification.

Positive ESS means estimated value survives the declared conservative scenario. Negative ESS means pass. The minimum across scenarios is not a formal statistical guarantee or confidence bound.

Illustration only: Napoli benchmark p = 0.557225 and price 1.82 give ordinary benchmark EV +1.415%. Applying a hypothetical two-percentage-point probability haircut gives p_low = 0.537225 and ESS = -2.225% before additional costs. The haircut is an example, not an estimated uncertainty interval for tonight.

Validation required before using ESS for stakes: preregister scenario rules and cutoffs; use chronological walk-forward evaluation with only timestamped information available before kickoff; compare against ordinary EV and no-bet baselines; record closing-line value, Brier/log loss, after-cost ROI, drawdown and confidence intervals clustered by match; retain an untouched holdout. No backtest or improvement claim was made here.

## Comparison sources

- [Roma complete prices](https://www.oddstorm.com/odds/match/13639102-as-roma-vs-slovan-bratislava/1x2)
- [Liverpool complete prices](https://www.oddstorm.com/odds/match/13639101-liverpool-vs-villarreal/1x2)
- [City complete prices](https://www.oddstorm.com/odds/match/13639090-manchester-city-vs-aek-athens/1x2)
- [Napoli complete prices](https://www.oddstorm.com/odds/match/13639103-napoli-vs-bodo-glimt/1x2)
- [PSG complete prices](https://www.oddstorm.com/odds/match/13639097-paris-saint-germain-vs-barcelona/1x2)
- [Porto complete prices](https://www.oddstorm.com/odds/match/13639100-porto-vs-psv-eindhoven/1x2)
- [Stuttgart complete prices](https://www.oddstorm.com/odds/match/13639099-vfb-stuttgart-vs-atletico-madrid/1x2)

## Verification and limitations

Arithmetic reproduced in the tool runtime. Official fixture and club-news sources checked, comparison prices read, two direct exchange pages inspected. No authenticated betslip, current stake limits, account commission/tax treatment or simultaneous executable prices verified. Coverage is a public-source sample across approximately two dozen listed providers, not every bookmaker or market. Local command execution was intermittent; no local model or database probabilities were obtained. Existing unrelated working-tree changes were left untouched.
