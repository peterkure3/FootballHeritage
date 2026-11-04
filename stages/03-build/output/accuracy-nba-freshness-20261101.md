# NBA input-freshness experiment

Production models, serving paths and training datasets remain unchanged. Nothing
has been staged or committed. This is an accuracy experiment, with no bets or
profitability claim.

## Recorded evidence

The October 31 primary capture contains 81 completed regular-season results.
Daily ESPN scoreboards independently matched 80 on exact kickoff, team identity,
orientation and final score. One unmatched provider fixture (`21717857`) was
excluded. All twelve daily requests succeeded. The earlier ESPN date-range
request failed with HTTP 400 and the official NBA schedule request returned 403;
neither failed response is used as corroboration.

Reconciled results retain the later of the two actual observation timestamps.
They are never represented as available before capture. Raw responses and
normalized records have recorded SHA-256 hashes. Source agreement does not
prove source independence or that either provider is universally correct.

The frozen trial is
`pipeline/data/processed/nba_accuracy_shadow/20261031-freshness/trial.json`.
It contains 57 future paired forecasts, generated October 31 around 21:00 UTC
(November 1 around midnight in Kampala). One ineligible schedule entry was
excluded. First kickoff: October 31 at 22:00 UTC.

Both arms use the exact same saved NBA model, with SHA-256
`5db648fad59783874da2b7a9c8268fff7f54bc89a05ba5ca5c0bbd894f958477`.
The baseline history contains 8,114 NBA-only games ending June 9; the refreshed
arm adds the 80 reconciled results. Six winner predictions changed. This is an
input-effect observation, not evidence of improved accuracy.

The research feature path uses explicit timezone-aware observation cutoffs before
kickoff. Unobserved or future results are excluded. Production's existing UTC-day
cutoff is unchanged. No odds are supplied in either arm. Future intervening
results within the seven-day horizon are unknown to these frozen forecasts.

## Evaluation and reproduction

Run from `pipeline/`:

```powershell
py -3 -m scripts.evaluate_nba_freshness_shadow --trial data/processed/nba_accuracy_shadow/20261031-freshness
py -3 -m unittest discover -s tests -p test_nba_freshness_shadow.py
py -3 -m unittest discover -s tests -p test_nba_research_results.py
```

Each evaluator run checks frozen trial/schedule hashes and writes a separate
dated receipt with captured result responses. It requires an exact kickoff and
team match, completed regular-season status, at least four periods, and valid
non-tied final scores. Overtime is included. Duplicate matching results remain
ambiguous; invalid frozen probabilities or forecast timestamps fail. Accuracy,
log loss and Brier score use the same settled games for both arms.

The initial assessment at October 31 21:04 UTC recorded zero settled, 57 pending,
and no source errors. No measured NBA improvement is established. The trial's
minimum review sample is 200 settled fixtures across 20 match days; this batch
alone cannot reach it. Repeated batches must count the earliest forecast per
provider ID and retain model/input-policy identity. Cross-batch NBA aggregation
is now implemented in `scripts.assess_nba_accuracy_study`, keeping these hypotheses
separate; see `accuracy-study-accumulation-20261101.md`.
Reaching a sample threshold does not authorize promotion.

Eighteen focused tests passed across NBA collection/freshness and soccer
research/shadow/study modules. The initial module-qualified unittest invocation
failed because `tests` is not an importable package; directory discovery passed.
Replay evidence is recorded in
`stages/04-test/output/nba-freshness-replay-20261101.json`.

Further work: collect prospective results and additional paired batches, assess
uncertainty by match day, and test any training change on separate chronological
development folds before freezing it. Historical gains from the soccer identity
experiment remain retrospective and do not establish future gains or profits.
