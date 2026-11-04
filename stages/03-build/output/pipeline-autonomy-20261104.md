# Pipeline integration and autonomous operation — 2026-11-04

The recurring pipeline runs without Codex or another AI agent. All 94 top-level
Python scripts in stage output folders are inventoried with source checksums and
maintained workflow replacements or archive/opt-in dispositions. Historical
repairs, probes and frozen match-specific investigations are retained rather than
automatically replayed. The user approved this scope during the session.

## Delivered

- `pipeline/scripts/run_pipeline.py`: daily/local/market/report/weekly jobs,
  dependency gates, shared OS lock, bounded child execution and process-tree
  termination, atomic run summaries, per-step logs, environment doctor and status.
- `pipeline/run_pipeline.bat` and compatibility daily/weekly wrappers. The launcher
  uses the dedicated `.venv` rather than the incomplete scraping environment.
- `pipeline/setup_automation.bat`, exact dependency lock and separate collector
  environment requirements. Fixed pandas 3 requiring SQLAlchemy >=2.0.36.
- `pipeline/scripts/export_market_report.py`: current local date, stale/future
  snapshot rejection, maintained market engine, explicit EV units, JSON/Markdown/CSV,
  and optional local-only inactive candidate previews with provenance checks.
- Removed stale fixture/source/test-count claims and empty-day failure from the
  existing soccer research renderer. Preserved the research workflow as opt-in.
- Official football collection now reports swallowed provider failures and can run
  independently of the paid Odds API. `--public-only` omits paid batch collectors.
- Fixed NFL aggregate-cache reload dtype consistency exposed by the full suite;
  retained existing user research code and its checksum protection.
- Registered `FootballHeritage-Pipeline-Daily` at 06:00 with `daily --public-only`
  and `FootballHeritage-Pipeline-Weekly` Sunday 03:00 with `weekly`. Both tasks were
  returned in Ready state. Times use the computer timezone and the signed-in user.

## Executed verification

- Full suite in the dedicated environment: **391 passed, 31 skipped, 75 subtests**
  (`python -m pytest -q tests --disable-warnings`). Log:
  `pipeline/logs/automation/pytest-verification.log`.
- After the final soccer-renderer change: **23 passed** across market report,
  runner, source-failure control and NFL cache checks. This overlaps the full suite;
  the counts must not be added together.
- `pip check`: no broken requirements. Source compilation and tracked-file
  whitespace checks passed.
- The first live market cycle exposed the pandas/SQLAlchemy incompatibility.
  Corrected it in an isolated environment and repeated successfully.
- Market job `20261104T112527087269Z-markets`: all three steps passed. Regional
  audit recorded 27 matched quotes and no cycle errors. Public NBA validation,
  paper-result processing, snapshot and report completed.
- Daily public job `20261104T112851816218Z-daily`: all steps passed, including
  official fixture fetch, form import, transform, database load/schema, general
  predictions, regional refresh, backend sync, snapshot and report.
- Optional export of the local `20261103-market-refresh` candidate passed after
  refreshing the snapshot. An earlier attempt correctly refused stale input.
  Candidate output: `pipeline/logs/automation/candidate-verification-20261104/`.
  Serving model selection was not changed.
- Environment doctor passed dependency, scraping-import, active-artifact and both
  database checks before registering the tasks. Task registration does not claim a
  future trigger has already executed.
- Weekly training-input dry run is recorded separately in
  `pipeline/logs/automation/training-input-verification.log`; a full weekly training
  cycle was not needed to validate these unchanged trainers, and is not claimed.
- Fallow ran before/after. The post-change audit is
  `pipeline-autonomy-fallow-20261104.json`. It reports repository issues and warns
  that missing node_modules limits dependency classification. It does not establish
  Python correctness; the Python tests and live runs provide that evidence.

## Operating limits

Use `pipeline/docs/UNATTENDED_PIPELINE.md` for setup, commands, logs, task settings
and recovery. The PC must be awake, signed in, online and able to reach PostgreSQL.
Tasks catch up missed starts and retry bounded failures. Daily collection does not
provide continuously fresh quotes; run `markets` before relying on a report.
Source-specific exclusions remain visible even when an export succeeds. Empty
coverage does not prove absence of opportunities. Paid-provider access needs account
repair before enabling paid batch collection. Weekly jobs produce candidates;
they do not automatically promote models. Existing history, model artifacts and
private service configuration must be backed up separately.

The 31 skipped tests remain skips, not passes. No production deployment, source
credential change, wager, commit or push was performed. Existing unrelated working
tree changes were preserved. Future provider outages and schema changes can still
require maintenance; failures now have bounded execution and inspectable logs.
