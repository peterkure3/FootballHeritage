# Verified observation history and the second NBA batch

This turn made progress toward the accuracy goal by preserving causal input
history and extending the frozen prospective studies. Production models and
request handling are unchanged. Nothing staged or committed.

## Observation-time preservation

`scripts.merge_nba_research_history` combines verified independent captures into
a separate history artifact. It checks normalized/raw files, primary capture
linkage, independent response hashes, timezone-aware observations and valid NBA
finals. For an unchanged fixture identity, kickoff and score, the earliest
verified observation time is retained. Changed or reverted values use their new
observation time. A newly excluded earlier result is quarantined. Conflicting
same-time corrections and duplicate provider IDs fail.

The actual merged history contains 87 independently reconciled finals:
80 retained their verified October 31 observation times; seven are newly known
from the November 1 capture. There were no revisions or quarantines. This is
not invented historical availability: earlier source receipts and hashes remain
linked. It does not prove provider freshness or historical correctness beyond
the captured evidence.

Artifact: `pipeline/data/raw/research/nba_results_20261101/first_observed/`.
It contains the usual `reconciled.jsonl` and manifest contract already consumed
by both research recorders. Original capture files and frozen trials were not
rewritten. Underlying evidence must remain present for future verification.

## Expanded prospective sample

New batch paths:

- `pipeline/data/processed/nba_model_shadow/20261101-refresh/`
- `pipeline/data/processed/nba_accuracy_shadow/20261101-freshness/`

Each has 58 future paired forecasts. The original/candidate model arms use the
same 8,197 eligible results, with the frozen next-day availability floor; four
new finals remain unavailable under that floor until the next UTC day. Model
weights, feature definition and review policy are unchanged. Forecasts generated
after kickoff are excluded. Five model-arm winner predictions differ in the new
batch; this is not an accuracy result.

After combination, each study contains 64 unique fixtures: six settled and 58
pending. Fifty-one later recaptures are excluded; only seven new fixture IDs
increase the sample. Earlier recorded probabilities remain authoritative for
those 51 games. The overlapping studies remain separate hypotheses.

Actual settled performance remains candidate 5/6 versus original 4/6 in the model
trial, and 4/6 in both freshness arms. These are the same six unique games, not
twelve independent finals. Confirmation still requires additional fixtures and
match days; there is no promotion or profitability conclusion.

## Checks and reproduction

Twenty-three affected tests passed across observation merging, both NBA research
recorders/evaluators and shared study accumulation. Five new tests cover first
observation retention, corrections/reversions, exclusion quarantine, duplicate/
naive-time rejection and modified evidence detection. Python compilation and
whitespace checks passed, and staging remains empty.

The refreshed model batch has an independent replay receipt at
`pipeline/data/processed/nba_model_shadow/20261101-refresh/verification.json`,
checking every preserved time, frozen model/source hashes, all paired inputs and
probabilities, and new fixture membership. Original forecasts are not regenerated.

From `pipeline/`, use a new output path when repeating the merge:

```powershell
py -3 -m scripts.merge_nba_research_history --captures data/raw/research/nba_results_20261031/reconciliation data/raw/research/nba_results_20261101/reconciliation --output data/raw/research/nba_results_20261101/first-observed-replay
py -3 -m unittest discover -s tests -p test_nba_history_observations.py
```

Later captures can include this verified merged artifact as the preceding input.
Keep the original sources and preserve actual observation times; do not use
newly collected results to revise earlier frozen predictions or backtests.
