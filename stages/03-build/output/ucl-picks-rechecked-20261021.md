# Champions League picks rechecked — 21 October 2026

Public prices observed **15:38:25–15:38:26 UTC / 18:38 Kampala**. This is a timestamped snapshot, not confirmation of an executable ticket. Final team lineups were not independently confirmed. Markets are 90 minutes plus stoppage time.

## Revised shortlist

1. **Club Brugge win at 1.94, Ababet:** the main revised value candidate. Five available consecutive wins versus Lens DLWLW. The model estimate is 56.2%, versus 51.1% de-vig consensus. Its rise is mostly caused by expanded history: at the same refreshed prices the old history gave 52.1%. Belgian opponent history remains less complete than the target club history, so the larger estimate is still experimental.
2. **Lille win at 2.30, Cloudbet:** retains tentative value, with a lower probability estimate than earlier. Current model 47.1%; de-vig market 42.3%; best-price break-even 43.5%. Mixed form WLWLD means this is a price-based candidate, and a draw or defeat is collectively more likely than a Lille win.
3. **Real Madrid win at 1.27, Ababet:** a likely-winner selection at 82.0% model probability, rather than a large value opportunity. Market consensus is 78.5%. Real have four wins in the latest five available results. The short price leaves limited margin for estimation error.

**Bayern win at 2.28, Ababet remains conditional:** raw model 49.7%, but the official club preview confirms Olise is suspended and Musiala unavailable. Neuer’s return and Kompany’s presence were unresolved in that preview. These factors are not explicitly modeled; no invented numerical adjustment has been applied. Do not treat the raw +13.4% EV as injury-adjusted value.

Sporting win at 1.29 is an alternative likely-winner lean (82.4% model, 76.5% market), subject to lineup review. Betis–Feyenoord draw at 4.72, betPawa, is the largest raw EV signal (+16.0%), but the estimated chance is only 24.6%; it stays a speculative watchlist outcome, outside the main shortlist. Betis win at 1.70 is now slightly negative EV in the model and is a pass.

## All forecasts and prices

All probabilities are experimental. H / D / A means home win / draw / away win. Best-price comparisons use accepted public sources only.

| Fixture | Model H / D / A | Best H / D / A | Home-win gross model EV | Home form / away form |
|---|---|---|---:|---|
| Como – Man United | 40.5% / 26.6% / 32.9% | 2.50 ababet / 3.92 ababet / 2.77 ababet | +1.2% | WLDLW / LDDLD |
| Lille – Galatasaray | 47.1% / 26.8% / 26.1% | 2.30 cloudbet / 3.78 ababet / 3.25 ababet | +8.4% | WLWLD / WLWLW |
| Real Madrid – RB Leipzig | 82.0% / 11.7% / 6.3% | 1.27 ababet / 8.13 betpawa / 11.00 cloudbet | +4.1% | WLWWW / WLWWL |
| Inter – Shakhtar Donetsk | 82.2% / 12.3% / 5.5% | 1.27 ababet / 7.15 betpawa / 11.60 ababet | +4.4% | WDWLW / WWWWW |
| Bayern Munich – Arsenal | 49.7% / 22.1% / 28.2% | 2.28 ababet / 3.90 ababet / 3.12 ababet | +13.4% | WWDDW / WLWWW |
| Club Brugge – Lens | 56.2% / 21.8% / 22.0% | 1.94 ababet / 4.20 ababet / 3.82 ababet | +8.9% | WWWWW / DLWLW |
| Aston Villa – Viking | 81.9% / 11.8% / 6.3% | 1.26 ababet / 7.16 betpawa / 11.90 ababet | +3.2% | WWDWW / WWWDW |
| Sp Lisbon – LASK Linz | 82.4% / 11.2% / 6.4% | 1.29 ababet / 6.96 betpawa / 10.70 ababet | +6.3% | WDDWW / LDLLW |
| Betis – Feyenoord | 58.4% / 24.6% / 17.1% | 1.70 ababet / 4.72 betpawa / 4.67 ababet | -0.8% | WDWWL / WWWWW |

## Arbitrage

No confirmed arbitrage across 27 complete book/fixture quote sets. Every best-price reciprocal sum exceeds 1. Closest: Real Madrid–RB Leipzig, sum 1.001312, gross return -0.131% before fees or taxes. Buying all three outcomes would lose money at these prices.

## What changed and what was verified

The frozen reviewed v2.1.0 model was rerun with 19,739 causal results, including the 2,757 validated results in the 18-club backfill. The 58 awarded or uncertain extra-time/penalty records remain outside modeling. Existing target-club results in the covered period were replaced, not appended on top. Cross-source opponent aliases were aligned using overlapping fixture evidence; no ambiguous proposals were applied.

The same-price comparison isolates the effect of the history changes from the price refresh. The new histories changed the biggest outcome probability by about 4.1 percentage points for Brugge and 2.4 points for Betis; the other seven fixtures changed by less than 1.7 points. This is sensitivity analysis, not a calibration result.

All nine forecasts reproduced from saved feature vectors. Market normalization, finite probability sums, model checksum, one quote per bookmaker, best-price EV and reciprocal-sum calculations passed. Bovada was rejected because its cache Age was 1,694 seconds; Bookmaker was conservatively omitted because its page’s price timestamp was over an hour old. Retained sources: betPawa, Cloudbet and Ababet.

The model was not retrained or promoted. Earlier holdout comparisons did not establish market-beating performance: model-minus-market log-loss bootstrap interval included zero. Gross EV = probability × decimal price − 1; it is conditional on model accuracy and excludes taxes, fees, limits and execution differences. Prefer tentative singles over an accumulator; no bet was placed.

Lille and Como kick off at **19:45 Kampala**; the other seven fixtures at **22:00 Kampala**. Recheck the ticket price and starting XI before any decision.

## Evidence

- [Official Bayern preview and absences](https://fcbayern.com/es/noticias/matchpreviews/2026/10/previa-champions-league-fc-bayern-fc-arsenal)
- [Galatasaray official Lille preview and traveling squad](https://www.galatasaray.org/haber/futbol/sampiyonlar-ligi/maca-dogru-lille-galatasaray/61183)
- [Real Madrid announced squad](https://www.realmadrid.com/en-US/news/football/first-team/squad-call/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)
- [Backfill coverage](ucl-history-backfill-20261021.md)
- [Forecasts and quote evidence](ucl-picks-rechecked-20261021.json)
- [Verification](ucl-picks-recheck-verification-20261021.json)
- Public sources: [Ababet](https://ababet.ug/), [Cloudbet UCL](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events), [betPawa Uganda](https://www.betpawa.ug/).
