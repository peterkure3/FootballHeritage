# Weekly retraining reuses daily ingestion

`pipeline/run_weekly_retrain.bat` now runs only `models.train_model_v2` followed by `models.predict_v2`. Removed the duplicate raw fetch, transform and database-load steps. Interpreter fallback and failure exits remain, and progress labels now describe two steps.

Run `run_daily_fetch_with_sync.bat` first and wait for it to finish. It owns fetching, transformation, database ingestion, regional odds collection and backend sync. Weekly training consumes the latest stored processed Parquet snapshot, local historical files and checksum-protected sportsbook imports. The trainer already rejects insufficient completed data and invalid chronological partitions. No new freshness guarantee is implied when a daily provider fetch fails and the daily runner continues with a warning.

This separation avoids duplicate provider requests and reprocessing while preserving reproducible candidate training inputs. The weekly trainer continues saving isolated candidates; prediction generation continues using the configured active model. Candidate promotion and further backend sync behavior were not changed.

Verification: inspected the remaining weekly commands and preserved error handling; `git diff --check` passed. `py -3 -m models.train_model_v2 --dry-run` passed using 10,107 completed fixtures and existing imported observations. It validated the chronological dataset splits without fetching data, fitting a model, writing model artifacts or regenerating predictions.
