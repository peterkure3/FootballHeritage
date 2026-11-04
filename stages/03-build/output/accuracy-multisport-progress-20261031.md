# Accuracy goal: study aggregation and NBA freshness

Previous goal turn made progress: 45 prospective paired soccer forecasts were
frozen. This turn also made progress; it is not a wait or a completed goal.
Production models remain unchanged; nothing staged or committed.

## Prospective soccer study

`scripts.assess_accuracy_study` now combines batches with identical model hashes,
alias maps, class order and sample policy. It counts the earliest generated
forecast per provider fixture ID, regardless of later recaptures. A changed
model or policy requires a separate study. Results are recomputed from captured
provider responses with verified file hashes, rather than trusting editable
assessment totals. Latest observed responses are used; conflicting same-time
responses remain ambiguous. Dated study reports never overwrite prior reports.

Three tests passed: duplicate recapture retains the earlier prediction, distinct
fixtures accumulate, changed model/policy is rejected. Real current study:
`pipeline/data/processed/accuracy_shadow/study-20261031.json` — zero settled,
45 pending, zero duplicate forecasts. No new accuracy evidence is claimed.

## Multisport baseline inventory

Checksum-linked saved reports are recorded in
`stages/04-test/output/multisport-accuracy-baseline-20261031.json`.

| Sport | Saved test sample | Saved accuracy |
|---|---:|---:|
| NBA | 1,089 | 64.37% |
| WNBA | 278 | 70.86% |
| Men's college basketball | 5,310 | 71.19% |
| Women's college basketball | 4,869 | 74.94% |
| NFL | 900 | 64.56% |
| College football | 1,676 | 74.52% |

These are not comparable rankings across sports or a current live-accuracy
claim. Only NBA was independently replayed this turn: dataset/model hashes
verified, exact original test fixtures rebuilt, accuracy/log loss/Brier matched
the saved metrics to 1e-12. Other rows are saved-report inventory only.

## NBA input freshness gap and research capture

The current basketball loader exposes 8,586 games, including 472 non-NBA records,
and zero October 2026 games. The selected NBA-only saved model has 8,114 games;
its latest result is 2026-06-09. Latest raw score captures contain no completed
games. This makes input freshness a higher priority than a more complex model.
Do not replace the NBA-only artifact with the unfiltered mixed-league corpus.

`etl.fetch_nba_results_research` captured 81 completed NBA results and excluded
seven unfinished/ineligible entries. The isolated directory is
`pipeline/data/raw/research/nba_results_20261031/`; it is not automatically loaded
by production trainers. Raw and normalized hashes, unique provider IDs and final
quarter totals were checked. Latest completed kickoff is 2026-10-31 02:00 UTC.

Regular-season scope uses October 20 as the 2026 opening date from the
[NBA's published key dates](https://www.nba.com/news/key-dates), plus provider
season/postseason flags. These checks do not establish independent result-source
agreement. Unknown, live, preseason and future games are excluded; malformed
scores and inconsistent quarters fail. Three adapter tests passed.

Availability is the real capture time, 2026-10-31 around 20:48 UTC, never the
historical game date. The new results cannot be used to improve earlier
backtests. They can inform future forecasts only after capture. This is a data
completeness improvement, not yet an accuracy improvement. The existing live
sport feature path normalizes its cutoff to the UTC day; using newly observed
scores before the next day needs an explicit experimental availability path,
not a silent production behavior change.

Follow-up: the reconciliation and first paired NBA batch are now recorded in
`accuracy-nba-freshness-20261101.md`: 80 independently matched results, 57 future
paired forecasts, six changed winner predictions, and no settled accuracy
evidence yet. Continue collecting the frozen studies under their original
policies. No promotion is authorized by the current evidence.
