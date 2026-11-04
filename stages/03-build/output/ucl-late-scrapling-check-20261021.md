# UCL public sportsbook and form review — 21 October 2026

Public prices captured with Scrapling at 17:24:24–17:24:38 UTC (20:24 Kampala). All seven remaining games kick off at 19:00 UTC / 22:00 Kampala. These are captured public offers; account acceptance, limits and final bet-slip prices were not verified.

## Finding

No regulation-time 1X2 arbitrage among the accepted sources. Club Brugge, Sporting CP and Real Madrid are the main experimental watchlist. The model has no statistically established advantage over the market; no pick or combination ensures a win. Final starting lineups were not verified. No bet was placed.

## Source checks

Refreshed betPawa Uganda, Cloudbet, Ababet Uganda, Bovada and Bookmaker. Only the first three passed this review’s conservative freshness rules. Bovada returned upstream Age=952 seconds. Bookmaker’s page Last-Modified was 17:00:38 UTC; its exclusion is a conservative page-timestamp rule, not proof of when its individual odds changed. This is not an exhaustive claim about all public bookmakers.

Accepted only complete, open, pre-match HOME/DRAW/AWAY markets, matched to the fixture and kickoff with regulation-time settlement. Como–Manchester United and Lille–Galatasaray were excluded because kickoff had passed.

## Model and history

Used the separately reviewed v2.1.0 research candidate, not the active site’s v2.0.0. Repriced its saved causal history features with new consensus prices; did not retrain, recalibrate or promote a model. Historical inputs contain 19,739 merged fixtures, including 2,757 usable regulation results from the expanded target-team history across the last three seasons plus the current season. Another 58 ambiguous regulation results were withheld. No results from tonight entered these historical features.

Prior matched-odds holdout log loss: model 0.97339074 versus market 0.97376709. The bootstrap difference interval [-0.003281, +0.002485] includes zero. Positive estimated EV below is therefore a research signal, not a demonstrated profitable betting system. The model incorporates odds and team performance history but has no explicit player-availability features.

## Remaining matches

Form is the last five available competitive results, oldest to newest. Cross-league winning runs do not imply equal opponent strength.

| Home / away | Home form / away form | Best home price | Model home chance | De-vig market home chance | Model gross EV |
|---|---|---:|---:|---:|---:|
| Real Madrid / RB Leipzig | WLWWW / WLWWL | 1.27 ababet | 81.7% | 78.2% | +3.7% |
| Inter / Shakhtar Donetsk | WDWLW / WWWWW | 1.27 ababet | 82.0% | 77.1% | +4.1% |
| Bayern / Arsenal | WWDDW / WLWWW | 2.28 ababet | 49.7% | 43.0% | +13.4% |
| Club Brugge / Lens | WWWWW / DLWLW | 1.94 ababet | 56.5% | 51.3% | +9.6% |
| Aston Villa / Viking | WWDWW / WWWDW | 1.31 ababet | 80.4% | 75.8% | +5.3% |
| Sporting CP / LASK | WDDWW / LDLLW | 1.37 ababet | 78.0% | 71.8% | +6.9% |
| Real Betis / Feyenoord | WDWWL / WWWWW | 1.68 ababet | 57.9% | 58.1% | -2.8% |

EV = model probability × decimal odds − 1, before fees and taxes. De-vig market chance is the mean of each accepted book’s normalized implied probabilities.

## Selection review

- Club Brugge win at 1.94 Ababet: strongest combination of a sizeable model estimate and recent form (five wins). Lens recovered with a 3–1 win at Troyes after losing 0–2 to Sporting. Lens’s official preview confirms Brugge’s 4–3 win at Inter but also notes Brugge conceded at least three in four of its previous five home Champions League games. This remains a material risk.
- Sporting CP win at 1.37 Ababet: unbeaten in the last five available results (WDDWW), compared with LASK’s LDLLW. The estimate fell from roughly 82% in the earlier price review to 78% as the market moved. Do not treat a better offered price alone as evidence of better underlying prospects.
- Real Madrid win at 1.27 Ababet: four wins from five, while Leipzig’s latest result was a 1–6 defeat to Bayern. Real’s announced squad includes Mbappe, Vinicius and Bellingham; this is squad availability, not a verified starting XI. The estimated margin is smaller than Brugge’s and Sporting’s.
- Aston Villa win at 1.31 and Inter win at 1.27, both Ababet: secondary signals. Viking are unbeaten in five available results and held Bayern 3–3; Shakhtar have five consecutive wins. Those opponent runs temper confidence.
- Bayern win at 2.28 Ababet: hold despite approximately +13.4% raw model EV. Bayern officially confirms Olise suspended and Musiala unavailable; the model has no explicit features for these absences. Neuer’s participation was still a match-day decision in the official preview.
- Real Betis home win at 1.68: pass; model EV is negative. The Betis–Feyenoord draw at 4.76 Ababet shows approximately +17.7% model EV but only a 24.7% estimated chance; retain as a speculative research signal, not a main selection.

## Arbitrage

| Match | Sum of best inverse odds | Theoretical equal-return ROI |
|---|---:|---:|
| Real Madrid / RB Leipzig | 1.003624 | -0.361% |
| Inter / Shakhtar Donetsk | 1.015654 | -1.541% |
| Bayern / Arsenal | 1.015520 | -1.528% |
| Club Brugge / Lens | 1.009969 | -0.987% |
| Aston Villa / Viking | 1.008095 | -0.803% |
| Sporting CP / LASK | 1.015525 | -1.529% |
| Real Betis / Feyenoord | 1.015406 | -1.517% |

Every reciprocal sum exceeds 1, so there is no nominal arbitrage in these captured prices. Fees, limits, price changes and settlement mismatches could only make execution harder.

## Evidence and verification

Source capture: `D:\Github\FootballHeritage\pipeline\data\raw\ucl_revision_20261021T172420Z`. Machine output: `ucl-late-scrapling-check-20261021.json`. Independent replay: `ucl-late-scrapling-verification-20261021.json`.

Verified model class order, reproduced all seven probability vectors, checked all 21 best-price and EV calculations, recomputed seven de-vig vectors and seven arbitrage calculations, and checked 21 complete bookmaker quotes. These checks validate the calculations and retained inputs, not future match outcomes.

- [RC Lens official match preview](https://www.rclens.fr/fr/club-brugge-kv-rclens)
- [Bayern official availability and match preview](https://fcbayern.com/es/noticias/matchpreviews/2026/10/previa-champions-league-fc-bayern-fc-arsenal)
- [Real Madrid official squad](https://www.realmadrid.com/en-US/news/football/first-team/squad-call/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)
- [Ababet public page](https://ababet.ug/)
- [betPawa Uganda](https://www.betpawa.ug/)
- [Cloudbet Champions League](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events)
