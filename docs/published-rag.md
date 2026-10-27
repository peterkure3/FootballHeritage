# Published RAG retrieval

RAG uses the existing application PostgreSQL pool whenever `APP_ENV` is set to
anything other than `development`, or `PUBLICATION_STREAM_ID` is present. In this
mode `RAG_DATABASE_URL` is ignored, including URL parsing. The approved active
Football model comes from the enabled publication stream's model manifest;
`RAG_MODEL_VERSION` is only used by the legacy development reader.

RAG and AI Picks share `published_picks::visit_candidates`: a repeatable-read,
read-only transaction, five-second statement timeouts and keyset pages of 100.
Only upcoming, unsettled Football fixtures with matching fixture/prediction IDs,
the active model and predictions generated within the last 24 hours are eligible.
Probabilities must be finite, in range and sum to one within the existing
tolerance. Quotes must have observed timestamps within the past 24 hours.

RAG applies conversation league/day filters before keeping at most 200 candidates
ordered by named-team relevance across user messages, then fixture date/ID. Every
eligible page contributes; the final selection retains at most five predictions.
Evidence includes the stream, record key, publication version/time, model version,
prediction time and original numerical probabilities. Knowledge documents remain
in the application database. Knowledge retrieval has a three-second total timeout;
published prediction retrieval has a ten-second total timeout.

Missing stream/model, disabled source, storage errors and retrieval timeouts yield
`prediction_evidence_available=false` and no prediction evidence. An available
source with no fresh eligible records yields `true` and empty prediction evidence.
General knowledge responses remain possible. There is no local database/HTTP
fallback in published mode. Saved conversations, idempotent request responses,
authentication and provider behavior retain their existing contracts.

The authenticated disposable-database harness is
`pipeline/.venv-scrapling/Scripts/python.exe scripts/verify_auth_http.py`.
It deliberately supplies an invalid legacy RAG URL and an unreachable Python HTTP
URL. `verify_published_rag_http.py` checks cross-page relevance, numerical evidence,
fresh quotes, provenance, replay/history, follow-ups, unavailable sources/models
and withdrawals. Synthetic fixtures exist only in its disposable local database.

## Remaining gateway contracts

Update 2026-10-27: this inventory records what remained after the RAG phase. Its
gateway transports, native intelligence readers/refresh and legacy chat are now
migrated in source via `durable-gateway.md`. Computation remains Python-owned;
hosted rollout is still pending.

These routes still depend on Python and are not covered by the RAG migration:

| Domain / callers | Required work before cutover |
|---|---|
| `predictionService.js`: dashboard fixtures, models, operations, trials and sport previews | Publish domain snapshots/records with pagination/filter parity and canonical sport/provider identities |
| `BestBets.jsx`, parlay search/suggestions/store | Publish reviewed quotes/value inputs and preserve Python calculation, tax, correlation and ranking contracts |
| `FPLAdvisor.jsx` | Publish advice/team data; preserve team evaluation and refresh authorization |
| `CollegeSports.jsx`, `MarchMadness.jsx` | Multi-sport producer/identity contracts and snapshot readers |
| `SmartAssistant.jsx` | Preserve request/response and inference contract separately from RAG chat |
| Administrative refresh/training/collection and intelligence refresh | Durable command execution/status contract; do not turn side effects into GET snapshots |

`pipeline_gateway.rs` remains in place for these domains. A complete gateway
migration cannot be claimed from the existing Football fixture bundle alone.
No hosting settings, credentials, production deployment or existing databases
are changed by this code migration. Neon remains staging.
