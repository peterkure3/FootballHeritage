# First prospective NBA results

The goal was resumed after time advanced. This turn made progress: six previously
frozen NBA fixtures are now settled, captured and independently corroborated.
The objective remains active; production models are unchanged. Nothing staged
or committed. No automatic task was added.

## Frozen model comparison

| Arm | Correct / settled | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| Original model | 4 / 6 | 66.67% | 0.638538 | 0.446654 |
| Frozen inactivity candidate | 5 / 6 | 83.33% | 0.540610 | 0.352891 |

The candidate correctly selected Philadelphia away against Charlotte, where the
original selected Charlotte. Both missed New Orleans against Atlanta. Both got
Memphis, Cleveland, San Antonio and Houston right. Predictions were recorded
before kickoff; no refitting or prediction regeneration occurred.

This is encouraging early evidence, not a reliable accuracy gain. Only six
unique games have settled across two UTC dates (one US evening). The study's
review policy is at least 200 settled fixtures over 20 match days, followed by
review rather than automatic promotion. Fifty-one original batch fixtures remain
pending. Do not use this small result to change the candidate parameters.

## Separate freshness hypothesis

On the same six games, stale and refreshed history both selected four winners
correctly. Refreshed inputs improved log loss from 0.730563 to 0.649264 and Brier
from 0.531595 to 0.457204. This uses the original weights and different input
availability rules from the model experiment. These are overlapping studies,
not twelve independent settled games or one pooled comparison.

## Evidence and checks

Each study was assessed with captured ESPN responses and recomputed through the
cumulative evaluator. There were no source errors and no duplicate forecasts
counted. Reports:

- `pipeline/data/processed/nba_model_shadow/study-20261101T045859Z.json`
- `pipeline/data/processed/nba_accuracy_shadow/study-20261101T045859Z.json`
- `stages/04-test/output/accuracy-nba-prospective-20261101.json`

The primary results capture at around 05:01 UTC contains 88 finals and four
ineligible entries. The subsequent independent reconciliation matched 87;
provider ID `21717857` remains excluded for lacking an exact independent fixture.
All six prospective finals match primary identity, exact kickoff and scores.
Raw/normalized hashes and forecast-before-kickoff checks passed. Frozen trial
files and existing training artifacts were not changed. No code changed in this
turn, so existing tests were not needlessly rerun.

## Remaining work

The new history is in `pipeline/data/raw/research/nba_results_20261101/`.
Before making another batch, preserve the earliest verified observation time
for unchanged results from the earlier capture. Replacing it with today's
recapture timestamp would distort replay of the candidate's state transitions.
If scores, fixture identity or kickoff changed, the corrected data must retain
the newer observation time. Each carried timestamp needs links to verified
earlier source receipts; this must never become invented historical availability.
The new capture has not yet been used to generate another batch.

The parallel NFL investigation found an existing 855-game efficiency artifact
with a 120-game test. Its 61.67% headline accuracy cannot be compared to the main
NFL model's 64.56% on a different period and corpus. A paired history-versus-
efficiency comparison on identical fixtures/partitions is required before any
claim that efficiency features add value. This investigation has not changed
NFL models or established an NFL improvement.
