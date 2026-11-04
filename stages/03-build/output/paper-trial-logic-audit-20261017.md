# Paper-trial logic audit — 17 October 2026

Read-only audit at 15:28 UTC / 18:28 EAT. No model, selection policy, forecast or settlement was changed.

## Recomputed state

The automatic Bovada EPL study has nine batches, 30 fixtures, 22 valid forecasts and eight model-input exclusions. Twelve forecasts meet its selection rule: six settled and six pending. Ten valid forecasts have no selection. Nine forecasts have final results: six selections and three abstentions. The settled selected bets span two UTC fixture dates, with -0.25 paper units (-4.17% ROI; -6.08% stressed ROI). All 12 selected outcomes agree with the largest-stressed-EV rule; no decision mismatches found.

The separate manual study contains the Newcastle away-win choice at Coventry on 12 October, AbaBet price 2.05. It settled as a loss (-1 paper unit), with recorded final score Coventry 4–1 Newcastle. It is excluded from the automatic study because its user-selected policy, active-model context and bookmaker differ. The original frozen Bovada candidate abstained: its Newcastle stressed EV was 4.291789%, below 5%. The manual active-model context estimated 31.279667% stressed EV at its actual 2.05 price; that is a different probability source, not the frozen candidate's decision.

## Rules

Only England Premier League, Bovada, regulation-time home/draw/away markets enter the automatic study. Candidate `20261009T100528981075Z` and its artifacts are fixed. A quote must be complete, recorded within 900 seconds, and observed/generated before kickoff and after training/history. Choose at most one outcome per fixture: maximize `probability * decimal_odds * 0.98 - 1`; select only when that value is at least 0.05. Outcomes need not be the most likely winner. One unit per selection. Pending/excluded/unselected fixtures do not increase the settled-selection denominator.

Formal assessment requires both 200 settled selections and 60 distinct UTC fixture dates, complete settlement through the qualifying cohort day, exact policy/book/manifest, and verified official result evidence. Its stressed ROI 95% interval must have a lower bound above zero to pass the paper-evidence assessment. No model is automatically promoted.

## Confirmed problems and restrictions

1. All eight missing-history exclusions involve provider names absent from the key lookup even though the clubs exist in the saved history. Missing mappings: `Brighton & Hove Albion` → existing `brighton`; `Sunderland` → existing `sunderland afc`; `Hull City` → existing `hull city afc`. This is a real input-normalization defect, not evidence that the clubs lack history. It does not establish that those fixtures would pass the EV threshold.
2. `continue_frozen_trial` marks every row in previous automatic batches seen, including exclusions and no-selection forecasts. Later prices and corrected data are never reconsidered for that fixture. Thus early failures persist and early abstentions cannot become later selections. This is a first-observation policy, not a continuously scanning eligibility strategy.
3. On 15 October the collector recorded upcoming fixtures as far ahead as 25 October. A quote's 15-minute freshness is measured at recording, not relative to kickoff. First-observation locking therefore freezes prices/decisions days early; this is permitted by the present code but poorly conveyed in the UI.
4. Scope is one league/book/soccer candidate. NBA/NFL/other leagues, regional-book prices and active-model probability/EV comparisons do not feed this study. Many games elsewhere do not increase its counter.
5. Collector is currently operational: scheduled task enabled every 15 minutes; latest audited run succeeded at 15:25:19 UTC. It is not presently stalled. The six pending selections are dated 17, 18, 23, 24 and 25 October; at audit time the selected 14:00 UTC match on 17 October had started 89 minutes earlier and did not yet have a final settlement.
6. UI labels show settled progress and batch rows, but lack a concise coverage funnel and an explicit first-observation decision timestamp, making abstentions/exclusions/pending picks look like missing selections.

Recommended follow-up: repair provider-name mapping at the candidate input boundary; preserve historical immutable records; separately version any change to first-observation timing or retry/selection rules; expose coverage, skip reasons and recorded-versus-settled counts. Do not silently lower EV thresholds, mix manual picks into the model denominator, or reconstruct pregame selections after results are known.

Evidence: `paper-trial-audit-20261017.json`, `paper-trial-coverage-20261017.json`, current scheduler/log inspection and read-only audit scripts in this directory. The official-feed comparison contains unresolved alias variants and must not be read as an exact count of genuinely unrecorded fixtures.
