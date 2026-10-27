# Local Windows pipeline publication

Status: scripts prepared; no scheduled task, private credential file or production
connection was created by this work. Existing ingestion/training tasks remain.

Keep PostgreSQL private on loopback and preserve existing models/data/backups.
Use a supported Python with wheels for `requirements-sync.txt`; the sync venv is
separate from existing ML environments. It does not upgrade Pandas/sklearn/models.

1. Read `database-ownership.md` and `neon-sync-design.md`. Back up local PostgreSQL
   and rehearse the new additive migrations against a disposable copy first.
2. Create private `pipeline/.env.sync` from the SYNC_* variables in `.env.example`.
   Configure loopback local PostgreSQL, a verified-TLS Neon development destination,
   and the reviewed active model version. Protect the file with the user's Windows
   ACL; never commit or print it. Existing `.env` files are not replaced.
3. From repository root run `./scripts/setup_pipeline_sync.ps1`. This creates
   `pipeline/.venv-sync` and installs transport-only dependencies. Add
   `-ApplyLocalMigrations` only after reviewing the local migration target/backup;
   it refuses a non-loopback host and verifies previously applied checksums.
   Use migration credentials for setup, then restricted local runtime credentials.
4. Validate the additive backend migration on the intended Neon development branch
   with its migration identity. Register the local stream UUID in `published.sources`
   and validate restricted role grants. Do not register against a guessed project.
5. Set private SYNC_* variables in the process when using the direct Python CLI,
   or use the supervisor's `--env pipeline/.env.sync`. Perform an explicit initial
   `py -3 -m sync.football --bootstrap --model-version <reviewed-version>` from
   `pipeline/`; this is the only intentional full source enumeration. The supervisor
   subsequently uses the dirty queue. Creating triggers does not backfill old rows.
6. Run `./scripts/start_pipeline_sync.ps1 -Once`; inspect the UTC JSONL log in
   `pipeline/logs/publication-YYYYMMDD.jsonl`, local queue status and reconciliation.
   Record IDs/status, never payloads or credentials. Keep the destination preview-only
   until API contracts and restricted-role tests pass.
7. Run `./scripts/install_pipeline_sync_task.ps1` after that review. It creates a
   distinct non-overlapping limited-user task at sign-in and refuses to overwrite
   an existing task. `-StartNow` explicitly starts it. Settings restart the process
   after failure; the Python supervisor reconnects with bounded jitter. Task state:
   `Get-ScheduledTaskInfo -TaskName FootballHeritage-NeonPublication`.

The default task requires the user to sign in after reboot, stay signed in, and
keep the computer awake. **Unattended boot operation has not been configured**;
that requires a reviewed service/task identity and credential/CA access. Do not
claim an interactive sign-in task is an always-on Windows service.

Status from `pipeline/` after loading private variables:

```powershell
.\.venv-sync\Scripts\python.exe -m sync.worker --status
.\.venv-sync\Scripts\python.exe -m sync.outbox
.\.venv-sync\Scripts\python.exe -m sync.reconciliation
```

`sync.outbox --requeue <event-uuid>` retries one reviewed dead letter without
changing its effect or version. No bulk automatic repair is provided. Intentional
deletion uses the publisher tombstone API; deleting a raw source row does not
delete production state.

SIGINT/SIGTERM ask the supervisor to finish its current bounded operation and
close connections. Force-killing a task releases PostgreSQL locks; replay handles
an interrupted acknowledgment. Test forced stop/restart/reboot on the development
destination before production. Database statement/connect/lock timeouts are finite;
Task Scheduler's force-stop is not itself a graceful shutdown guarantee.
