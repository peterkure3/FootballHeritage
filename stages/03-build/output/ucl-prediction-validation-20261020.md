# Validation of Champions League shortlist — 20 October 2026

Checked after 17:12 UTC, before the 19:00 UTC fixtures. This is a pre-match robustness audit, not outcome validation or historical model validation.

## Verdict

No selection is established as a robust positive-EV bet. Withdraw Slovan as a betting recommendation. Napoli remains a conditional price watch; PSG–Barcelona draw remains unverified. No executable arbitrage confirmed. The earlier probabilities were bookmaker-derived benchmarks, not calibrated independent predictions.

## Reproduced calculations

Reference 1X2 odds from the earlier reported Pinnacle snapshots:

- Napoli: 1.74 / 4.07 / 4.74; selected home at offered 1.82.
- PSG–Barcelona: 2.49 / 4.47 / 2.46; selected draw at offered 4.75.
- Roma–Slovan: 1.12 / 9.92 / 23.87; selected away at offered 28.00.

Proportional margin removal: p_i = q_i / sum(q), q_i = 1/O_i.
Power margin removal: p_i = q_i^k, choosing k so sum(q_i^k) = 1. Computed by 100 bisection iterations between k=1 and k=5, which bracket these examples.
EV = p * offered_decimal_odds - 1, excluding costs.

| Selection | Break-even chance | Proportional chance / EV | Power chance / EV | Probability decrease erasing proportional edge |
|---|---:|---:|---:|---:|
| Napoli win at 1.82 | 54.945% | 55.723% / +1.415% | 56.454% / +2.745% | 0.777 percentage points |
| PSG–Barcelona draw at 4.75 | 21.053% | 21.681% / +2.987% | 21.379% / +1.548% | 0.629 percentage points |
| Slovan win at 28 | 3.571% | 4.046% / +13.274% | 3.219% / -9.868% | 0.474 percentage points |

Slovan's sign reversal demonstrates sensitivity to probability estimation. Power removal does not prove its true probability, but the disagreement invalidates treating +13.3% as robust. Additive removal also gives negative Slovan EV (-15.885%).

[Primary methods paper: Clarke, Kovalchik and Ingram (2017)](https://www.sciencepg.com/article/10.11648/10026106) discusses proportional and power approaches and favorite-longshot bias. Its historical results do not validate tonight's predictions.

## Independent price cross-check

[Oddschecker Napoli](https://www.oddschecker.com/football/champions-league/napoli-v-bodo-glimt/winner) returned best-summary 10/13 = 1.76923, with page timestamp 20 October 17:04 (page timezone not independently established).
[Oddschecker PSG–Barcelona](https://www.oddschecker.com/football/champions-league/psg-v-barcelona/winner) returned draw 7/2 = 4.50, timestamp 17:05.
[Oddschecker Roma–Slovan](https://www.oddschecker.com/football/champions-league/roma-v-slovan-bratislava/winner) returned Slovan 22/1 = 23.00, timestamp 16:52.

Holding the old proportional probabilities fixed, these respective prices imply EV of -1.414%, -2.434% and -6.953%. These are sensitivity calculations, not synchronized fresh probability estimates. Different operator coverage and snapshots can explain discrepancies; this does not prove all earlier offers have disappeared. OddStorm could not be reopened during this audit, so its old quotes were not reconfirmed.

Oddschecker's displayed AI estimates are unaudited third-party outputs. They are not a substitute for an independently tested model or evidence of calibration.

## Squad and execution checks

[Napoli official squad](https://sscnapoli.it/sscn-i-convocati-per-il-match-contro-il-bodo-glimt/) confirms Hojlund, De Bruyne, McTominay, Lobotka and other named players in the matchday squad. This does not confirm the starting XI or provide an estimated probability adjustment.
[Barcelona official medical update](https://www.fcbarcelona.com/en/football/first-team/news/4594024/medical-updates-on-eric-and-kounde) confirms Eric Garcia and Kounde unavailable. No quantified injury-model adjustment was available.

[Betfair Napoli–Bodo](https://www.betfair.com/exchange/plus/no/fotball/uefa-champions-league/napoli-bodo-glimt-spilling-36194557) again returned a suspended snapshot: Bodo best back 4.50, lay ladder including 4.90. Therefore the earlier advertised 1.82/4.30/4.90 combination remains unverified. No authenticated betslip or accepted stakes were obtained.

## ESS status

The proposed Edge Survival Score has no demonstrated predictive or profitability benefit. It is a decision-rule proposal requiring chronological holdout testing. At Napoli 1.85, old benchmark EV is +3.087%, but an illustrative two-percentage-point probability haircut changes EV to -0.613% before other costs. Thus the earlier 1.85 threshold alone is not sufficient validation.

## Limits

No outcomes yet available for these three fixtures during checking. No local database or model was accessed because command execution failed with a process-helper setup error. No calibration, historical ROI, confidence interval or win guarantee can be claimed. Arithmetic was executed and reproduced in the tool runtime. This report records the downgrade of the earlier shortlist.
