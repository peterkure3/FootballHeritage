# Cumulative accuracy studies

This turn made progress: cumulative NBA evaluation is implemented and exercised,
and result capture handles UTC/US calendar-day boundaries. Production models,
forecasts and training data remain unchanged. Nothing staged or committed.

`scripts.assess_nba_accuracy_study` reuses the soccer study's verified JSON reader
and earliest-forecast combination logic. It keeps the NBA model and freshness
hypotheses in separate studies. Models, input feature contract, baseline history,
class order and assessment policy must match within a study. Newly observed
additional history can evolve without changing model weights or feature policy.

Each fixture counts once, using its earliest generated forecast. Same-time
conflicting forecasts fail rather than depending on file order. Every input
batch is validated, including later recaptures excluded by deduplication.
Captured result files are hash-checked and assessment-to-trial linkage is
checked. Editable receipt totals are ignored. Results are recomputed from the
latest observed ESPN event; same-time conflicting observations remain ambiguous.

Current actual cumulative reports:

- `pipeline/data/processed/nba_model_shadow/study-20261101.json`: zero settled,
  57 pending, zero duplicate forecasts excluded.
- `pipeline/data/processed/nba_accuracy_shadow/study-20261101.json`: zero settled,
  57 pending, zero duplicate forecasts excluded.

These overlap in fixtures but test different hypotheses. They must not be added
together to claim 114 independent games or pooled as confirmation of one change.
The soccer trial remains separate, with its existing cumulative evaluator.

## Date-boundary corrections

The NBA result evaluator now requests both the UTC kickoff date and its preceding
calendar day. This covers games listed on the prior US-day scoreboard. The
research reconciliation script derives capture days from each new primary
batch, rather than ending permanently on October 31. Both use the same date
helper. Existing frozen results and forecasts were not regenerated.

The full synthetic test exercises capture and accumulation: a game at 02:00 UTC
is returned only by the prior day's response, and still settles correctly. It
also proves that a receipt claiming 999 settled games is ignored in favor of one
captured final result, then rejects a modified raw file with a stale hash. Other
tests cover repeated fixture selection, incompatible hypotheses/features/models,
same-time forecast conflicts, and later versus simultaneous result revisions.
Twenty-one affected tests passed. The first date-helper integration exposed a
Windows-invalid timestamp filename; date-only filenames were restored and the
tests rerun successfully. Python compilation and whitespace checks passed; the
staging area is empty. Synthetic settled games are not actual sports evidence.

## Subsequent assessment

From `pipeline/`, after games finish:

```powershell
py -3 -m scripts.evaluate_nba_freshness_shadow --trial data/processed/nba_model_shadow/20261101-inactivity
py -3 -m scripts.evaluate_nba_freshness_shadow --trial data/processed/nba_accuracy_shadow/20261031-freshness
$studyStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
py -3 -m scripts.assess_nba_accuracy_study --root data/processed/nba_model_shadow --output "data/processed/nba_model_shadow/study-$studyStamp.json"
py -3 -m scripts.assess_nba_accuracy_study --root data/processed/nba_accuracy_shadow --output "data/processed/nba_accuracy_shadow/study-$studyStamp.json"
```

Future batches require new output directories, verified fresh history, and
forecasts generated before kickoff. Keep model and feature policy frozen. Do not
repeat the same 57 games to reach the review threshold of 200 settled fixtures
across 20 days. No automated task or production publishing was introduced.

The remaining accuracy confirmation depends on future results and additional
prospective batches. Neither current sample has settled evidence, and the
retrospective accuracy interval still includes zero. Reaching a sample threshold
requires review, not automatic promotion. Bootstrap/model-selection limitations,
uneven history and inherited historical availability assumptions remain.
