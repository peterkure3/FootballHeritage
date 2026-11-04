# Accuracy goal: prospective evidence now recording

Previous goal turn: progress (retrospective candidate and measured improvement).
This turn: progress (immutable live pregame forecasts and a checked result evaluator).
The overall goal remains active; no promotion, staging or commits.

## Recorded evidence

The existing official fixture fetcher returned 67 fixtures from PL, PD, BL1, SA
and FL1 over a bounded seven-day window. Exactly 45 were scheduled in the future;
22 non-future/scheduled rows were excluded. No fixture request failed and no
future fixture was lost because of unmatched history in either arm.

Both frozen history experts predicted each of the same 45 fixtures, without odds,
bets, registry writes or production publication. Baseline and reviewed model
hashes, history checksum, frozen alias map, exact input vectors, raw fixture
responses, source checksums and generation timestamps were saved. The first
kickoff is 2026-11-01 11:30 UTC. The original trial digest is
`38349d1bcc5cec22d29a36a982279888e4c5a53e424f4d728cf5895761beb35e`.

Path: `pipeline/data/processed/accuracy_shadow/20261031-paired/`.

The initial assessment found zero settled and 45 pending forecasts. There are
no new accuracy results yet. Assessment leaves the trial bytes unchanged and
writes separate dated receipts. It requires a unique provider ID, exact kickoff,
matching home/away identities, FINISHED status, REGULAR score duration and valid
nonnegative integer scores. Conflicting or mismatched records cannot count as
settled. Pending fixtures are outside the metric denominator. No automatic
promotion is possible.

## Reproduce

From `pipeline/`, to assess this batch after games finish:

```powershell
py -3 -m scripts.evaluate_accuracy_shadow --trial data/processed/accuracy_shadow/20261031-paired
```

The recorder is `scripts.record_accuracy_shadow`; it requires a fresh output
directory and never overwrites an earlier trial. Source API responses can be
served from the existing fetcher's cache; the recorded timestamp establishes
local observation, not an assertion of provider freshness. Exact fixture state
is checked again at result assessment. Historical input uses the saved snapshot
and the inherited previous-UTC-day result rule; a prediction-time capture makes
the snapshot available now, but does not retrospectively verify its source data.

## Validation and remaining work

Four adversarial shadow tests passed: paired generation, pregame cutoffs, unknown
history/past fixture exclusions, duplicate provider identity rejection, and exact
final-result matching. Synthetic tests are not sports accuracy evidence. Original
trial checksum was independently checked after assessment.

The frozen sample policy calls for at least 200 settled matches across 20 match
days before an adoption assessment. This 45-match batch cannot alone satisfy it.
Deduplicated cross-batch study aggregation is now implemented in
`scripts.assess_accuracy_study`; later batches remain to be added. See
`accuracy-multisport-progress-20261031.md` for its checks. In particular,
do not reinterpret this first small batch as the complete confirmation study.
Fresh history captures shared by both arms will also be needed for later batches
so input staleness is explicit rather than hidden. Other sports' baselines and
recent-season data completeness remain open workstreams while these games run.
