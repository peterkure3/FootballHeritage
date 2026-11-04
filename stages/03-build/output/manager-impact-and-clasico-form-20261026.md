# Manager impact and the 25 October Clásico forecast

## Findings

**Team form was included in yesterday's model.** The immutable La Liga model and saved dataset reproduce the published forecast to numerical tolerance (`1e-12`): Barcelona 60.2710%, draw 15.0580%, Real Madrid 24.6710%. The model picked Barcelona and missed the eventual winner.

The [official Barcelona report](https://www.fcbarcelona.com/en/football/first-team/news/4598638/fc-barcelona-1-2-real-madrid-heartbreaking-defeat) confirms the 1–2 result and Barcelona's nine consecutive league wins before this match. Madrid's [official report](https://www.realmadrid.com/en-US/news/football/first-team/reports/cronica-barcelona-real-madrid-j10-liga-25-10-2026) identifies Mourinho's team and the winning performance. A single upset cannot isolate the contribution of either coach.

| Saved pre-match input | Barcelona | Real Madrid |
|---|---:|---:|
| Last five league results, oldest first | WWWWW | WWLWW |
| Wins / draws / losses in those five | 5 / 0 / 0 | 4 / 0 / 1 |
| Average goal difference over those five | +3.0 | +1.4 |
| Weighted form points per match, last ten | 2.8216 | 2.3549 |
| Elo before the fixture | 1868.9588 | 1768.4367 |

Form uses 3/1/0 points for a win/draw/loss, with weights `0.9 ** age_in_matches` over up to ten previous league matches. Separate features track the last five W/D/L counts and goal difference, weighted goals scored/conceded, venue performance and head-to-head results. Results from the prediction's UTC day are excluded. These are league-specific histories; Champions League form, player availability, announced lineups and manager identity were not inputs to this La Liga forecast.

The audited run is `20261025T165351114106Z`; the forecast cutoff is `2026-10-25T16:55:09.289201Z`. The saved model selected calibrated logistic regression (`C=0.01`) with 27 history features. Exact reconstruction, the feature vector and dated last-five results are in `clasico-form-audit-20261026.json`.

## What the research supports

Manager identity, tactical decisions and the circumstances of a coaching change are plausible sources of information. The average effect of changing managers is not a reliable universal positive bonus. [Bryson et al. (2024)](https://doi.org/10.1111/sjpe.12369) find little general benefit from turnover across four countries after adjusting for selection into coaching changes. [Kleinknecht and Würtenberger (2022)](https://doi.org/10.1002/mde.3419) find improvements in a Bundesliga study, with differences between internal and external successors. Their different findings underline the importance of context and controls for regression to the mean.

Predictive usefulness and causal impact are separate questions. A manager's raw win rate also reflects squad strength, opponent quality and which clubs employ them. The implementation should test incremental predictive value above form and Elo, rather than insert a hand-written Mourinho/Flick rating or change yesterday's probabilities retrospectively.

## Implemented isolated experiment

Added `pipeline/models/manager_features.py`, `pipeline/scripts/assess_manager_impact.py` and temporal/source-integrity tests. The existing Wyscout match archive contains dated native coach IDs, so this experiment needed no new scrape. Original source: Wyscout / Pappalardo et al. (2019), [Figshare collection](https://doi.org/10.6084/m9.figshare.c.4415000), CC BY 4.0. Attribution and archive SHA-256 are retained.

Five 2017/18 domestic leagues supplied 1,826 matches. Seven score/winner disagreements were quarantined, leaving **1,819 matches and 163 observed coaches**. The source has 228 missing coach-side observations. Native team IDs prevent cross-source club-name collisions.

The prototype adds 14 features: for each side, a last-observed-manager indicator, observed stint games, recently observed change, prior observed coach games, smoothed points per game and an Elo-adjusted result score; plus smoothed prior manager-pair meetings. Small samples shrink toward neutral priors. Elo-adjusted result means actual win/draw/loss score `1/.5/0` minus the pre-match Elo expected score; it is not an estimated causal coaching effect.

**Temporal protection:** current-match coach IDs enter only after that day's results. The prediction vector uses the coach last observed on a previous completed UTC day. This avoids retrospectively supplying a new coach before their first match, but cannot recognize a newly announced appointment before that first match. Missing current metadata can also leave a stale last-observed assignment. The source does not establish historical announcement timestamps, and the experiment is research-only.

Baseline inputs are the existing 27 history features plus league indicators. Both feature sets use the same model candidates, chronological partitions, tuning criterion and separate sigmoid calibration:

| Period | Matches | Dates |
|---|---:|---|
| Training | 1,079 | 4 Aug 2017–29 Jan 2018 |
| Tuning | 246 | 30 Jan–5 Mar 2018 |
| Calibration | 199 | 9 Mar–13 Apr 2018 |
| Untouched test | 295 | 14 Apr–20 May 2018 |

| Held-out result | Form + Elo | Form + Elo + manager features |
|---|---:|---:|
| Accuracy | 50.85% | 50.85% |
| Log loss, lower is better | 1.04178 | 1.03790 |
| Brier score, lower is better | 0.61598 | 0.61588 |

Both tuning procedures selected logistic regression `C=0.01`. Mean log-loss improvement is **0.00388**, with a rough week-block bootstrap 95% interval of **−0.01531 to +0.02436**. The interval includes no gain and spans only six held-out match weeks. Spain's test accuracy decreased from 47.06% to 45.59% despite a small log-loss improvement. These results do not justify adding the prototype to the serving models or claiming that manager information would have corrected the Clásico pick.

Models, source checksums, input features and held-out predictions are retained under `pipeline/data/processed/manager_research/20261026_checked/`. A compact report is `manager-ablation-20261026.json`. No serving model, existing prediction, database row or historical result was changed by this experiment.

## Production implementation path

1. Collect multi-season manager appointment and departure records with stable coach/team IDs, effective start/end dates, caretaker status, source URLs and publication/capture timestamps. Preserve revisions with `known_from`/`known_to` as well as effective dates. A team's current coach must never be backfilled into all its historical matches.
2. Resolve the assignment as it was known at the forecast cutoff, for the scheduled kickoff. Missing or ambiguous assignments remain explicitly unknown. Announced future departures and appointment revisions require the same point-in-time rules.
3. Extend this state layer with verified assignments to recognize the first game under a new manager. Add actual tenure days, games in the current tenure, prior cross-club experience, smoothed opponent-adjusted performance and sparse manager-versus-manager records. Distinguish missing coverage from a genuinely inexperienced coach. Add tactical/lineup information only when separately available before the cutoff.
4. Create a new feature-schema/model version with the same feature builder in training and inference. Persist the manager assignment, source/known timestamp and feature values with every forecast. Keep the existing 39-column contract and yesterday's stored artifacts intact.
5. Evaluate baseline versus manager-augmented models on several rolling season holdouts, checking log loss, Brier score, calibration, first-change games, missing-data cases and per-league stability. Keep test periods out of model selection. Promote only after repeatable improvement; conduct a separate matched-control/fixed-effect study if a causal turnover claim is wanted.

Verification: eight manager-specific tests plus existing league and training-resource safeguards, **18 tests passed** in the final targeted run; Python compilation and saved-model probability replay passed. Tests cover first-match leakage, same-day leakage, future outcomes/coaches, unknown IDs, change timing, pair orientation, unfinished results, quarantine and checksum tampering. Repository Fallow baseline and post-change audits were saved separately.
