# Champions League simulations: 3–4 November 2026

Generated 2026-10-30T21:15:12.776917+00:00 (UTC). All forecasts settle in regulation time. 20,974 completed fixtures; 100,000 score simulations per match; seed 20261103.

Official fixtures: https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fix/

## Model evaluation

| Model / evaluation | Held-out games | Accuracy | Log loss | Baseline log loss |
|---|---:|---:|---:|---:|
| Outcome classifier, Champions League subset | 207 | 55.6% | 0.9550 | 1.0253 |
| Outcome classifier, all competitions | 3943 | 51.4% | 0.9975 | — |
| Goal model, Champions League subset | 207 | 55.6% | 0.9666 | 1.0241 |
| Goal model, all competitions | 3943 | 51.6% | 0.9957 | — |

Cross-competition training is used because 557 UCL-only games are below the league trainer’s 1,000-game minimum. The configured official API account returned 403 for older seasons. No guard was lowered. Hyperparameters were selected on chronological tuning data; calibration and final test periods are separate. Outcome baselines use development-period class frequencies; the goal baseline uses development-period mean home/away goals. These are not sportsbook benchmarks and do not establish a profitable edge.

## Match forecasts

Form is oldest → newest. It uses five available verified regulation results; coverage is not exhaustive for every cup. H/D/A are the outcome classifier probabilities. Expected goals are the goal model’s home/away means, not shot-based xG. Over 2.5 and BTTS come from the goal simulations.

| EAT kickoff | Match | Form H / A | H / D / A | Expected goals H–A | Total | Over 2.5 | BTTS |
|---|---|---|---|---|---:|---:|---:|
| 03 Nov 20:45 | Shakhtar Donetsk – Sporting CP | WWWLD / DWWLL | 29% / 19% / 51% | 1.11–1.55 | 2.67 | 50% | 53% |
| 03 Nov 20:45 | Galatasaray – Stuttgart | WLWWW / WWLDL | 39% / 22% / 38% | 1.57–1.47 | 3.04 | 59% | 61% |
| 03 Nov 23:00 | Atlético Madrid – Bayern Munich | WWWDW / DDWDW | 20% / 16% / 64% | 1.06–2.20 | 3.26 | 63% | 58% |
| 03 Nov 23:00 | Barcelona – Aston Villa | WWWLL / DWWWW | 62% / 19% / 19% | 2.55–1.21 | 3.77 | 72% | 65% |
| 03 Nov 23:00 | Bodø/Glimt – Lille | WWWLL / WLDLD | 47% / 21% / 32% | 1.52–1.18 | 2.70 | 51% | 54% |
| 03 Nov 23:00 | Feyenoord – Inter | WWWLD / LWWWW | 38% / 20% / 42% | 1.57–1.68 | 3.25 | 63% | 64% |
| 03 Nov 23:00 | LASK – Slovan Bratislava | LLWWL / LWLDW | 52% / 23% / 26% | 1.88–1.24 | 3.11 | 60% | 60% |
| 03 Nov 23:00 | Man United – Roma | DLDLL / LWWDW | 34% / 20% / 46% | 1.35–1.63 | 2.98 | 57% | 60% |
| 03 Nov 23:00 | Villarreal – PSG | LWDLW / WWWWW | 20% / 19% / 61% | 1.07–2.19 | 3.26 | 63% | 58% |
| 04 Nov 20:45 | Fenerbahçe – Liverpool | WLWDL / LWWWW | 35% / 19% / 46% | 1.46–1.77 | 3.22 | 62% | 64% |
| 04 Nov 20:45 | AEK – Real Madrid | WWLLW / WWWWW | 30% / 18% / 52% | 1.40–1.91 | 3.31 | 64% | 64% |
| 04 Nov 23:00 | Dortmund – Betis | DLDWW / WWLWD | 52% / 21% / 28% | 1.59–1.07 | 2.66 | 49% | 52% |
| 04 Nov 23:00 | Porto – Napoli | WWLLW / LLWDW | 54% / 21% / 25% | 1.72–1.07 | 2.79 | 53% | 54% |
| 04 Nov 23:00 | PSV – Club Brugge | WLLWD / WWWWW | 55% / 19% / 26% | 2.03–1.31 | 3.33 | 64% | 63% |
| 04 Nov 23:00 | RB Leipzig – Man City | WWLLW / WLWWL | 29% / 17% / 54% | 1.39–2.05 | 3.44 | 67% | 65% |
| 04 Nov 23:00 | Lens – Como | WLWLW / LWWWW | 32% / 21% / 47% | 1.27–1.60 | 2.87 | 55% | 57% |
| 04 Nov 23:00 | Slavia Praha – Arsenal | WLDDD / WWWDW | 17% / 20% / 63% | 0.85–1.99 | 2.84 | 54% | 49% |
| 04 Nov 23:00 | Viking – Sabah | WDWLW / DWWLD | 55% / 20% / 25% | 2.10–1.23 | 3.33 | 65% | 62% |

## Captured markets

Prices were collected around 23:56 EAT on 30 October to 00:00 EAT on 31 October. Cloudbet and BetPawa returned 18 UCL fixtures each; Stake exposed 10 fixtures in its public initial page. Only exact kickoff and oriented team-pair matches with open, complete regulation-time markets enter the comparison. Some source names or kickoff mismatches may therefore reduce usable coverage. SportPesa’s response did not supply matching UCL prices. ForteBet’s API was disallowed by its robots policy; its desktop page supplied a shell without verified prices.

| Match | Model lean | Probability | Best captured price | Break-even fair odds | Books matched |
|---|---|---:|---|---:|---|
| Shakhtar Donetsk – Sporting CP | Sporting CP | 51.2% | 2.00 (betpawa) | 1.95 | betpawa, cloudbet |
| Galatasaray – Stuttgart | Galatasaray | 39.4% | 2.24 (betpawa) | 2.54 | betpawa, cloudbet |
| Atlético Madrid – Bayern Munich | Bayern Munich | 63.6% | 2.00 (betpawa) | 1.57 | betpawa, cloudbet, stake |
| Barcelona – Aston Villa | Barcelona | 62.2% | 1.23 (betpawa) | 1.61 | betpawa, cloudbet, stake |
| Bodø/Glimt – Lille | Bodø/Glimt | 46.6% | 1.80 (cloudbet) | 2.15 | cloudbet, stake |
| Feyenoord – Inter | Inter | 41.7% | 1.71 (betpawa) | 2.40 | betpawa, cloudbet, stake |
| LASK – Slovan Bratislava | LASK | 51.7% | 1.43 (betpawa) | 1.93 | betpawa, cloudbet |
| Man United – Roma | Roma | 45.7% | 2.71 (betpawa) | 2.19 | betpawa, cloudbet, stake |
| Villarreal – PSG | PSG | 61.2% | 1.62 (betpawa) | 1.63 | betpawa, cloudbet |
| Fenerbahçe – Liverpool | Liverpool | 46.1% | 1.61 (betpawa) | 2.17 | betpawa, cloudbet |
| AEK – Real Madrid | Real Madrid | 52.0% | 1.29 (betpawa) | 1.92 | betpawa, cloudbet, stake |
| Dortmund – Betis | Dortmund | 51.8% | 1.81 (betpawa) | 1.93 | betpawa, cloudbet |
| Porto – Napoli | Porto | 54.3% | 2.23 (betpawa) | 1.84 | betpawa, cloudbet |
| PSV – Club Brugge | PSV | 55.0% | 2.13 (betpawa) | 1.82 | betpawa, cloudbet |
| RB Leipzig – Man City | Man City | 53.5% | 1.50 (betpawa) | 1.87 | betpawa, cloudbet |
| Lens – Como | Como | 47.2% | 2.18 (betpawa) | 2.12 | betpawa, cloudbet |
| Slavia Praha – Arsenal | Arsenal | 63.4% | 1.33 (betpawa) | 1.58 | betpawa, cloudbet |
| Viking – Sabah | Viking | 54.7% | 1.47 (betpawa) | 1.83 | betpawa, cloudbet |

Nominal 1X2 arbitrage found: **0 of 18 games**. This compares the best price on each of the three mutually exclusive outcomes. Taxes, fees, stake limits and price movement are excluded. Model-based EV values in the JSON are exploratory, not verified betting recommendations.

## Verification and limits

- Every team has five available results on distinct dates, and its newest result is dated 23 October or later.
- Ambiguous same-day senior appearances were quarantined; see the CSV in the raw capture folder. Conflicting score labels were also screened.
- Both saved models replayed held-out predictions. Monte Carlo outcome estimates agree with analytical Poisson probabilities within 0.8 percentage points.
- 24 existing causal-feature and fixture-identity checks passed.
- No serving model, registry or database was changed.
- Lineups, injuries and weather are not fitted inputs. Weekend matches before these UCL fixtures have not yet been played.
- Some clubs have sparse historical coverage. Model/market disagreement does not by itself establish value.
- The score simulation assumes independent Poisson goal counts; 100,000 draws reduce simulation noise, not forecasting error.

Candidate: `pipeline\models\model_store\candidates\ucl_nextweek_20261030_final`.
Full probabilities, team-form match logs, captured odds, EV calculations, model evaluation and source links: `ucl-nextweek-predictions-20261030.json`.
Table export: `ucl-nextweek-predictions-20261030.csv`. Integrity checks and source hashes: `ucl-nextweek-verification-20261030.json`.
