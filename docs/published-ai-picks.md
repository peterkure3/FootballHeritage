# Published AI Picks contract

`POST /api/v1/ai-picks/generate` retains its authenticated Football filters,
ranking rules, saved `ai_pick_runs`, and response envelope. In every configured
non-development environment, or whenever `PUBLICATION_STREAM_ID` is present,
`AiPicksService` uses `published_picks.rs` and the shared application PostgreSQL
pool. An invalid/missing stream, missing approved model, disabled source, storage
failure or timeout returns 503 with a safe message. There is no Python HTTP
fallback in this mode. Development without a publication stream retains the
existing local Python interface.

The model comes only from the enabled stream's `model_metadata` record
`football:active-model`, schema version 1. Fixture bundles must match that model,
sport/schema and fixture/prediction identifiers. Eligibility preserves the Python
route's 30-day future fixture horizon, unfinished status, UTC date and competition
filters, and 24-hour prediction/quote freshness windows. Expected missing fresh
predictions returns 200 with empty picks and an explanatory summary. Withdrawn
records are excluded. Each selected pick adds publication freshness metadata;
existing selection and explanation fields are retained.

Queries run in a read-only repeatable-read transaction with a five-second statement
timeout and a 15-second total retrieval/ranking timeout. Keyset pages contain at
most 100 fixtures; only the requested best 1–20 picks are retained between pages.
Every eligible page is considered. Equal-ranked fixtures use publication-key
order, making ties deterministic; the old SQL route specified no fixture order.
Malformed publication casts fail closed rather than returning invented results.
This initial reader still needs realistic query plans and latency measurements.

`pick_selection.rs` ports selection/ranking only. Training, feature engineering,
probabilities, simulation and inference remain Python. Twelve frozen cases from
the actual Python `build_picks` function check values, missing quotes and ties;
the Python test verifies both source hash and outputs. Regenerate the contract
only after reviewing a model-selection rule change. These fixtures are labelled
synthetic test data and never serve as runtime fallback.

`scripts/verify_auth_http.py` calls `verify_published_picks_http.py` in its own
disposable loopback database. It tests authenticated HTTP against Python's ranker
over 160 eligible fixtures spanning multiple pages plus stale, future, finished,
wrong-model and invalid-probability cases, with Python HTTP pointed at a closed
port. It also checks saved-run retrieval, missing-model/source failures, empty
dates, stale/future quotes and withdrawal. This proves local request/data flow,
not hosted Vercel compatibility, Neon credentials, full sports coverage, RAG chat
migration or production readiness. Other gateway/RAG Python dependencies remain.

Publication retains the latest observed quote per bookmaker, excluding future
timestamps before selecting the latest quote. The reader then enforces the
24-hour window. A database regression test checks that a future-dated correction
does not hide the preceding observed quote. As with all published evidence, new
eligibility after an idle period requires source refresh/reprojection; the Rust
API never contacts a collector or the local computer to refresh it.
