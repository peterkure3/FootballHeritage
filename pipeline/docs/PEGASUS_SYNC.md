# Pegasus to Windows backend synchronization

Pegasus collects Premier League fixtures/results daily at 06:00 Africa/Kampala.
Its PostgreSQL container is `fh-pegasus-db`, listening on Pegasus loopback port
55432. The Windows backend uses its existing `backend/.env` configuration.

Run the sync on Windows. `scripts/sync_pegasus.ps1` opens an SSH tunnel on local
loopback port 55433, reads Pegasus credentials from a private local file, and
executes the existing pipeline-to-backend event mapping. It closes only the SSH
process it started. An existing tunnel may also be used. The default is a
read-only preview; `-Apply` writes one transaction.

## First-time setup (Windows PowerShell)

Check SSH key authentication:

```powershell
ssh -i "$env:USERPROFILE\.ssh\footballheritage_pegasus_ed25519" -o IdentitiesOnly=yes -o BatchMode=yes peterkure3@pegasus hostname
```

It must print `pegasus` without asking for a password. A dedicated key was created
during this setup at the path above; its private-file ACL grants only the current
Windows user access. Install its public key using your existing password login:

```powershell
Get-Content -LiteralPath "$env:USERPROFILE\.ssh\footballheritage_pegasus_ed25519.pub" | ssh peterkure3@pegasus "set -e; umask 077; mkdir -p ~/.ssh; echo >> ~/.ssh/authorized_keys; cat >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys"
```

This appends only the public key, leaving other authorized keys in place.
Never share the private key. If the private
key is later encrypted, an available SSH agent is required for unattended runs.
The wrapper automatically uses this dedicated key, including paths with spaces.

Copy only PostgreSQL credentials, keeping the provider API keys on Pegasus:

```powershell
$syncDir = Join-Path $env:LOCALAPPDATA 'FootballHeritage'
New-Item -ItemType Directory -Path $syncDir -Force | Out-Null
scp peterkure3@pegasus:.config/footballheritage/pegasus-db.env "$syncDir\pegasus-db.env"
```

The credential file is outside Git. Treat it as a secret and never paste its
contents into chat or commit it. `backend/.env` must contain the backend's
`DATABASE_URL`; source and destination credentials are resolved independently.

From the Windows repository root:

```powershell
powershell -NoProfile -File .\scripts\sync_pegasus.ps1 -Limit 5
```

Review the fixture list and insert/update plan. Then apply the complete sync:

```powershell
powershell -NoProfile -File .\scripts\sync_pegasus.ps1 -Apply
```

Repeat the preview to check that the same fixtures would update, not create new
events. Log output is in `pipeline/sync_to_backend.log`; SSH errors are stored
beside the private credential file. If connections fail, the wrapper returns a
failure rather than claiming the data was synchronized.

## Automatic Windows synchronization

After installing the public key, run from the Windows repository root:

```powershell
powershell -NoProfile -File .\scripts\install_pegasus_sync.ps1
```

The installer verifies key login and a five-fixture read-only preview, then
registers `FootballHeritagePegasusSync` and starts it. It runs at sign-in and every
30 minutes while the current Windows user is signed in, with network availability
and a ten-minute execution limit. It reconnects its own SSH tunnel, so a manual
terminal is not needed. A closed or sleeping Windows computer catches up when
it becomes available. Pegasus continues collecting independently.

The installer stops if a task of the same name already exists rather than
overwriting it. To inspect a run or trigger an additional sync:

```powershell
Get-ScheduledTaskInfo -TaskName FootballHeritagePegasusSync
Start-ScheduledTask -TaskName FootballHeritagePegasusSync
```

## Mapping and failure behavior

- The source connection is read-only. Both sessions use UTC for fixture times.
- Football event identity is `(football_pipeline, match_id)`; NBA identity is
  `(nba_pipeline, game_id)`. A rescheduled fixture retains its backend event UUID.
- Existing untracked events can be adopted when sport, team names and kickoff
  match exactly. Multiple candidates stop the sync for review.
- Only the latest odds row per fixture is selected. Missing source odds preserve
  existing backend moneylines. New fixtures without odds retain null prices.
- A record failure rolls back the entire batch and exits unsuccessfully.
- This synchronizes fixtures/results into `events`, not pipeline model artifacts,
  predictions, accounts, balances or bets. Odds collection on Pegasus awaits quota.

## Verification recorded 2026-10-13

Six regression tests passed, including live PostgreSQL tests in disposable
schemas for preview, latest-odds selection, unchanged odds, rescheduled event
identity, and complete rollback. A three-fixture preview against the Windows
databases passed; the backend retained 4,164 events at that earlier check.

The actual Pegasus tunnel was subsequently verified. All 20 source fixtures
were synchronized and their league, kickoff, team names, scores and status were
checked against the source. All 20 existing event UUIDs and price pairs survived;
the backend retained 4,189 total events during that sync. A repeat preview planned
20 updates and no new events. The audit is
`stages/03-build/output/pegasus-sync-live-20261013.json`; the before-state snapshot
is private under `%LOCALAPPDATA%/FootballHeritage`, outside Git.

Both PowerShell scripts parsed successfully and the repetition trigger was
validated as PT30M with no duration (indefinite). The public key was installed,
key-based login returned `pegasus`, and the Windows task was registered.
Its first scheduled sync completed with result 0 and 20 fixtures synchronized.
The task returned to Ready; its next run was 2026-10-13 01:22:54 EAT.
An independent key-based tunnel on port 55434 also passed a five-fixture preview
and was closed by the wrapper. The manually opened tunnel can be closed.
Schedule evidence is in `stages/03-build/output/pegasus-sync-schedule-20261013.json`.

```powershell
py -3 -m unittest discover -s pipeline/tests -p test_backend_sync.py -v
```

The PostgreSQL tests require `SYNC_TEST_DATABASE_URL` and automatically create
and remove separate test schemas. Without it, the live tests are skipped.

Fallow baselines are in `stages/03-build/output/pegasus-sync-fallow-*.json`.
The repository already has unrelated Fallow findings and a dirty working tree;
those are not corrected by this change.
