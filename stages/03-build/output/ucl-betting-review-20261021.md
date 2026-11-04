# Champions League betting review — 21 October 2026

Prices observed 14:36:12–14:36:14 UTC (17:36 Kampala). Kickoffs are 19:45 Kampala for Como–Manchester United and Lille–Galatasaray; 22:00 for the other seven games. Markets: full-time regulation 1X2, including stoppage time.

## Findings

No confirmed arbitrage. Across the 26 usable complete book/fixture markets, the best combined reciprocal sums range from 1.007054 to 1.016501. All exceed 1; the closest combination still loses about 0.70% before costs. No bets placed.

The leading experimental value candidates are Bayern to win at 2.28 and Lille to win at 2.26, both Ababet. Bayern is conditional because Olise is suspended and the model has no player-availability features. Lille is a price-based candidate despite mixed recent results. Real Madrid at 1.27 is a stronger likely-winner selection, with a thin estimated edge. These are tentative singles, not validated profitable recommendations.

## Coverage and validation

The catalog contains 46 brands: 40 had configured URLs, 9 produced normalized football markets, and 8 had quotes for today’s UCL fixtures. SportPesa returned another competition. Five UCL sources explicitly marked markets OPEN. A second capture retained betPawa, Cloudbet and Ababet. Bovada was excluded because its HTTP Age was 554 seconds; Bookmaker’s page was last modified more than seven minutes before retrieval and is omitted conservatively. BetOnline, 1xbet and 22bet had unconfirmed market status. Other brands were inaccessible, unresolved or lacked a verified parser; coverage is not exhaustive.

Fixtures were matched by reviewed senior-team aliases, UTC kickoff within 60 seconds, regulation-time market and home/away orientation. Reversed provider listings were reoriented. Open outcome status, finite prices above 1, probability normalization, model/dataset checksums, pre-match history cutoffs and score conflicts were checked. A supplementary archive request for Viking failed; available verified Norwegian league results and European results cover its displayed form.

Cross-source duplicate matches under opponent aliases were removed before the final inference. The resulting causal history has 19005 rows. Form means the latest five available domestic-league and regulation European results; cup coverage is incomplete. Training history for LASK, Shakhtar and Brugge is much thinner than for major-league teams. This report does not claim all team history was collected.

The frozen experimental v2.1.0 model uses the previously selected uncalibrated probabilities. Its prior holdout accuracy was 52.75%; on 2,608 matched-odds games, model log loss was 0.973391 versus market 0.973767. The day-block bootstrap interval for the difference included zero (-0.003281 to +0.002485). A market-beating edge is not established. This run updates causal inputs and local identity mappings; it does not retrain, replace production, or validate tonight’s future outcomes.

Model SHA256: `148f1fafa22130e9aca5d6a75e648dfcf153087594ef29e83dd0b4c2482d9523`. Gross model EV = model probability × decimal odds − 1. It excludes tax, fees, limits, rejection and price movement. De-vig consensus is the equal-book mean of proportional margin removal; it is a benchmark rather than ground truth.

## All matches

Form is oldest to newest. The lean is the most likely model outcome, not an automatic bet. Prices are the best among retained sources.

| Fixture | Home form (GF–GA) | Away form (GF–GA) | Model H / D / A | Best H / D / A | Reciprocal sum |
|---|---|---|---|---|---|
| Como – Man United | WLDLW (7–7) | LDDLD (3–6) | 39.1% / 27.0% / 34.0% | 2.50 (ababet) / 3.92 (ababet) / 2.77 (ababet) | 1.016113 |
| Lille – Galatasaray | WLWLD (5–6) | WLWLW (6–9) | 49.1% / 25.6% / 25.4% | 2.26 (ababet) / 3.78 (ababet) / 3.25 (ababet) | 1.014720 |
| Real Madrid – RB Leipzig | WLWWW (13–8) | WLWWL (13–8) | 80.8% / 12.5% / 6.7% | 1.27 (ababet) / 7.98 (betpawa) / 10.60 (ababet) | 1.007054 |
| Inter – Shakhtar Donetsk | WDWLW (16–10) | WWWWW (13–2) | 80.3% / 13.9% / 5.8% | 1.27 (ababet) / 7.01 (ababet) / 11.60 (ababet) | 1.016262 |
| Bayern Munich – Arsenal | WWDDW (20–7) | WLWWW (8–4) | 49.4% / 21.8% / 28.7% | 2.28 (ababet) / 3.90 (ababet) / 3.12 (ababet) | 1.015520 |
| Club Brugge – Lens | LWWWW (16–8) | DLWLW (8–8) | 52.0% / 25.3% / 22.7% | 1.94 (ababet) / 4.20 (ababet) / 3.82 (ababet) | 1.015339 |
| Aston Villa – Viking | LWDWW (13–6) | WWWDW (19–6) | 81.4% / 12.2% / 6.4% | 1.26 (ababet) / 7.29 (betpawa) / 12.10 (ababet) | 1.013470 |
| Sp Lisbon – LASK Linz | WDDWW (11–5) | LDLLW (11–13) | 80.8% / 12.3% / 6.8% | 1.29 (ababet) / 6.91 (ababet) / 10.70 (ababet) | 1.013370 |
| Betis – Feyenoord | WDWWL (12–10) | WWWWW (21–5) | 60.4% / 23.8% / 15.8% | 1.70 (ababet) / 4.67 (ababet) / 4.67 (ababet) | 1.016501 |

## Candidate prices

| Selection | Decimal price | Model probability | Market de-vig probability | Break-even probability | Gross model EV |
|---|---|---|---|---|---|
| Bayern Munich win | 2.28 ababet | 49.4% | 42.8% | 43.9% | +12.7% |
| Lille win | 2.26 ababet | 49.1% | 43.2% | 44.2% | +10.9% |
| Real Madrid win | 1.27 ababet | 80.8% | 78.2% | 78.7% | +2.6% |
| Sp Lisbon win | 1.29 ababet | 80.8% | 75.9% | 77.5% | +4.3% |

These probabilities are experimental point estimates. Lineups are not confirmed. No fabricated adjustment is applied for an absent player. Sporting is an alternative likely-winner lean, but sparse LASK history and reported Sporting absences reduce confidence. Inter faces a Shakhtar side with five available consecutive wins. Betis faces a Feyenoord side with five available consecutive wins; avoid treating either favorite as a safe addition. Manchester United are winless in the displayed five, and the model does not support buying their current win price.

## Sources and evidence

- [UEFA fixtures/results](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--202627-champions-league-all-the-league-phase-fixtures-and-results/)
- [Bayern official Viking match reaction: 3–3, not 3–4](https://fcbayern.com/en/news/2026/10/reaction-to-champions-league-match-at-viking-fk)
- [Real Madrid official squad](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/convocatorias/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)
- [Lille official opponent preview](https://losc.fr/actualites/2026-10-20/la-decouverte-de-galatasaray)
- [Villa official team news](https://www.avfc.co.uk/news/2026/october/20/prematch-team-news-for-viking-visit/)
- [Olise suspension report](https://fcbinside.com/2026/10/20/gnabry-karl-or-saibari-heres-how-bayern-will-solve-the-olise-problem-against-arsenal/)
- Public prices: [Ababet](https://ababet.ug/), [betPawa Uganda](https://www.betpawa.ug/), [Cloudbet UCL](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events). Public price visibility does not establish account access or stake acceptance.
- Machine-readable review: `ucl-analysis-20261021.json`; odds captures and cache audit: `pipeline/data/raw/ucl_today_20261021_recheck/`; first catalog capture: `pipeline/data/raw/ucl_today_20261021_all_public/`; provider form: `pipeline/data/raw/team_form/ucl_20261021/`; supplementary archives: `pipeline/data/raw/ucl_today_20261021_form/`.
