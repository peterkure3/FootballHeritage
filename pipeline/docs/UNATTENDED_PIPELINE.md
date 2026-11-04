# Running FootballHeritage without an AI agent

All commands below run locally. No Codex account, AI agent, or chat session is required.
Keep this repository, the local PostgreSQL databases, private `.env` files, raw history,
and model artifacts backed up. The scripts do not recreate missing credentials or training data.

## Normal operation

Open PowerShell in the repository and run:

```powershell
cd D:\Github\FootballHeritage\pipeline
.\run_pipeline.bat doctor
.\run_pipeline.bat daily --public-only
.\run_pipeline.bat status
```

`doctor` checks installed dependencies, pandas/SQLAlchemy compatibility, the scraping
interpreter, configured football key, active model files, and both database connections.
It does not spend API credits or prove provider access. `--public-only` skips the three
paid Odds API batch collectors; official football fixtures, imported form, public
bookmaker collection, NBA public odds and paper-result settlement still run. Use
`daily` without that flag after fixing and verifying paid-provider access.

| Command | Purpose |
|---|---|
| `run_pipeline.bat daily --public-only` | Official football/form ingestion, prediction generation, regional collection, backend sync, snapshot and report |
| `run_pipeline.bat daily-local --public-only` | Same workflow without backend sync |
| `run_pipeline.bat markets` | Refresh regional/public markets and paper results, then snapshot and report |
| `run_pipeline.bat report` | Export the existing snapshot; refuses snapshots older than 30 minutes |
| `run_pipeline.bat weekly` | Train new global and league candidates; keeps serving models unchanged |
| `run_pipeline.bat weekly --training-args --threads 2 --trees 100` | Pass tuning options to the global candidate trainer |
| `run_pipeline.bat daily --public-only --dry-run` | Show the exact job plan without collecting data or writing reports |
| `run_pipeline.bat status` | Print latest job results; nonzero if absent or any latest job failed |

The old `run_daily_fetch.bat`, `run_daily_fetch_with_sync.bat`, and
`run_weekly_retrain.bat` now call this runner. Existing scheduler actions using those
paths therefore use the same logging and lock. Do not run both old and new scheduled
tasks for the same work.

Every real run creates `logs/automation/<UTC timestamp>-<job>/run.json`, step `.log`
files, and, when a fresh snapshot is available, `markets/report.md`, `analysis.json`
and `picks.csv`. `latest-<job>.json` points to the most recent run. Logs and runtime
data are deliberately not committed. Check both the run status and report source
errors: an export can succeed with explicitly documented partial source coverage.

Exit status is 0 for a completed job, 1 for failed/blocked steps, and 75 when another
pipeline job owns the shared lock. Invalid command arguments use status 2. A child
process has a bounded timeout and its process tree is stopped on timeout. Independent
settlement/collection/report work is attempted even if another step fails. Failed
official fixture collection blocks its transform/load chain; failed load/form/schema
blocks general predictions and backend sync. Regional collection retains its own
existing exact-match, fresh-quote forecast and paper-trial rules.

## Windows scheduling

From `pipeline/`, preview the task definitions:

```powershell
powershell -NoProfile -File scripts/install_pipeline_tasks.ps1 -PublicOnly
```

Install them when the database and environment checks pass:

```powershell
powershell -NoProfile -File scripts/install_pipeline_tasks.ps1 -PublicOnly -Install
Get-ScheduledTask -TaskName 'FootballHeritage-Pipeline-*'
Get-ScheduledTaskInfo -TaskName FootballHeritage-Pipeline-Daily
```

Defaults are daily 06:00 and Sunday 03:00 in the **computer's timezone**. Override
with `-DailyAt '06:00' -WeeklyAt '03:00'`. Market reports use Africa/Kampala dates.
These tasks run under your signed-in account with ordinary privileges, catch up after
a missed start, and retry failures three times at 20-minute intervals. Keep the PC
awake, signed in, connected to the internet, and PostgreSQL running. They cannot run
on a powered-off machine. In Task Scheduler you may separately configure credentials
for execution while signed out. The installer never stores a password or overwrites
an existing task. Inspect existing tasks before changing or removing them.

Daily collection is not continuous live odds collection. Run `markets` shortly before
using a report; quotes expire according to the existing 15/30-minute rules. To disable
the installed tasks without deleting their definitions:

```powershell
Disable-ScheduledTask -TaskName FootballHeritage-Pipeline-Daily
Disable-ScheduledTask -TaskName FootballHeritage-Pipeline-Weekly
```

## Setup or recovery

Install Python **3.12** with the Windows Python launcher. Run `setup_automation.bat`.
It creates `.venv`, restores the tested exact versions from `requirements-automation-lock.txt`, creates the separate Scrapling
environment if absent, and runs `doctor`. On an existing scraping environment,
dependencies/browsers are preserved; repair them explicitly if needed:

```powershell
.venv-scrapling\Scripts\python.exe -m pip install -r requirements-scraping.txt
.venv-scrapling\Scripts\scrapling.exe install
```

The launcher prefers `.venv\Scripts\python.exe`, then a complete Python 3.12 installation,
then the normal Python discovery helper. To select a different executable explicitly,
set `FH_PIPELINE_PYTHON` to its full path. Do not point it at the scraping-only interpreter.
Credentials stay in service `.env` files. Never paste them into scheduler arguments.

| Symptom | Action |
|---|---|
| `doctor` reports missing dependency or pandas/SQLAlchemy incompatibility | Rerun `setup_automation.bat`; pandas 3 requires SQLAlchemy >=2.0.36 |
| Database check fails | Start PostgreSQL; check the private pipeline/backend database configuration; rerun `doctor` |
| HTTP 401 from paid odds | Check the provider account/key/quota; run `daily --public-only` until access is repaired |
| HTTP 403/429 or provider unavailable | Read the failed step's log/source report; allow rate-limit recovery before rerunning |
| No active picks, missing teams, or missing candidate history | Read exclusions and coverage; do not substitute invented forecasts or force model promotion |
| Snapshot too old/future-dated | Check Windows clock; run `markets`; do not loosen freshness thresholds |
| Exit 75 / task overlap | Let the current run finish, then rerun; never delete the lock file to bypass a live run |
| Timeout | Inspect the step log, connectivity and service health; rerun the whole job after repair |
| Previous run crashed | Rerun the job; the OS releases the lock. Completed steps are recorded, not automatically replay-resumed |

Runs use new directories rather than overwrite dated evidence. Existing producers
retain their own database upsert/trial deduplication behavior; there is no blanket
transaction across an entire job. A rerun can append observations or predictions.
Back up the database and data/model directories regularly. Move older completed logs
to a backup location when disk space is low; never remove active-run data.

## What happened to the scripts in output folders

The dated scripts are retained as historical evidence. The recurring workflow calls
reusable modules under `etl/`, `models/`, and `scripts/`, never arbitrary files from an
output folder. The source inventory is `docs/OUTPUT_SCRIPT_INVENTORY.md`.

| Output-script family | Maintained entry point |
|---|---|
| Dated market refresh export and daily pick rendering | `scripts.export_market_report`, run by `daily`/`markets`/`report` |
| Bookmaker/NBA collection and exact quote import | `scripts.refresh_regional_pipeline`, `etl.scrape_sportsbooks`, `etl.fetch_nba_public_odds` |
| Missing form/UCL upcoming form/history collection | `etl.fetch_football_form --import-history`; daily job includes CL and supported domestic competitions |
| Archive/league history collection | `etl.fetch_league_training --help` (explicit opt-in download) |
| Football and league training scripts | `models.train_model_v2`, `models.train_football_leagues`; weekly saves candidates |
| NBA/NFL/college model training investigations | `models.train_sports --help`; opt-in candidate training |
| Simulation and comparative soccer market research | `scripts.analyze_soccer_markets` and `scripts.report_soccer_markets`; explicit inputs below |
| Outcome refresh and paper-trial audits | Recurring regional settlement and `scripts.assess_paper_trial` |
| Accuracy/NBA frozen studies | Existing record/evaluate/assess scripts below; opt-in because they require a specific frozen study contract |
| One-time repairs, probes, lineup checks and dated opponent analyses | Historical only; never replay repairs or stale match evidence automatically |

Candidate previews are opt-in and cannot activate a model:

```powershell
.venv\Scripts\python.exe -m scripts.export_market_report --output logs\candidate-preview-NEW --candidate models\model_store\candidates\YOUR_REVIEWED_BUNDLE
```

The exporter checks the dataset checksum, feature/class contract, training time,
history coverage and probability normalization. Only local candidate bundles beneath
`models/model_store/candidates` are accepted. It records model/dataset/snapshot hashes,
keeps active picks separate, and emits explicit `gross_ev_fraction`/`gross_ev_pct`.
Candidate quality is the saved evaluation result, never a hardcoded performance claim.

For research simulation, provide a **fresh** sportsbook capture and matching form
directory from the existing collectors. Use new output paths each time:

```powershell
.venv\Scripts\python.exe -m scripts.analyze_soccer_markets --capture data\raw\sportsbooks\CAPTURE --form data\raw\team_form\FORM --output logs\soccer-analysis-NEW --runs 100000
.venv\Scripts\python.exe -m scripts.report_soccer_markets logs\soccer-analysis-NEW
```

For a current Champions League analysis using a newly trained global candidate,
first capture official CL form with `etl.fetch_football_form --competitions CL
--import-history --output-dir <new-form-directory>`, train with
`models.train_model_v2 --output-dir models/model_store/candidates/<new-candidate>`,
then collect fresh odds with the separate Scrapling interpreter running
`etl.scrape_sportsbooks --transport scrapling --sports soccer_uefa_champs_league
--output-dir <new-capture-directory>`. Run the matched analysis:

```powershell
.venv\Scripts\python.exe -m scripts.analyze_champions_league --capture <new-capture-directory> --form <new-form-directory> --candidate models\model_store\candidates\<new-candidate> --output logs\ucl-analysis-NEW --runs 1000000
```

Optional `--previous <prior-capture-directory>` checks whether current arbitrage
legs also had an arbitrage in the earlier capture. The analysis produces
`analysis.json`, `report.md`, and `markets.csv`, regenerates labeled active-model
forecasts without publishing, and runs seeded Monte Carlo score simulations.
Sparse-history teams may have exploratory simulations while their candidate
classifier forecasts remain excluded. Reversed home/away listings, stale data,
and markets without explicit open availability are rejected. Capture prices
**after** training so they remain fresh for the analysis.

Frozen study evaluation needs no AI. Pick a study containing `trial.json` and its
checksum, evaluate its recorded batches, then aggregate the corresponding study root:

```powershell
.venv\Scripts\python.exe -m scripts.evaluate_accuracy_shadow --trial data\processed\accuracy_shadow\BATCH
.venv\Scripts\python.exe -m scripts.assess_accuracy_study --root data\processed\accuracy_shadow --output logs\soccer-study-NEW.json
.venv\Scripts\python.exe -m scripts.evaluate_nba_freshness_shadow --trial data\processed\nba_accuracy_shadow\BATCH
.venv\Scripts\python.exe -m scripts.assess_nba_accuracy_study --root data\processed\nba_accuracy_shadow --output logs\nba-study-NEW.json
```

Do not merge different frozen policies/models into one root. The assessors reject
incompatible study contracts. Research scripts never establish an automatic model
promotion rule; serving model selection remains an explicit reviewed operation.

## Verification commands

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe -m pip check
.\run_pipeline.bat doctor
```
