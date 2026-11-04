# Predictions page data review — 2026-10-09

Reviewed the mounted `/predictions` route, its React Query hooks, prediction service, results component, and FastAPI routers. Also checked the separate `/ai-picks` route to distinguish its Rust backend integration. This is a review; application behavior and active models were not changed.

## Live verification

Started an isolated local FastAPI process on port 5563 against the configured pipeline database, made read-only requests, queried evaluation/quote provenance with SELECT statements, and terminated the process. Reproduce with `py -3 scripts/audit_predictions_page.py` from `pipeline/`.

The observations below are the baseline before implementation. The [live audit JSON](predictions-page-live-audit-20261009.json) was refreshed while checking the fixes and now includes corrected history/accuracy responses. See [implementation and current verification](predictions-ui-update-20261009.md) for the completed changes and the new aggregate feed snapshot.

- Health, matches, accuracy and both history requests returned HTTP 200. Database connected; latest stored prediction timestamp was `2026-10-08T18:16:46.067938`. The health field `last_pipeline_run` actually measures latest prediction creation, not successful completion of every ingestion stage.
- All 30 fetched matches had stored v2.0.0 predictions; none had home/draw/away bookmaker odds. The fetched list includes finished fixtures, because filtering happens after the database limit.
- The 30-day accuracy endpoint returned 30.69% over 404 rows / 404 distinct fixtures (124 correct). Of these, 380 have unknown kickoff timestamps, 24 are confirmed pre-kickoff, and zero are at/after kickoff. The query explicitly includes missing dates, so this is neither a verified 30-day sample nor proof of prospective prediction performance.
- Stored `odds` contains 78,045 rows across only 37 distinct match IDs, with home decimal prices from 1.06 to 13.0. All `updated_at` values are null. Stored volume does not establish current fixture coverage or quote freshness.
- Unfiltered history page size 5 reports 1,490 total rows, two correct on the page, and 40% page accuracy. The same request with `result_filter=correct` returns two items but still reports total 1,490 and accuracy 40%, proving filter/count/pagination inconsistency.

## Findings and proposed corrections

1. **Odds format is wrong in the frontend.** `pipeline/config.py` requests decimal odds; `etl/transform.py` retains their prices; `/matches` returns decimal averages. `predictionService.js` and `Predictions.jsx` apply American formatting and implied probability formulas to these fields. Decimal 2.00 means 50% break-even probability, but the current American formula yields 98.04%. Use explicit `odds_format: decimal` and `1 / decimal_odds` internally; convert only for display preferences.

2. **Bookmaker prices lack usable provenance.** `/matches` averages every joined odds row without a latest-per-book selection, age cutoff, bookmaker identifier, or market settlement metadata. Repeated snapshots and different bookmakers can contribute unequally. Surface one actual current quote with source and timestamp for EV; compute market consensus separately from complete same-market, same-capture bookmaker probabilities. Unknown quote time must remain unavailable for freshness-qualified value comparisons.

3. **The fixture limit can hide upcoming matches.** `/matches` sorts dates descending and limits before the frontend discards finished fixtures and sorts ascending. The five nearest upcoming fixtures were present in this audit; the ordering still risks omitting nearer fixtures as the future schedule grows. Move upcoming/status/date filtering into SQL and order by kickoff ascending before pagination. Provide total count and sport/league/date filters. Separate live fixtures from pregame predictions.

4. **Soccer outcomes are incomplete.** Stored predictions contain home/draw/away probabilities, but fixture cards display only home/away and explicitly send `draw: null` into edge calculations. Render all valid outcomes for the market; use two-way outcomes for basketball and American football with their explicit overtime/tie settlement rules. Show missing probability as unavailable rather than zero.

5. **Accuracy needs a trustworthy denominator.** History, accuracy, and version statistics do not require `prediction.created_at < kickoff`, and history/accuracy admit unknown dates. Define a deterministic pre-kickoff prediction selection per fixture and model version, exclude unverifiable dates from forward-performance metrics, disclose exclusions, and separate historical backfill from live tracked predictions. Add sample size, date range, log loss/Brier, calibration, and same-fixture bookmaker baseline. Current data contains one row per scored fixture, but SQL has no safeguard against future duplicate prediction versions.

6. **History filters and summary scope disagree.** Apply correctness filtering in SQL before COUNT/LIMIT/OFFSET. End-date filtering should use an exclusive next-day boundary so all kickoff times on that date are included. Accuracy currently accepts only `days`; the frontend league/custom-date history filters do not propagate equivalent filters to summary statistics. Return summaries for the same selected sample. Keep unknown dates outside named date windows.

7. **The new sport candidates are not connected to this page.** Fixture cards call `/predictions/{match_id}` for latest stored predictions, and what-if uses the active soccer model through `/predict-matchup`. Neither calls `/sport-models/preview`. Provide a sport/league-aware model registry and explicitly labelled candidate preview before any promotion. The separate `/ai-picks` page already exposes decimal odds, bookmaker, model version and source times but currently enables generation for Football only.

8. **Missing prediction and failed API requests are conflated.** `getPrediction` catches server/network errors and returns null, causing the card to report “Prediction unavailable” for outages. Distinguish missing prediction, API failure, loading, stale prediction, missing market and no positive estimated EV. The hooks still use React Query v4 `cacheTime` and query `onError` options although the installed major version is 5; migrate to `gcTime` and supported error handling.

## Suggested card and API contract

Use one paginated aggregate endpoint rather than separate fixture and per-card prediction requests. Include:

| Group | Required fields |
|---|---|
| Fixture | canonical ID, sport, league, team IDs/names, timezone-aware kickoff, status |
| Prediction | outcome-probability mapping, selected outcome, model version/status, generated time, feature cutoff, input completeness/fallback flags |
| Market | market type, settlement rule, bookmaker ID, actual decimal prices, source observation time, ingestion time, availability/freshness |
| Comparison | per-outcome break-even and no-vig consensus probabilities, model-minus-consensus difference in percentage points, estimated unit EV, evaluation eligibility |
| Evidence | sample size/date range, calibrated performance and bookmaker baseline for the relevant league/model, excluded-row counts |
| Paging | page/cursor, page size, total count, applied filters, response generation time |

Display matchup and kickoff first, then all model probabilities, bookmaker comparison and quote age, followed by model provenance and evidence details. Probability difference is not unit EV: estimated unit EV is `model_probability * decimal_odds - 1` under the stated settlement assumptions. Estimated positive EV is not demonstrated bookmaker advantage; the saved bookmaker comparison reports do not establish such an advantage.

## Validation limits

Verified code paths and live API/database responses; did not run a rendered browser interaction test or alter prediction generation, model promotion, data ingestion, production services or betting behavior. No production frontend/backend edits. Fallow 3.32.0 audit passed with zero introduced findings; inherited findings remain, root node_modules is absent, and Fallow does not analyze Python.
