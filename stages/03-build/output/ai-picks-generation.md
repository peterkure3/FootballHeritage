# AI Picks generation — 2026-10-08

Implemented the generation path after the local backend returned 503 because
`PIPELINE_API_URL` was unset. The example configuration also used `/api` instead
of the pipeline's `/api/v1` prefix.

## Behavior

- Development has a local pipeline default; configured root and legacy API URLs
  are normalized. Other environments require explicit configuration.
- The dedicated pipeline endpoint returns real stored active-model predictions
  created within 24 hours for unfinished fixtures in the next 30 days.
- Competition/date filters run before ranking. Champions League and Europa League
  labels accept the database's UEFA prefix. Dates use UTC.
- One selection per fixture: qualifying quoted value edges first, then model
  probability. Available quotes must be no older than 24 hours and not future-dated.
- Without quotes, prediction cards retain model probabilities and mark odds,
  edge, expected value, bookmaker and reference stake unavailable. Nothing is
  substituted. Quote-backed calculations use a fixed one-unit reference stake.
- Generation persists selections, requested filters, model version, timestamps,
  summary and provenance. User-owned history reproduces the saved response.

## Verification

- Python unittest discovery: 22 passed, including five AI Picks calculation tests.
- Rust URL normalization regression passed; backend compiled offline and was
  restarted on port 8888. Existing unrelated compiler warnings remain.
- Frontend strict TypeScript/build passed. Lint: zero errors, one existing
  AdminEvents hook warning. Eight AI Picks browser checks passed in Chromium
  and Firefox, covering missing quotes, filters, retry, empty results and navigation.
- Actual authenticated local POST: HTTP 200, 10 model v2.0.0 predictions from
  28 eligible fixtures. Saved run and history matched selections and provenance.
- League filter: 18 Champions League fixtures. UTC date/league filter: six
  Premier League fixtures on 2026-10-10. Empty La Liga results were HTTP 200;
  invalid sport/date were 422, unauthenticated generation was 401, and another
  account reading the saved run received 404 with empty personal history.
- Python syntax and git whitespace checks passed.

## Operational state

Backend process 27484 serves the rebuilt development binary. Pipeline remains on
port 5555. Backend restart invalidates in-memory sessions; existing users may need
to log in again. The previous binary is retained under backend/target for rollback.

Two isolated local QA accounts were created for authenticated and ownership checks:
`c0a195db-319a-4c81-9cbc-abaf064526ee` and
`2ce00f1f-5bb7-4569-80fc-8fecc977c10e`. No bets or financial operations were performed.
The accounts and their test runs remain identifiable for later cleanup; credentials
were generated in memory and were not written to disk or printed.

There are currently no bookmaker quotes for upcoming fixtures, so live responses
are predictions rather than value comparisons. Football is the only generation
model exposed. Chat still requires its own provider configuration. Candidate model
promotion and licensed historical backfill remain pending from the earlier pipeline
milestone. This records implementation and local verification, not staging sign-off.
