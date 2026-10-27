# Performance report

No production performance claim is made. Test execution duration is not ingestion,
database, model or synchronization throughput. Synthetic unit fixtures are not a
realistic benchmark dataset. Existing measured training work remains in
`docs/TRAINING_PERFORMANCE.md`; it is not a measurement of this architecture.

## Measured frontend build artifacts

Successful local builds used React 19, TypeScript 7.0.2 and Vite 7.3.7:

| Artifact | Eager-import baseline | Lazy routes before security update | Final build with Zod 4.6.7 |
|---|---|---|---|
| Main JS entry | 661.62 kB | 304.28 kB (304,276 bytes) | 341.37 kB (341,373 bytes) |
| Main CSS entry | 148.36 kB | 97.49 kB | 97.49 kB (97,492 bytes) |

The final main JS entry is approximately 48% smaller than baseline; main CSS is
approximately 34% smaller. Deferred pages now load separate chunks; shared vendor
chunks remain. These are artifact sizes, not browser latency or total downloaded
application-size measurements. Zod 4.6.7 increased the entry versus the intermediate
build; its security fix is retained. Build output reported two upstream Zod
tree-shaking annotation warnings without build failure. No model/throughput or
API-latency improvement is inferred from these bundle measurements.

| Required measurement | Baseline | After | Evidence needed |
|---|---|---|---|
| API p50/p95/p99 | Local debug baseline | Local debug repeat | See dated measurements below; release/hosted results remain pending |
| Query latency / plans | Local point lookup | Local actual reader query | Raw EXPLAIN (ANALYZE, BUFFERS) included in dated evidence; hosted plans pending |
| Vercel cold start | Not measured | Not measured | Invocations with runtime cold-start evidence, region and Neon suspension state |
| Ingestion throughput | Not measured | Not measured | Existing saved captures, rows/second, HTTP calls/cache hits, provider pacing |
| Feature engineering | Not measured | Not measured | Fixed chronological dataset, parity hash, rows/second |
| Inference | Not measured | Not measured | Same trusted model, threads, rows and exact/within-tolerance outputs |
| Monte Carlo simulation | Not measured | Not measured | Fixed seeds, scenarios/second and distribution tolerances |
| PostgreSQL bulk writes | Not measured | Not measured | Realistic row widths/indexes/conflicts and transaction sizes |
| Local-to-Neon publication | Not measured | Not measured | Bundle bytes, events/second, TLS latency, retries, replay and backlog-drain time |
| CPU / memory | Not measured | Not measured | Host/runtime versions, peak RSS, CPU samples and concurrency |

Run remote benchmarks on a confirmed development branch/preview, not production
without a reviewed load budget. Preserve raw samples and report percentiles
alongside errors and sample count. Compare one change at a time. Do not claim an
async rewrite, new dataframe engine, or Rust migration is faster without evidence.

## Local gateway measurements — 2026-10-27

Windows loopback PostgreSQL; 1,000 captured local fixture rows and synthetic contract quotes.
Rust debug binaries, one HTTP worker and at most three database connections per API process.
The worker was stopped during cached reads. Source data was read only; test accounts and
publications existed in a newly created disposable database. No Neon or Vercel load ran.

| Run | API processes | Concurrency | Samples | Errors | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Queue-path baseline | 1 | 1 | 40 | 0 | 100.05 | 192.86 | 232.95 |
| Queue-path baseline | 4 | 4 | 160 | 0 | 116.96 | 139.84 | 167.07 |
| Cached-read repeat | 1 | 1 | 40 | 0 | 144.26 | 233.59 | 283.47 |
| Cached-read repeat | 4 | 4 | 160 | 0 | 86.92 | 216.44 | 452.77 |

The repeat uses a single approved-source SELECT for completed reads, avoiding the
queue transaction and stream lock. These runs were not a controlled host-load experiment;
other verification work ran concurrently and latency varied. No reliable speedup, release
latency budget or production throughput is inferred. Percentiles use nearest rank; the
40-sample p99 is its maximum. Samples are stored sorted, with query plans and role-test results.

The baseline plan measures the publication point lookup. The repeat plan measures the
actual cache reader with enabled-source, completed-state and freshness predicates.

[Repeated samples and query plan](../stages/03-build/output/durable-gateway-20261027/performance.json),
[baseline samples](../stages/03-build/output/durable-gateway-20261027/performance-baseline.json).
Vercel cold starts, verified Neon TLS/role transport, release-build concurrency and full
ingestion/inference/simulation throughput are separate unmeasured rollout gates.
