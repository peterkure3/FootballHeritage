# Rust RAG chat — 2026-10-08

AI Picks chat now executes a RAG agent inside the Rust backend, replacing the
unconfigured chatbot proxy at `POST /api/v1/ai-picks/chat`. No chatbot files were
changed and no Node chatbot service is required for this feature.

## Implementation

- `backend/src/rag.rs` owns direct read-only PostgreSQL prediction/quote retrieval,
  team/league/date ranking, PostgreSQL full-text knowledge retrieval, evidence
  references, generation and evidence-only responses. It does not call pipeline HTTP.
- `RAG_DATABASE_URL` supplies the prediction database. Connections default to
  read-only transactions with a five-second statement timeout; only fresh active
  model predictions and current bookmaker quotes are retrieved.
- A migration adds indexed `ai_rag_documents` and five authored knowledge documents
  on probability, odds, expected value, freshness and capabilities. No embedding
  service or vector extension is required.
- Rust calls Gemini directly using `RAG_GEMINI_API_KEY` (or backend `GEMINI_API_KEY`)
  and `RAG_GEMINI_MODEL`, default `gemini-2.5-flash`. `RAG_CHAT_MODE=auto` uses
  generation when available; `grounded` returns evidence directly. Missing or failed
  generation returns explicit evidence mode. Unknown P/K source references are
  rejected in generated replies.
- Replies expose source IDs, retrieved facts, mode, model and provider/retrieval
  availability. The frontend shows sources and restores them from saved history.
- The server owns context; supplied prior messages must match saved history. Turns
  save one user and one assistant message atomically. Conversation ownership is
  checked before retrieval/generation, and message ordering uses a sequence column.
- Stable request IDs, scoped by owner, recover completed replies after lost responses.
  Concurrent retries serialize and return the saved response. Reusing an ID with a
  different body returns 409. Chat permits 12 new turns per user per minute; saved
  retries do not consume the allowance.

## Verification

- 23 Rust backend unit tests passed, including retrieval follow-ups, league/day
  restrictions, citation validity, missing odds, context integrity and rate limits.
  Backend built offline and migration applied at startup on port 8888.
- Frontend strict TypeScript/build and lint passed (one existing AdminEvents hook
  warning). Four Chromium/Firefox chat browser checks passed with one worker,
  covering retry IDs, safe text rendering, saved sources and follow-up context.
  The first four-worker run timed out during concurrent compilation; the isolated
  one-worker rerun passed without product changes.
- Actual authenticated chat: HTTP 200, `gemini_rag`, provider available, cited
  model probabilities for Arsenal's next fixtures. Two concurrent identical requests
  returned the same response and produced exactly two messages. Follow-up saved
  exactly four messages total, preserved the fixture reference, and retained evidence.
- Conflicting request ID and forged history returned 409; invalid role, empty and
  overlong messages returned 400; unauthenticated chat returned 401. Another owner's
  conversation read/write returned 404. Request IDs were independently scoped by user.
- AI Picks generation regression returned HTTP 200 with 10 predictions.
- An isolated Rust server in `grounded` mode returned cited knowledge and prediction
  evidence even with pipeline HTTP pointed at a closed port. Unicode character
  limits worked. The test server on 18889 was stopped after verification.
- Git whitespace check passed. Main Rust server remains process 27092 on port 8888;
  no service is listening on chatbot port 3000. Existing users may need to log in
  again after the backend restart.

## Local fixtures and operational notes

Local backend configuration was added to its ignored `.env`; credentials were not
printed or committed. Three isolated QA accounts remain identifiable for cleanup:
`c8d19457-ac43-4b5a-bf52-9f62b4ff4c89`,
`7c5cd42a-4039-4fef-9275-388d7d8f5981`, and
`9042061a-615c-4fa0-bece-e154752496f7`. No financial operations were performed.
The previous backend binary is retained under backend/target for rollback.

Retrieval is lexical and uses seeded product knowledge plus fresh prediction data;
it does not yet include news, injuries, external document ingestion or vector search.
Generated explanations remain estimates grounded by the supplied evidence and
prompt constraints; source-ID validation is not a complete factuality evaluator.
Current fixtures still lack bookmaker quotes. Model promotion and licensed
historical backfill remain pending from the earlier milestone. This is local
implementation verification, not staging sign-off.

Provider implementation reference: [Gemini generateContent](https://ai.google.dev/api/generate-content).
