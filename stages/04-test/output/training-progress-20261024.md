# Weekly retraining progress and CPU detection

## Findings and changes

The single expert-selection log message concealed 12 sequential stages (eight candidate fits/tuning evaluations, two development refits and two calibrations). Added dependency-free progress with a one-second terminal heartbeat or 30-second redirected-log heartbeat. Stage/row counts, total and current elapsed time, and approximate ETA remain visible during blocking fits. Estimates begin after a completed stage; heterogeneous candidate/refit costs limit their accuracy.

A default-environment synthetic selection run stalled. Faulthandler pinpointed scikit-learn histogram fitting waiting in Joblib's `_count_physical_cores_win32` for `powershell.exe ... Get-CimInstance ... NumberOfCores`, with no subprocess timeout. Bounded-runtime settings alone did not prevent the probe. Explicit temporary `OMP_NUM_THREADS` plus `threadpoolctl` bypass it; the previous environment is restored even after failure. Training and backtests now pass through the requested thread budget, including holdout prediction. Existing user training/services were not stopped; only our three stalled diagnostic test trees were cleaned up.

Added optional candidate-only row limits and logistic solver/iteration controls, forwarded from the weekly batch file. Defaults retain all data and original solver settings. Winners still refit on the full train+tune development period; calibration/test periods remain separate. The trainer still requires in-memory data and full refits; this is not an out-of-core implementation. No user datasets or model artifacts were overwritten and no full weekly retrain or production promotion was run.

## Verification

- Progress tests: 3 passed (ETA, heartbeat during blocking work, error cleanup and terminal output).
- CPU-resource tests: 2 passed (restore environment, invalid budgets).
- Selection tests: 10 passed in the default environment, including chronological leakage protections, artifact compatibility, sampled candidate/full refit behavior, and an assertion that physical-core discovery must not run.
- Existing model pipeline tests: 17 passed.
- Behavior comparison against the committed baseline on 240 deterministic fixtures: identical selection scores/winners and maximum probability difference **0.0** with default settings.
- CLI `--help`: passed; new flags exposed. Python compilation and Git whitespace checks passed.
- Earlier unbounded diagnostic runs stalled and were terminated; after the explicit OpenMP fix the suite completed normally. Fallow was unavailable locally (`npx --no-install fallow --summary` reported a missing package), so no successful Fallow analysis is claimed.

32 targeted tests passed. Large-dataset wall-clock improvement is not benchmarked; performance flags can change candidate selection and require quality comparison. See `docs/TRAINING_PERFORMANCE.md` for exact commands and scaling limits.
