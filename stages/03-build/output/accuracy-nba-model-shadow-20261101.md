# Prospective NBA inactivity-model trial

The previous turn produced the fixed inactivity candidate; this turn recorded
prospective evidence collection for that candidate. Production remains unchanged,
and nothing is staged or committed. The goal is active, not complete.

## Frozen comparison

`pipeline/data/processed/nba_model_shadow/20261101-inactivity/trial.json`
contains 57 paired future games, generated October 31 around 21:40 UTC
(November 1 around 00:40 in Kampala), before the first 22:00 UTC kickoff.
Seven winner predictions differ between the original and candidate models.
The candidate is exactly the frozen retrospective artifact, without retraining.

Both arms use the same 8,189 eligible results: 8,114 original games and 75
independently reconciled new results. Five more captured results are held out
until the next UTC day. Availability is the later of observation time and the
next UTC day after the game; nothing observed after the feature cutoff enters
either arm. Historical availability remains inherited, without archived receipts.
Both arms exclude odds. Final scores include overtime.

The replay explicitly processes historical feature queries and eligible result
updates. This matters because the candidate's inactivity rule resets state
during feature queries. Simply inserting results into a fresh state would miss
earlier inactivity resets and violate its training feature contract. Each future
fixture receives an independent copy of the replayed state. Future fixture
order cannot change another forecast's inputs. The forecast horizon uses only
results known now; intervening future results are unknown.

Schedule responses were reused from the verified earlier capture, with hashes
checked and copied. Fixture IDs, exact teams, times, timestamps, both input
vectors, both probabilities, model/history hashes, policy and source references
are frozen. Later postponements or schedule revisions must not be silently
settled under different times.

This is a separate hypothesis from the existing NBA freshness trial. The two
trials must not be pooled as evidence for one model improvement. Minimum review
sample is 200 settled fixtures across 20 match days; this batch alone is too
small. A threshold does not automatically authorize promotion. Further batches
must preserve the contract and retain only the earliest forecast per fixture ID.
Cross-batch NBA aggregation is now implemented in `scripts.assess_nba_accuracy_study`;
see `accuracy-study-accumulation-20261101.md`. Additional batches remain outstanding.

## Verification

Thirty-two tests passed across new prospective replay tests, NBA research and
freshness tests, and existing sport-model/basketball regressions. Tests compare
state replay against training feature definitions, exclude unavailable/future
outcomes, ensure independent forecast states, and check that the shared evaluator
uses the correct arm names for each distinct trial contract.

The recorder wrote valid trial files, then its console summary failed on a NumPy
integer. The exact original recorder source was preserved and hash-verified;
only console serialization was corrected. Forecasts were not regenerated or
backdated. A recorder snapshot is now saved automatically for future batches.

The initial assessment recorded zero settled and 57 pending games, with no source
errors. Reproduction evidence is stored alongside the trial in `verification.json`:
all paired inputs/probabilities replay, and three actual historical reference
fixtures check agreement with the training feature definitions. Python compilation
and diff whitespace checks passed; staging is empty.

From `pipeline/`, collect later results with:

```powershell
py -3 -m scripts.evaluate_nba_freshness_shadow --trial data/processed/nba_model_shadow/20261101-inactivity
py -3 -m unittest discover -s tests -p test_nba_model_shadow.py
```

Assessments use separate dated receipts and never overwrite the frozen trial.
The evaluator checks exact kickoff/team matches, final regular-season status,
valid non-tied scores and at least four periods. Ambiguous matches remain
unsettled. Metrics compare both models on identical settled games. No prospective
accuracy gain, profitability or production readiness is established yet.
