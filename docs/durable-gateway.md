# Published gateway and durable computation

The Rust production/staging API no longer contacts a Windows HTTP service or
starts a local Python process. Existing `/api/v1/pipeline/...` paths remain.
Completed reads come from PostgreSQL snapshots. Missing or expired outputs and
request-specific computations use an explicit asynchronous contract. The existing
Python interfaces still own models, simulations, calculations and source data.

`pipeline/sync/gateway_routes.json` freezes every existing FastAPI route plus the
native intelligence list/refresh adapters. Unknown routes cannot be queued. A
source stream scopes all request keys and results. Existing provider/sport IDs
and response fields pass through unchanged; the gateway does not infer global
IDs from team names or relabel sports. Optional request bodies retain the existing
256 KiB gateway ceiling. Results are limited to 8 MiB.

## Request behavior

- A completed read returns the original status and JSON, with `X-Data-Source`,
  `X-Generated-At` and `X-Fresh-Until` headers. Generation here is response
  computation time; original model/source timestamps remain in the response.
- Missing/expired output returns HTTP 202, `X-Gateway-Pending: 1`, `Retry-After`
  and a job ID. This never masquerades as an empty successful model result.
- Private computations and administrative actions require an authenticated user
  and a UUID `Idempotency-Key`. Reuse the same key, method, URL and body when
  polling. A changed request using the same key returns 409. Private results are
  scoped to the user. A completed action's retry is an immutable saved response.
- Existing feature policy and administrator restrictions apply to every poll.
  `refresh=true` is administrative. Worker-side administrator status is rechecked
  before execution. Disabled sources cannot serve even previously cached output.
- The shared frontend fetch helper handles only the explicit pending protocol,
  retaining headers/body/key, respecting cancellation and surfacing a pending
  timeout as an error. Other HTTP 202 responses retain their original meaning.

Public snapshots have a reviewed TTL (normally five minutes; selected ranking
and intelligence list views use 30 seconds). Ranking snapshots expire before
visible kickoff, quote-age and prediction-age boundaries. Historical/stale fields
already labelled by the producer retain their original meaning. Successful
side effects invalidate public snapshots; an uncertain write invalidates them
conservatively. Private idempotency replies preserve their original evidence.

Native `/api/v1/intelligence/{devigged-odds,ev-bets,arbitrage}` now uses published
versions of its existing local producer views, retaining filters, limit clamping,
ordering, IDs and decimal strings. Its refresh becomes a durable administrative
operation. The legacy `/api/v1/chat` response shape is served by Rust RAG in
published mode; its health endpoint no longer calls Node.

## Worker lifecycle

Apply `backend/migrations/20261027000001_durable_gateway.sql` with migration
credentials on the approved target. Old applied migration files are unchanged.
`backend/build.rs` makes Cargo notice newly added migration files. The API only
needs the application pool and registered `PUBLICATION_STREAM_ID`.

Run `python -m sync.gateway --env <private gateway env>` from `pipeline/`.
It makes outbound verified PostgreSQL connections; it opens no HTTP listener.
The private environment contains:

```text
SYNC_NEON_DATABASE_URL=<approved gateway-worker connection; sslmode=verify-full>
SYNC_GATEWAY_STREAM_ID=<same approved stream UUID as the API>
SYNC_COMPUTE_PYTHON=<absolute path to the existing complete model environment>
```

The transport environment uses `requirements-sync.txt`; the selected computation
environment needs the existing model/API requirements and `httpx==0.28.1`.
Keep its existing local database and internal-token configuration. No model
promotion or numerical implementation is performed by this transport.

The supervisor prewarms a bounded set of default views and claims jobs using
`SKIP LOCKED`, a five-minute lease and a fresh lease token. Each computation runs
in a separate process with a 240-second deadline and discarded process output.
Only the fenced lease can commit the response. Expired read leases can recover;
expired/failed side-effect leases become `indeterminate`, never automatically
repeat. Review the producer's actual state before manually submitting a new
operation after `COMPUTATION_OUTCOME_UNKNOWN`. Exactly-once external side effects
are not claimed across a crash between a local commit and remote acknowledgement.

The queue limits outstanding jobs to 128 per stream and 16 per private user.
Queued work older than a day is failed. Connections reconnect with bounded
backoff and shutdown waits for the bounded current computation. Public cache
retention/archival remains an operator responsibility; the worker has no DELETE
or TRUNCATE grant. Separate worker processes can claim independent jobs safely.

Windows launchers accept `-Service gateway`, defaulting to `pipeline/.env.gateway`:

```powershell
./scripts/start_pipeline_sync.ps1 -Service gateway -Once
./scripts/install_pipeline_sync_task.ps1 -Service gateway
```

The publication scheduler remains a separate service/task, so slow computation
does not block fixture publication. No task was registered by this implementation.
Use a dedicated gateway role, not the existing fixture sync role. See the grants
and scope requirements in `database-ownership.md`.

## Verification and rollout

`scripts/verify_auth_http.py` creates and removes an exact disposable loopback
database and independent Rust processes. It checks original Python JSON and
validation, native intelligence decimals, real EV insertion/replay, cached reads
with the worker stopped, source/freshness failures, lease recovery, write
ambiguity, CORS, legacy chat, sessions, RAG and Python ranking parity. The real
child executor is also exercised without an HTTP listener. Boundary tests are
`python -m unittest discover -s tests -p test_gateway_publication.py -v` from
`pipeline/`; Node tests cover polling, cancellation and pending timeouts.

This is implementation and local verification. Production deployment, remote
role provisioning, verified hosted TLS and Vercel cold-start/browser checks
require the approved target and rollout. The existing Neon project stays staging;
no deployment, credential change, task installation or operational-data mutation
is performed by the verification harness.
