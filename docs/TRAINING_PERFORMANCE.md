# Weekly retraining: progress and large datasets

Run from `pipeline` with its installed Python environment. The weekly batch file now forwards training arguments and uses unbuffered output:

```powershell
.\run_weekly_retrain.bat --threads 4 --selection-max-rows 100000
```

These are starting settings to benchmark, not a promised speedup. Check available RAM and CPU capacity first, especially if the API or another training process is running. Existing running Python jobs have already imported their code: the new progress display appears on the next invocation. Do not start another full retrain alongside the current job just to see it.

## Progress and ETA

The message `Selecting separate market and history experts on the tuning period` now leads into a live ASCII progress bar. It accounts for 12 stages: four candidate fits with tuning evaluation, a full-development winner refit, and calibration for each expert. Every update includes the expert/candidate, row count, total elapsed time, current-stage elapsed time and ETA.

An interactive terminal updates every second even inside a blocking estimator fit. Redirected output and scheduled jobs receive readable log entries at stage boundaries and a heartbeat every 30 seconds. ETA is approximate and uses completed-stage timings. It reads `estimating` before the first completion, or when the current stage exceeds the estimate. Models have different costs, and full refits are larger than sampled selection fits; the ETA is not a completion deadline or a measurement of iterations inside a solver. This bar covers expert selection/refitting/calibration, not initial data loading or subsequent prediction generation.

## Performance controls

On this Windows installation, a stack trace identified a hang in Joblib's automatic physical-core discovery: it waited indefinitely for a `powershell.exe` CIM query. Training now supplies `OMP_NUM_THREADS` explicitly while fitting and evaluating, as well as applying `threadpoolctl` to loaded runtimes. This bypasses the OpenMP helper's physical-core probe. The prior environment value is restored afterwards. A regression test rejects any attempt to invoke that probe. Backtests also preserve their requested thread budget.

| Argument | Default | Effect |
| --- | --- | --- |
| `--threads` | `2` | Native thread budget for odds-aware training and holdout prediction. Benchmark rather than using every logical CPU automatically. |
| `--selection-max-rows` | Full training period | Deterministic class-proportional cap for candidate fitting within each expert's training period. Tuning remains complete; winners refit on the complete train+tune development period. |
| `--logistic-max-iter` | `2000` | Iteration limit for all logistic candidate fits and final logistic refits. Lower values may underfit; convergence warnings remain visible. |
| `--logistic-solver` | `lbfgs` | Optional `saga` or `newton-cholesky`, supported by the project's scikit-learn versions. Benchmark selection score, convergence and runtime before choosing. |
| `--trees` | `200` | Histogram boosting iteration count in the default odds-aware strategy. This does not control logistic fitting time. |

Example for an explicitly faster experiment, saved as a new candidate:

```powershell
py -3 -u -m models.train_model_v2 --threads 4 --selection-max-rows 100000 --logistic-solver newton-cholesky --logistic-max-iter 500
```

`newton-cholesky` is worth benchmarking when rows greatly outnumber features times classes; its Hessian memory scales quadratically with that feature/class dimension. `saga` is another option for large datasets, with scaled features (the existing logistic pipelines already scale them). These are optional alternatives, not changes to the default model. See [scikit-learn's solver guidance](https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.LogisticRegression.html).

The existing two-expert selection already uses histogram boosting rather than the legacy gradient-boosting ensemble. Repeated whole-frame copies for odds masks have been removed, and candidate-fitting/tuning slices are reused. No random internal histogram-validation split has been introduced: early stopping remains disabled to preserve the chronological evaluation design.

## Extremely large datasets

The new cap reduces eight candidate-training workloads; it does **not** bound ingestion memory, feature construction, tuning, calibration or full winner refits. This trainer is still an in-memory batch trainer. For data exceeding RAM:

1. Profile loading, feature generation, each candidate, refitting and calibration separately using the stage logs. Keep exact fixture deduplication and pre-match odds provenance.
2. Move canonical/features storage to partitioned Parquet and process partitions chronologically, persisting the rolling team-history state. Cache keys must include dataset contents, feature schema and split boundaries. This requires a separate implementation; caching is not currently added here.
3. Evaluate an incremental history/market expert using `SGDClassifier(loss="log_loss")` and `partial_fit` over batches, with incremental scaling and separate future tuning/calibration/test windows. This is a new candidate strategy requiring validation, not a drop-in change to existing artifacts. [Incremental classifier reference](https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.SGDClassifier.html).
4. Consider less frequent hyperparameter selection and regular refits of a previously selected configuration, keyed to the feature schema and training policy. Do not skip validation or automatically promote a candidate because it trained faster.
5. Keep process parallelism and native threads within the CPU/memory budget. Parallelizing all eight candidates can multiply RAM consumption and native thread counts. [Parallelism and oversubscription guidance](https://scikit-learn.org/1.8/computing/parallelism.html).

Compare tuning log loss, class calibration and held-out results against the existing baseline. Sampling and solver/iteration changes can change which model wins. Holdout windows remain separate and the final test labels are never used for fitting or selection. Defaults retain full-data fitting and the original solver/iteration limits.
