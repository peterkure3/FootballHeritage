# Bookmaker comparison grid — 11 October 2026

Open **Predictions → Bookmaker grid**. FootballHeritage is the first data column,
followed by all bookmaker sources present on the current page, sorted by source
key. Each group contains home win (1), draw (X), and away win (2).
Competition/date filters, refresh and pagination reuse the existing fixture API;
this view requests 20 fixtures per page.

The selector switches between:

- **Outcome probabilities:** active model probabilities beside each bookmaker's
  margin-removed implied probabilities, calculated within each complete market.
- **Estimated EV:** `(model probability × bookmaker decimal odds − 1) × 100%`.
  Each bookmaker uses its actual quote. FootballHeritage remains the explicitly
  labeled model-probability baseline, since it supplies no bookmaker price for
  its own EV. Positive cells are green; negative cells use the gold palette.

The API now includes `market.quotes[].fair_probabilities` for fresh complete
markets, reusing the normalization already used for consensus. Stale, incomplete,
untimestamped and missing prices show a dash. EV also requires a current valid
forecast. The existing 24-hour freshness policy is unchanged.
The grid covers the active soccer model's regulation-time 1X2 fixtures; other
sport candidates remain in the model lab.

The grouped heatmap follows the supplied reference using the project's cream,
green and gold colors. Headers and fixture labels stay visible inside the
scrollable table. Mobile scrolling stays within the grid. Tooltips identify
prices, capture times and model provenance. No sample data enter the application.

Restart the pipeline API if it runs without automatic reload so it serves the
new per-book probability field.

## Verification artifacts

- `bookmaker-grid-desktop.png`, `bookmaker-grid-mobile.png`: controlled browser
  fixtures checking positive/negative EV and unavailable data.
- `bookmaker-grid-live.png`: real PostgreSQL data through an isolated pipeline
  API, with five bookmaker groups and 42 upcoming fixtures at verification time.
- `bookmaker-grid-fallow-after.json`: repository audit.

No models, trial policy, database contents, scheduling or bet placement changed.

## Validation

- Focused API tests: nine passed, including rollback-only PostgreSQL integration:
  `RUN_PREDICTION_DB_TESTS=1 py -3 -m unittest discover -s tests -p test_prediction_dashboard.py -v`.
- Eleven Chromium prediction checks passed, including real API data, metric
  switching, missing/stale evidence and contained mobile overflow:
  `RUN_PREDICTION_DB_TESTS=1 npx playwright test tests/predictions.spec.js --project=chromium --reporter=line --workers=2 --timeout=60000`.
- Frontend lint: zero errors, one existing AdminEvents hook warning.
  Type checking and production build passed.
- Fallow 3.32.0 final audit passed with no introduced findings. Missing root
  node_modules limits dependency classification; Python is outside its coverage.
- Inspected desktop, mobile and real-data screenshots. An initial grouped-header
  test assertion was corrected to address the first header row; parallel browser
  timeouts were resolved by rerunning with two workers. No application assertion
  was relaxed.
