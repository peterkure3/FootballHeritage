# Admin operations dashboard — 2026-10-15

The admin dashboard now shows live operations, sportsbook data, predictions and
paper-trial progress, matching the requested focus. The old dashboard displayed
hardcoded users, revenue, growth, alerts, and confirmation messages for unwired
bulk actions. Those placeholders are removed from the overview.

Open **http://localhost:5173/admin/dashboard** with an administrator account. The
frontend is running on port 5173. The configured API allows the `localhost`
origin; the existing administrator/super-administrator route guard remains.

## Visible behavior

- Upcoming fixtures, configured-source coverage, fresh quote counts, current
  active-model forecasts, and pending model paper selections.
- Collector outcome with separate last-attempt and last-success timestamps.
- Competition-level fixture, price, and forecast coverage.
- Searchable sportsbook coverage with fresh/unpriced filters and expandable
  source rows. Missing data is shown as unavailable, never as invented counts.
- Home/draw/away EV coverage, with positive estimated EV explicitly separated
  from demonstrated returns.
- Frozen model study progress, both formal assessment targets, pending
  selections, settled and stressed paper ROI. Manual studies remain separate.
- Latest raw collection receipt with transport, capture time, source counts and
  observation counts. Captures are distinguished from matched database quotes.
- Automatic 60-second refresh, manual refresh/retry, and JSON snapshot export.
  Independent service failures retain the other panel; failed background refresh
  preserves earlier data with a visible notice.
- Direct links to the prediction workspace's fixture, bookmaker and paper-trial
  tabs. The URL preserves the selected view and browser navigation works.
- Mobile layout and functioning sidebar toggle; the sidebar starts closed on
  narrow screens. Existing admin management pages remain accessible.

## Data contract

New `GET /api/v1/prediction-dashboard/operations` is a read-only aggregate of
already-public prediction evidence. It contains no account, wallet, or user
information. Collector/capture summaries deliberately omit private filesystem
paths, source URLs, and credentials.

Coverage uses all eligible upcoming, unfinished fixtures, not just one page.
Quote counts use one latest observation per fixture/bookmaker and exclude stale,
future-dated, incomplete, non-finite and invalid prices. Forecast counts use the
latest eligible active-model prediction, valid probabilities and a maximum
24-hour evidence age. EV comparisons use the best eligible price for each of
the three outcomes. The latest invalid observation is not silently replaced by
an older valid observation.

The existing `/paper-trials` endpoint supplies independent frozen-study evidence.
No model artifacts, selections, trial policies, settlement results, or account
balances were changed by this dashboard work.

## Verified live values

At verification: 38 upcoming fixtures; 38 current forecasts; 105 fresh quotes
from nine of 46 configured sportsbooks; 84 compared outcomes, including 41 with
positive estimated EV. The paper ledger had ten batches, 14 pending forecasts
and six selected pending model picks. Counts update from the running services.

## Validation and artifacts

- 13 Python tests passed, including real PostgreSQL rollback-only cases for
  stale/invalid prices, duplicate observations, active model selection, EV counts,
  empty coverage, and capture-summary privacy.
- Six new Chromium dashboard checks passed: metrics/filter/export/deep links,
  unavailable-service retry, cached-data notices, mobile menu/overflow, ordinary
  user redirect, and real database-backed operations/trials. All six passed again
  after component extraction. Six existing prediction/trial browser regressions
  also passed.
- Final targeted ESLint, TypeScript checks, production build, Python compilation,
  and `git diff --check` passed.
- Direct browser GET requests from `localhost:5173` to the running operations and
  paper-trial APIs both completed with HTTP 200, with populated metrics and no UI
  error notice. Development-mode initial query cancellations were distinguished
  from the successfully completed responses.
- Desktop and mobile previews were visually inspected. Large new render
  functions were split after audit; the new dashboard has no critical complexity
  finding. Fallow still reports workspace-wide existing and size/style findings;
  root dependency confidence remains limited by absent root `node_modules`.
  There are no new clone groups or dead-code findings relative to the baseline.

Evidence:

- `admin-operations-live-20261015.json`: live API summary cross-checked against
  the fixture feed's counts and outcome comparisons.
- `admin-operations-browser-20261015.json`: direct-browser request results and
  displayed metrics; administrator identity is explicitly a browser test fixture.
- `admin-operations-live.png`, `admin-operations-mobile.png`: previews. The desktop
  image uses live operations/trial data; the mobile image uses explicitly mocked
  test responses.
- `admin-operations-fallow-20261015.txt`: final repository audit.

Existing unrelated uncommitted workspace changes were preserved. No production
deployment or Git commit was performed.
