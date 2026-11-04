# Predictions page update — 2026-10-09

The `/predictions` page now presents complete forecast probabilities, verifiable bookmaker comparisons, and consistent pre-kickoff performance metrics. The interface follows the current site's cream and green design, with responsive fixture cards and separate Upcoming fixtures, Settled performance, and Model lab views.

## Resulting behavior

- Upcoming fixtures are filtered and ordered by nearest kickoff in PostgreSQL before pagination. Competition and UTC date filters operate on the complete schedule, with a real total count. Live/cancelled/postponed/finished matches do not enter the pregame feed.
- One aggregate request returns each page's fixtures, latest pre-kickoff prediction from the configured active model, probabilities, model/time provenance, and bookmaker evidence. The page no longer sends per-card prediction requests.
- Soccer cards show home, draw and away outcomes. Missing or invalid probabilities are unavailable, not zero. No prediction, stale prediction, missing market, stale/unverified market, API errors and absence of positive estimated value are distinct states.
- Decimal prices are used directly: break-even probability `1 / odds`, estimated unit EV `probability * odds - 1`. Each comparison cites an actual bookmaker price and observation time. Complete fresh quotes form an equal-book, margin-removed consensus; best actual prices are kept separate. The table includes model-minus-consensus percentage points. This is an estimate, not demonstrated betting advantage.
- Latest quotes are selected per bookmaker rather than averaging repeated snapshots. Predictions and complete quotes must each be within 24 hours to produce value comparisons. Future, incomplete, stale or time-unknown quotes cannot create an estimated edge.
- The page exposes model version and prediction time, plus settlement and freshness rules. Feature cutoff and fallback inputs remain explicitly unrecorded for stored predictions; values were not retroactively invented.
- Performance uses one latest valid pre-kickoff prediction per fixture, optionally scoped to a specific model version. Unverifiable kickoff dates, post-kickoff predictions and invalid probabilities are excluded. History correctness filtering and counts run before SQL pagination. Date range, exact league and version filters share the same cohort; end dates include the entire UTC day. Empty samples return null accuracy/loss instead of fabricated zero performance.
- Accuracy, log loss, multiclass Brier score, sample dates, league breakdowns and excluded counts are visible. Historical bookmaker baseline/calibration are unavailable for this cohort and are labelled accordingly. Timestamp eligibility alone does not prove that model training or feature inputs were leakage-free.
- Model version statistics use a valid pre-kickoff denominator and identify the configured active version, rather than assuming the most recently inserted version is active.
- The Model lab loads the actual saved candidate catalog and requests explicit previews for soccer, NBA, WNBA, NCAA men/women, NFL and college football. Previews show the appropriate outcome count, candidate status, history cutoff and settlement/probability basis. NFL probabilities are conditional on no final tie. Unknown teams and kickoffs before training are rejected by the existing preview API. Candidates remain inactive.
- Obsolete unmounted prediction card/badge/what-if components and their hooks were removed after repository-wide import mapping. The existing `/predict-matchup`, `/predictions/{id}` and other backend endpoints remain available; only their obsolete frontend wrappers were retired. Shared fixture consumers still use `getMatches`.

## API contracts

`GET /api/v1/prediction-dashboard/fixtures`

Parameters: `page` (>=1), `page_size` (1–50, default 6), exact `competition`, optional `match_date` (YYYY-MM-DD, UTC). Returns `items`, `total_count`, `page`, `page_size`, available `competitions`, `generated_at`, `active_model_version`, `max_evidence_age_hours`, and `timezone_basis`.

Each item contains fixture fields plus optional `prediction` and a `market` object. Prediction probabilities use outcome keys (`home_win`, `draw`, `away_win`). Market quotes preserve bookmaker, decimal prices and observation time. `comparisons` is empty when evidence fails eligibility. Quote age is evaluated server-side. Legacy naive pipeline timestamps are treated as UTC; that assumption is exposed in the contract.

`GET /api/v1/predictions/history-data` and `/predictions/accuracy-data`

Both accept exact `league`, `model_version`, optional `days` (1–365), `start_date`, and inclusive `end_date`. Explicit dates override `days`; omission of all date parameters means all dated eligible history. Reversed/invalid ranges return 422. History additionally accepts `page`, `page_size` and `result_filter` (`all`, `correct`, `incorrect`). History counts/accuracy describe the full filtered sample, not just the returned page. The performance summary intentionally keeps all correctness outcomes within its selected date/league/model cohort.

Existing history response fields are retained, with generated timestamps, exclusion counts and evaluation basis added. Accuracy adds log loss, Brier score, sample bounds and evidence limitations. Accuracy can be null for an empty sample. Version responses add `settled_count`; accuracy is null when no eligible settlements exist.

## Verified evidence

Live local API checks: **15 passed**, including fixture pagination, unknown competition, shared history/summary filters, history correctness counts, version responses and all seven saved sport model previews. Reproducer: `py -3 scripts/verify_prediction_dashboard.py` from `pipeline/`. All verification servers were stopped.

- 28 upcoming fixtures, with the six nearest fixtures returned on the first page.
- 30-day eligible performance: **24 fixtures, 10 correct, 41.67% accuracy**, log loss **1.04633**, Brier score **0.61921**. 380 stored predictions have unknown kickoff dates and are disclosed outside the named date window; six dated settled fixtures have no eligible pre-kickoff prediction.
- Correct-only all-time history reports **20 total / 20 correct**, returns five records for page size five, and counts are consistent with the filter.
- Current first-page fixtures have no linked bookmaker quotes. Their value comparisons remain unavailable. The quote calculation/UI cases are additionally verified against explicitly mocked test data.
- Raw API evidence: [predictions-ui-live-verification-20261009.json](predictions-ui-live-verification-20261009.json).

Validation: the 83-test Python regression suite passed during implementation; the nine quote/PostgreSQL dashboard tests passed again after final query changes. PostgreSQL tests use rollback-only temporary tables and are opt-in (`RUN_PREDICTION_DB_TESTS=1`) so normal unit CI does not require a configured local database. Python compilation passed. `pyflakes` is not installed in this environment.

Chromium verification: **six feature tests passed** after final UI changes, covering all outcomes/decimal EV, pagination, matching date scopes and correctness filters, mobile NFL preview/settlement, errors, stale quotes, mobile overflow, and actual pipeline data rendered in the page. The **18 existing navigation tests** also passed on the final combined navigation run. Feature tests run with `RUN_PREDICTION_DB_TESTS=1 npx playwright test tests/predictions.spec.js --project chromium --workers 1`; the real-database browser scenario is skipped unless explicitly enabled.

Final frontend ESLint, TypeScript typecheck and production Vite build passed. Fallow **3.32.0 audit passed with zero introduced dead-code, complexity, duplication or styling findings**. Its inherited findings remain, root node_modules is absent, and Python is outside its analysis coverage. The final nine dashboard tests also verified that version statistics exclude invalid winner labels and match the eligible history sample. `git diff --check` passed for modified feature files. Local verification servers on 5187, 5563 and 5564 were stopped.

## Visual previews

- [Real pipeline fixtures](predictions-ui-live.png)
- [Bookmaker comparison states — mocked test fixtures](predictions-ui-desktop.png)
- [Settled performance layout — mocked test data](predictions-ui-performance.png)
- [Mobile fixture states — mocked test fixture](predictions-ui-mobile-fixtures.png)
- [Mobile model lab — mocked candidate response](predictions-ui-mobile-models.png)

Active model artifacts, training data, sportsbook ingestion, stored predictions, production deployment and betting behavior were not changed. Current quote coverage, timezone assumptions, unrecorded training/input provenance and lack of a verified bookmaker advantage remain material data limitations.
