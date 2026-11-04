# Continuing the frozen EPL trial

Implemented and enabled on 10 October 2026. Current study: candidate
`20261009T100528981075Z`, Bovada regulation-time 1X2, one paper unit per
selection, largest estimated EV, minimum 5% after a 2% payout reduction.
The candidate artifacts and selection policy remain unchanged.

## Where to get selections

Open **Predictions → Paper trials**. The page displays combined study progress,
collector health, pending selections, cumulative ordinary/stressed ROI, batch
ledgers, and the formal assessment when available. Eligible rows identify the
home win, away win, or draw selection and its captured price. Skipped selections
and missing-history exclusions remain visible and do not count toward 200.

The app's normal endpoint is:
`http://localhost:5555/api/v1/prediction-dashboard/paper-trials`.
It now returns `studies` and `collector` alongside the existing `trials` list.
The live endpoint was verified with four settled selections across one UTC
fixture day, ROI -12.5%, stressed ROI -14.25%, and no assessment interval yet.

## Automatic collection

The enabled Windows task `FootballHeritage-PaperTrial-Collection` runs every
15 minutes with windowless Python. Its working directory is `pipeline/` and its
action is `-m scripts.run_trial_collection`. It runs under the current user's
interactive logon: **keep the computer awake and the user signed in**, with
PostgreSQL available. The API/frontend need to be running to view the page;
collection itself does not require either server.

The job refreshes official EPL fixtures once per UTC day, covering the previous
two days through the next 14 days. It uses the existing normalizer/UTC loader,
rejects other competitions and ambiguous IDs, and clears unfinished score labels.
It then collects regional public prices, records new same-day frozen Bovada
forecasts before kickoff, refreshes pending official results across prior dates,
and checks formal assessment eligibility. Other sport/provider ingestion and
weekly retraining are not scheduled by this installer.

Task Scheduler ignores overlapping task invocations; a process-held file lock
also prevents overlapping manual/scheduled runs of the wrapper. Daily ingestion
is marked complete only after success. Failed ingestion does not suppress the
collection/settlement attempt. Fresh-price failure does not suppress settlement.
Formal assessment is attempted separately even if the regional cycle fails.

Official fixture requests retry transient provider errors. Bovada public reads
retry transport failures up to three attempts; denied and rate-limited public
responses are not retried. Persistent primary-source failure is recorded and
returns a nonzero task result, rather than fabricating quotes or silently using
regional prices in the Bovada study.

## Commands

Run one collection manually:

```powershell
cd D:\Github\FootballHeritage\pipeline
py -3 -m scripts.run_trial_collection
```

Install/reinstall the task from the workspace root (the interval defaults to 15 minutes):

```powershell
.\scripts\install_trial_schedule.ps1
```

Inspect or disable the installed task:

```powershell
Get-ScheduledTaskInfo -TaskName 'FootballHeritage-PaperTrial-Collection'
Disable-ScheduledTask -TaskName 'FootballHeritage-PaperTrial-Collection'
```

Explicit assessment check from `pipeline/`:

```powershell
py -3 -m scripts.assess_paper_trial
```

No interval is computed while the sample gates are unmet.

## Formal assessment

- Group by candidate ID, full artifact manifest, exact policy, and bookmaker.
  Changed artifacts, policies, or books create separate study IDs. Conflicting
  duplicate forecasts/results fail; identical duplicate batches do not inflate
  the selection/day counts.
- Require at least 200 settled selected bets across 60 distinct UTC fixture days.
  Pending or ambiguous earlier selections block assessment even if faster-settled
  bets exceed both counts. Skipped/ineligible forecasts never count as bets.
- Choose the first complete chronological prefix satisfying both gates, including
  the whole qualifying day. Write `cohort.json` with its SHA-256 before computing
  any formal interval. Later batches do not change that cohort or repeat a failed
  assessment until it passes.
- Verify selected official result capture hashes and the exact captured provider
  ID, regulation-time status, teams, kickoff and scores before formal assessment.
  Settlement totals are recomputed from frozen forecasts and saved result evidence.
- Perform 10,000 fixture-day cluster bootstrap resamples with seed 42. Report
  ordinary/stressed ROI and 95% intervals, probability calibration bins, paired
  market log-loss/Brier/accuracy comparisons, cohort coverage and stressed drawdown.
- Positive paper evidence requires the stressed ROI interval's lower bound above
  zero. This does not promote a model or establish executable profitability;
  recorded price availability/costs and team/season dependence remain limitations.
- The decision is persisted once. Additional monitoring retains descriptive
  results, while another policy/model needs its own independent validation.
  Cancelled/postponed selections remain unresolved until a verified applicable
  settlement is available; automatic void settlement is not implemented.

## Evidence locations

- Immutable forecasts/settlement receipts: `pipeline/data/processed/edge_trials/`.
- Cohort and assessment: `pipeline/data/processed/edge_trials/_assessments/<study_id>/`.
- Quote ingestion/cycle audits: `pipeline/data/processed/regional_audits/`.
- Official fixture captures: `pipeline/data/raw/trial_fixtures/`.
- Collector health: `pipeline/logs/edge_trial_status.json`.
- Collector logs: `pipeline/logs/edge_trial_YYYYMMDD.log`.

Raw data, models, logs, and trial runtime artifacts remain gitignored. Preserve
these evidence directories between runs and retain the frozen candidate bundle.

## Verification

- Full Python discovery with database checks enabled: 118 tests passed. The
  subsequent official-result provenance test and transport retry tests passed
  in targeted runs (14 trial tests and nine collector tests).
- Nine Chromium feature checks passed, including real saved-model/PostgreSQL API
  responses, both sample gates, a frozen positive paper assessment, failure
  display, pending ROI and mobile width.
- Frontend lint: zero errors, one pre-existing AdminEvents hook warning.
  Type checking and production build passed.
- Real isolated HTTP endpoint: 200 with 4 selections/1 day and immutable active
  artifact hashes unchanged. The normal :5555 endpoint also exposes the study.
- Registered task: windowless Python, PT15M repetition, Interactive logon.
  Task Scheduler-launched run finished successfully with result 0 at
  22:31:07 EAT; health JSON reports success and no failed steps.
- Fallow 3.32 final audit passed with zero introduced findings. Python is outside
  its coverage; missing root node_modules still limits dependency classification.

Review artifacts: `trial-automation-live-20261010.json`,
`trial-automation-schedule-20261010.json`, `trial-automation-fallow-20261010.json`,
and `trial-automation-ui-20261010.png` in this output directory.
