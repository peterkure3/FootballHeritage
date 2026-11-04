# Sportsbook odds imported into the training pipeline

Imported **2,084 snapshots from 12 bookmakers** from the saved collection. Training
now automatically reads validated imports from `pipeline/data/processed/sportsbook_odds/`
and joins them to canonical fixtures using an unambiguous team pair and exact UTC
kickoff. Training and rolling backtests share this loader.

Import SHA-256: `5a3770d0b16b4d1ee62b1d390bd98f2f3006c9781e38498234c26c9ff326004f`.
The corresponding directory contains `odds.parquet` and `manifest.json`. The
manifest records the original source file, counts, source checksum, parquet
checksum, import time and join policy. Reimporting identical input is idempotent;
changed source bytes receive a separate import directory. Files are ignored by Git.

Actual observed time is retained and used as the prematch cutoff; provider update
time cannot backdate an observation. Latest valid observed prices per bookmaker
are averaged by the existing odds feature code. Multiple provider/direct source
observations remain preserved in storage, while a bookmaker contributes once per
matched fixture. UNKNOWN availability prices may inform market features but are
not evidence that a bet was executable.

## Readiness at import

- 10,189 canonical fixtures, including 10,107 completed fixtures.
- 8,950 completed fixtures had complete odds before import.
- **0 captured snapshots matched a completed fixture; all 2,084 remain pending.**
- Captured prices cannot create scores or result labels. Once completed fixture
  records with matching kickoff and teams arrive through the existing result
  ingestion path, their saved prematch prices become eligible for training.
- Fixtures missing reliable kickoff time, unmatched team identities, changed
  kickoff or ambiguous team pairs need explicit reconciliation before joining.
- No new model was fitted or activated: this capture contributes no new labeled
  observations today. The existing training dataset and chronological split stay
  intact.

## Commands

From `pipeline/`:

```powershell
py -3 -m models.import_sportsbook_odds --input data/raw/sportsbooks/20261008T174556306527Z/odds_snapshots_complete.jsonl
py -3 -m models.train_model_v2 --dry-run
```

The import command reports completed-fixture matches and pending snapshots. The
usual `py -3 -m models.train_model_v2` automatically reads all validated imports
when building a candidate. New collections must run the import command with their
new JSONL path; scraping alone does not import them.

## Verification

All 41 Python behavioral tests passed. Tests cover idempotent import, stored
checksum integrity, exact kickoff matching, preservation of unfinished status,
observation cutoff and rejection of suspended, live and duplicate snapshots.
The real import command and training dry run read the actual stored data.
