# Daily and weekly pipeline recovery — 2026-10-15

Both reported JSON errors were caused by files containing only zero bytes:

- `pipeline/logs/edge_trial_status.json`: 260 bytes.
- Sportsbook import `11a742335a6371a6e2df389bd85494f940c18ab87115f6478a4d5f55823952bf/manifest.json`: 892 bytes.
- That import's `odds.parquet`: 17,525 bytes, also entirely zero-filled.

The cause of the on-disk corruption is unknown. A scan of 515 local sportsbook
JSONL files found no source matching the damaged import's SHA-256. The import
cannot be reconstructed from the surviving captures. It and the old health file
were moved intact into `pipeline/data/processed/_quarantine/` with checksums and
a recovery record. See the companion JSON report for exact paths and evidence.
The remaining 247 import manifests and Parquet checksums verified before the live
refresh created another import. No training observations or past successful-run
times were invented. A verified backup could restore the excluded import later.

## Code changes

- Shared JSON saving publishes a unique same-directory temporary file after
  flushing and fsync, then atomically replaces the destination. Failed writes
  preserve the old destination and clean up their temporary file.
- Sportsbook import Parquet data is fsynced before publishing its manifest.
- Invalid manifests still stop training and now identify the offending path.
- Missing, malformed, or unreadable optional collector health does not block the
  paper-trial dashboard or collector. Corrupt health is shown as unavailable,
  without a claimed successful-run time.
- Raw feed JSON arrays remain supported; object validation applies to manifests
  and collector status. UTF-8 BOM files are accepted.
- Structured ETL messages and tracebacks redact API keys in request URLs.
- Raw Odds API fetching stops after a 401 and returns failure. NBA and NCAAB
  failures propagate nonzero status to the batch scripts instead of claiming
  success. Successful empty feeds remain successful. The existing daily batch
  policy continues past these fetch warnings to process available data and
  collect regional quotes.

## Validation

- 38 focused tests passed: JSON resilience (8), provider failures (5), sportsbook
  import (4), collection (5), and regional pipeline (16). One additional regional
  PostgreSQL timezone test was skipped because its opt-in flag was not enabled.
- Changed Python modules compiled; `git diff --check` passed.
- Live `py -3 -m scripts.refresh_regional_pipeline` exited zero: 3,023 collected
  snapshots, 37 matched quotes, six inserted EPL quotes, 100 imported training
  snapshots, no cycle errors. Audit:
  `pipeline/data/processed/regional_audits/20261014T225759729655Z_cycle.json`.
- `py -3 -m models.train_model_v2 --dry-run` exited zero: 21,938 imported
  observations, 10,217 canonical fixtures, 10,135 completed fixtures, and valid
  chronological splits. This did not fit or promote a model.
- Fallow summary and post-change audit ran. The audit reports existing findings
  across the large dirty workspace, with reduced dependency confidence because
  root `node_modules` is absent. It is not a clean gate; see the text artifact.

Full daily batch/backend synchronization and full weekly candidate fitting were
not rerun. The active model was not changed. The separate Odds API 401/account
issue remains: rotate the key exposed in the supplied logs, update the private
environment configuration, and check the provider account's usage/credentials.
Historical logs are not rewritten by the new redaction.
