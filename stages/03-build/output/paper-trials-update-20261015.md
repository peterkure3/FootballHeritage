# Paper-trial data refresh — 2026-10-15

The paper-trial API was serving the four existing batches, but automated fixture
ingestion was failing. PostgreSQL rejected the staging table's TEXT score
columns when the official upcoming-fixture batch contained only missing scores.
This left the collector failed and prevented its daily fixture refresh.

## Fixes

- Convert score columns to pandas nullable integers and explicitly declare SQL
  integer staging types in both loader staging writes. Missing scores remain
  SQL NULL; they are never converted to zero or labeled as completed results.
- Extend trial continuation from current-day fixtures to newly observed primary
  Bovada EPL quotes within the existing 14-day official fixture refresh window.
  Separate per-date quote files and reports prevent multiple-date collisions.
- Preserve the frozen candidate, artifact checksums, selection rules, thresholds,
  one-unit policy, quote freshness checks, and existing immutable forecasts.
- Do not request final results for future fixture dates. Their forecasts remain
  pending and excluded from settled ROI.

## Updated live state

- Collector completed successfully at `2026-10-15T01:06:58.312046+00:00`.
- Paper-trial endpoint returned HTTP 200 with **10 batches**, including six new
  date batches covering upcoming fixtures from October 17 through October 25.
- **14 pending forecasts**, of which **six meet the frozen selection policy**.
  Other observed fixtures that cannot satisfy candidate input requirements remain
  explicitly excluded. Forecasts without a selected outcome remain visible.
- **Seven settled selections preserved**: six frozen-model selections and one
  separate manual selection. The model study's existing settled ROI is -4.17%;
  the manual study remains separate. New pending forecasts do not change ROI.
- Formal model assessment remains `collecting`; the original 200-selection and
  60-fixture-day gates are unchanged. No demonstrated profitable edge is claimed.

## Verification

- PostgreSQL regression reproduced the nullable-score case in a private schema
  and rolled back all changes after checking empty scores and completed results.
- 33 Python tests passed across nullable fixture loading, trial collection,
  continuation windows, regional settlement, and trial-study integrity. One
  additional timezone test was skipped because its opt-in flag was not enabled
  for that regional suite invocation.
- Five Chromium checks passed, including real database-backed trial rendering.
  The real-data browser check passed again after the new batches were imported.
- Python syntax and `git diff --check` passed.
- Fallow retained the earlier workspace finding counts: two dead-code findings,
  14 complexity findings, one clone group. Root dependency confidence remains
  limited because root `node_modules` is absent; the audit is not a clean gate.

The full API evidence is in `paper-trials-update-20261015.json`; the audit is in
`paper-trials-fallow-20261015.txt`. The page polls once a minute while the Paper
trials view is open. No frontend behavior change was required to render the
updated data.
