# Pegasus synchronization — 2026-10-13

## Result

Schedule follow-up: the user changed Pegasus's timer to 08:00 Africa/Kampala
on 2026-10-13 and verified the next run as 2026-10-14 08:00 EAT. The earlier
06:00 verification below records the initial setup. Windows synchronization
remains at sign-in and every 30 minutes while the Windows user is signed in.

Prepared Windows-side synchronization from Pegasus PostgreSQL through SSH to
the existing backend database. `scripts/sync_pegasus.ps1` previews by default;
`-Apply` uses a single transaction. Setup commands and connection behavior are
documented in `pipeline/docs/PEGASUS_SYNC.md`.

The pipeline sync resolves source and destination secrets independently from
environment files, removes its hardcoded passwords, uses read-only source
transactions, preserves backend odds when source prices are absent, selects
one latest odds snapshot per fixture, and uses external identity to preserve
event UUIDs when kickoffs change. Failed records roll back the batch.

## Verified

- Pegasus collection: user-provided systemd journal confirms 20 unique fixtures,
  database-content verification, readable backup archives, 10.7-second run,
  152.8 MB peak RAM. Timer is enabled/active at 06:00 Africa/Kampala.
- Six sync tests passed. Four exercised real PostgreSQL in temporary schemas
  created and removed by the suite; real public events were not changed.
- Live Windows read-only preview of three local pipeline fixtures passed.
  Backend database contained 4,164 events. This preview did not use Pegasus.
- Python compile and pyflakes passed; Windows wrapper parsed without errors.
- Fallow pre/post audit summaries match: one dead-code issue, 11 complexity
  findings, maximum cyclomatic complexity 24, one clone group. Existing findings
  remain; Fallow warned that root node_modules was absent.

## Live synchronization and automation

- Actual Pegasus-to-Windows transport and application passed after the user
  opened the tunnel. All 20 fixtures were checked field-by-field after sync;
  existing UUIDs and moneyline pairs were preserved, and the backend stayed at
  4,189 events. Repeat preview planned updates only. See the live JSON audit.
- A dedicated Windows SSH key was generated with private-file ACL restricted
  to the current user. The user installed its public key on Pegasus, and
  noninteractive key login returned `pegasus`.
- `scripts/install_pegasus_sync.ps1` is ready and syntax-checked. Its PT30M
  indefinite trigger was checked; it requires key login and a preview before
  registering the task. The task is registered, its first run synchronized 20
  fixtures with zero errors, and LastTaskResult is 0. State returned to Ready.
  The next run is 2026-10-13 01:22:54 EAT; interval PT30M, Interactive logon.
- An independent key tunnel on port 55434 passed a five-fixture preview and was
  automatically closed. Manual SSH terminals are no longer required.
- Schedule evidence: `pegasus-sync-schedule-20261013.json`.

## Remaining project work

- Odds collection on Pegasus has zero reported credits. Predictions/model
  artifacts are outside this fixture/result sync.
- A password was already embedded in older scripts and shared in conversation;
  rotation and history remediation remain separate work.

Other user changes in the workspace were preserved. The whole build stage is
not complete, and no branch was pushed or deployment performed.
