# Football Heritage - Codebase Index

## Admin Features UI — 2026-10-27

Refreshed `/admin/features` with availability metrics, separated search and user
access controls, responsive feature cards, status badges, and an audit panel.
Confirmation and policy endpoints are preserved. Five Chromium browser tests,
targeted lint, and production build/typecheck passed; desktop/mobile fixtures
were visually reviewed. See `stages/03-build/output/admin-features-ui-20261027.md`.

## Durable gateway completion — 2026-10-27

Production/staging gateway paths now read PostgreSQL response snapshots or queue
explicit durable computations, with no Windows HTTP/local-process fallback.
Existing Python interfaces retain their filters, models and numerical behavior;
private/admin requests use scoped idempotency and leased execution. Native
intelligence lists/refresh and legacy chat also use publications/Rust RAG.
Ranking snapshots expire at kickoff/evidence boundaries. Strict Clippy is fixed
without suppressions. See `docs/durable-gateway.md` and the current phase report
for executed checks and local measurements. Neon remains staging; no deployment,
credentials or scheduled-task changes were made.

## Published RAG retrieval — 2026-10-26 continuation

RAG now shares the AI Picks publication candidate reader and application pool in
configured non-development environments or whenever a publication stream is set.
The legacy prediction database URL is not parsed in this mode. Retrieval keeps a
bounded relevance window across all eligible pages and includes publication
provenance and observed fresh quotes. See `docs/published-rag.md` for contracts
and the remaining gateway domains. Gateway migration and production readiness
remain incomplete; Neon stays staging and no deployment/credential changes occur.

## Durable sessions and published AI Picks — 2026-10-26 continuation

The session blocker described in the earlier foundation entry is now fixed in
source with Neon-owned `auth_sessions` and async shared-pool validation. Real
independent-process HTTP checks verify restart, revocation, atomic registration
rollback/retry and concurrent login locking. See `docs/auth-session-design.md`.

AI Picks generation now reads approved published model/fixture records in every
configured non-development environment or when a stream is configured. The Rust
selection port matches 12 frozen Python cases and an authenticated multi-page
HTTP comparison with Python offline. Source projection rejects other sports,
publishes the explicit model manifest atomically and excludes future-dated quotes
before choosing the latest observed quote. See `docs/published-ai-picks.md` and
`stages/03-build/output/published-ai-picks-20261026.md` for phase evidence.

Still pending: RAG/local database separation, remaining gateway domains,
multi-sport adapters, restricted Neon transport/role validation, representative
performance measurements and hosted Vercel checks. No production deployment or
credential change. Keep the existing Neon project for staging.

## Architecture audit and publication foundation — 2026-10-26

Added architecture/API/schema audits, target/ownership/sync/migration/Windows/
deployment/rollback/performance documents and `pipeline/sync/`: allowlisted
versioned bundles, atomic source capture/outbox, commit receipts, retries,
tombstones, dead-letter recovery and reconciliation. Existing models, producers,
legacy sync and gateway remain intact. Native Rust `/api/v1/predictions/{match_id}`
reads publications with pending/freshness states; legacy chat no longer logs or
slices prompt text. Frontend routes are lazy-loaded; Zod has a focused 4.x security
update. See `stages/03-build/output/publication-foundation-20261026.md` for checks.

User decision: current Neon project stays staging; production target later.
Publication DDL succeeded only on isolated child `codex-publication-contract-20261026`
(`br-lucky-wind-b4r6rgn1`); parent staging is untouched. No deployment, credential
change, local operational migration or model promotion. Gateway, AI Picks/RAG,
multi-sport publication and hosted end-to-end verification remain before cutover.

Critical serverless finding: `auth.rs::ensure_active_session` requires an
instance-local DashMap session. Persistent Neon-owned sessions and independent
instance/restart verification are required before release; local browser tests
do not validate that behavior. See the audit/migration plan.

## Manager-feature feasibility and Clásico form audit — 2026-10-26

Exact saved-model replay confirms 25 October Barcelona–Real Madrid form inputs: Barcelona WWWWW, Madrid WWLWW; probabilities 60.2710% / 15.0580% / 24.6710%. Form was league-scoped and managers were absent. Added a research-only lagged manager-state layer and chronological ablation over 1,819 verified Wyscout matches after seven metadata quarantines. Held-out accuracy was unchanged at 50.85%; log loss improved only 0.00388 with a bootstrap interval crossing zero. Current-match coaches are never exposed to their own prediction vectors. No serving changes or retrospective forecast edits; multi-season, announcement-dated assignments remain necessary for production. Details: `stages/03-build/output/manager-impact-and-clasico-form-20261026.md`.

## League models and bookmaker grid — 2026-10-25

La Liga and nine other supported competitions are available in the grid menu. Added country-scoped competition identities, reviewed domestic club aliases, full-inventory Scrapling refresh, HTTP cache evidence and secondary-ingestion cache exclusions. Refreshed official histories/fixtures and imported 459 timestamped sportsbook observations across three audited captures. Eight additional domestic models trained on 20,211 completed matches and generated 191 pre-match forecasts, published separately from the global active model with explicit provenance. Daily refresh regenerates league forecasts; weekly retraining includes the additional models. Championship's held-out log loss was worse than its prior baseline. Unavailable sources, missing adapters and exhausted paid-feed quota remain documented. No hosted deployment. See `stages/03-build/output/league-models-and-grid-20261025.md` for sources, metrics and verification.

## Hosted login/CORS runtime repair — 2026-10-24

Browser CORS failures masked Vercel HTTP 500 startup errors: the backend could not initialize its database, then a malformed `HTTPS_ENABLED` value blocked configuration loading. The user supplied the correct Neon staging URL securely; added Production `APP_ENV=production` and `RUN_MIGRATIONS=false`, normalized the three non-secret HTTP/origin settings, and redeployed existing commit `d8aaa59`. Both preflights and anonymous features now return 200 with the exact frontend CORS origin; invalid login JSON returns 400 with CORS, and an untrusted origin remains blocked. No application source, migrations, wallet operations or account login records were changed. See `stages/05-deploy/output/vercel-cors-20261024.md`.

## Authenticated Vercel build diagnosis — 2026-10-24

CLI login completed as `peterkure3`; GET-only inspection confirms frontend root `frontend`, backend root `backend/src`, and both production branches set to `feature/footballheritage-frontend`. Frontend's latest existing production deployment is READY, but `VITE_API_URL` lacks Preview scope. The latest backend build fails on 16 SQLx compile-time connection errors. Added Cargo `[env] SQLX_OFFLINE="true"` to use checked-in query metadata without shell flags or a live build database. Hosted `APP_ENV` and `RUN_MIGRATIONS` are absent; do not cold-start the API until production controls and migration disabling are configured. No cloud settings, deployments or database operations were changed. See `stages/05-deploy/output/vercel-staging-20261024.md` and its redacted hosted inventory/logs.

## Vercel staging environment diagnosis — 2026-10-24

Reproduced the frontend production build's rejection of the local HTTP API URL. Build validator and production API client now share the strict HTTPS URL contract; production cannot fall back to localhost. Seven policy/config tests, lint, a fixture-URL Vite build, locked Rust check/build and 31 database-free Rust tests pass; five isolated pipeline tests and syntax checks pass. Pinned CLI 65.2.0 works but is logged out; no local Vercel links exist and team-scoped settings/env reads require authorization. The current checkout is D:, while C:\FootballHeritage contains backups. No hosting/Neon mutation was performed. See `stages/05-deploy/output/vercel-staging-20261024.md` for service mappings, required staging variables, direct RAG connection requirements and Linux/hosting blockers.

## Local prediction API database repair — 2026-10-24

Corrected the local pipeline `DATABASE_URL` database path to `football_betting`; its empty path overrode `DB_NAME` and connected to `postgres`, where `matches` did not exist. Restarted the local Python API. Rust gateway fixtures, operations and paper-trials endpoints now return HTTP 200; fixture page 1 contains six of 18 upcoming fixtures. No schema or data changes. See `stages/03-build/output/local-prediction-db-fix-20261024.md`.

## Local frontend login routing repair — 2026-10-24

Local `frontend/.env` now points to `http://127.0.0.1:8888/api/v1`: on this machine `localhost:8888` reaches a different Docker/WSL service instead of the native Rust backend. Verified real browser login, profile redirect, authenticated reload/profile request and logout. The existing smoke script encountered a separate logout-navigation race; a focused browser check passed. Two isolated QA accounts remain. See `stages/03-build/output/local-login-fix-20261024.md`.

## Rust Vercel adapter and Windows database launchers — 2026-10-24

Added an empty `[build]` table to the Cargo config after reproducing the upstream Rust adapter's unsafe `config?.build.target` dereference. Host target, manifest, lockfile and API remain unchanged. Current upstream standalone HTTP proxy support means Actix does not always require `vercel_runtime`; deployed adapter/settings still need team access and hosted verification. Backup/restore BAT launchers now probe working Python 3 interpreters, including `py -3`, and provide help-only verification. See `stages/05-deploy/output/rust-vercel-20261024.md` for diagnostics, checks and remaining blockers.

## Retraining progress and Windows CPU-probe hang — 2026-10-24

Odds-aware weekly training now reports 12 candidate/refit/calibration stages with a live elapsed/ETA heartbeat. Explicit OpenMP budgets avoid the reproduced Joblib PowerShell physical-core detection hang; inference and rolling evaluation also respect the requested CPU budget. Optional selection-only row caps and logistic solver/iteration flags preserve complete development refits and chronological holdouts. Defaults produced identical probabilities and selection scores on 240 deterministic fixtures. See `docs/TRAINING_PERFORMANCE.md` and `stages/04-test/output/training-progress-20261024.md`.

## Applied migration line endings — 2026-10-24

Restored the original LF bytes for the AI Picks/Rust RAG migrations after Git's CRLF conversion caused SQLx checksum rejection. `.gitattributes` protects newer migrations while preserving older mixed history. Read-only validation of the actual SQLx-embedded source matched all 18 currently applied records; no migration or checksum record was modified. See `backend/docs/MIGRATION_CHECKSUMS.md`.

## Rust deployment binary selection — 2026-10-23

`backend/Cargo.toml` explicitly selects `football-heritage-backend` (`src/main.rs`) and gates initialization/wallet-reset executables behind `maintenance-tools`. CI compiles/tests opt-in targets without running their operational entrypoints. The API still uses Actix `HttpServer`; native Vercel Rust Functions compatibility remains separate from binary selection. See `backend/docs/VERCEL_BINARY_SELECTION.md` for runtime and `PORT` requirements. Routes, authentication, feature policy and migrations are preserved; no deployment or database operation is authorized by this note.

## Soccer event dataset and simulation baseline — 2026-10-22

Acquired all 3,251,294 Wyscout public events across 1,941 matches with provider MD5 and SHA-256 verification. Normalization retains 1,930 matches and quarantines 11. Added an isolated possession-bootstrap simulator, native-ID batch inference and player attribution with sampled substitutions. Seven competition models use independent chronological splits: 1,341 training, 295 validation and 294 test fixtures; 589,000 match rollouts and 29,400 player trajectories. Results are mixed versus the goal baseline and pass-count intervals are underdispersed; all models remain inactive. Unknown actors and substitution-time diagnostics remain explicit. Verification: 26 tests plus five subtests, zero Pyflakes errors, saved-model replay, batch CLI, 50,000-run convergence and full artifact certification. See `stages/03-build/output/soccer-event-simulation-20261022.md`; raw data and models are local/ignored.

## Bookmaker grid coverage repair — 2026-10-21

UCL grid ingestion now resolves reviewed Inter, Bayern, Brugge/Lens, Sporting and Viking names and reads the normalization manifest's expanded dataset. Audited captures retain HTTP-cache exclusions. The grid adds decimal odds, puts populated requested sources first and shows per-source fixture coverage. Live DB verification found quotes for all seven October 21 UCL fixtures (6–10 stored sources each); the upcoming API excludes games after kickoff. See `stages/03-build/output/bookmaker-grid-update-20261021.md` and the companion live JSON.

## UCL history backfill — 2026-10-21

Collected four-season senior competitive histories for all 18 clubs playing on 21 October: 2,815 unique fixtures, 884 additional fixtures against the previous reviewed candidate scope. The separate regulation CSV contains 2,757 results; 58 awarded or ambiguous extra-time/penalty records remain outside training. Season inventories, public results, official Viking records and raw checksums accompany per-team exports. No database or active-model writes. See `stages/03-build/output/ucl-history-backfill-20261021.md`; earlier betting probabilities have not been recalculated on this expanded history.

## Public NBA odds — 2026-10-21

Added strict Scrapling NBA moneyline collection from public bookmaker pages/feeds. Final capture accepted 34 complete pairs across 17 fixtures from Cloudbet and betPawa, independently matched against BALLDONTLIE NBA games. Its current/opening odds endpoints returned 401; Bovada's stale cached price response was rejected and Betika's denied Uganda origin was not harvested. Intelligence verifies capture checksums/freshness and excludes 31 older stored NBA fixture entries not corroborated by the independent schedule, without DB deletion. Candidate string timestamps and reviewed NBA history aliases are supported. Existing regional refresh invokes the Scrapling collector before publication. 13 new and 24 intelligence tests passed; regional suite passed with one gated skip. Live price/de-vig/EV replay passed. See `stages/03-build/output/nba-public-odds-20261021.md`.

## Sport betting intelligence — 2026-10-20

AI Picks now links to `/ai-picks/intelligence`, six sport summaries and sport-scoped predictions, de-vigged odds, EV, props and arbitrage views. Sport home/Insights links preserve sport scope. `etl.betting_intel` atomically publishes read-only inputs from existing sources and explicitly labeled candidate previews; the new `/api/v1/betting-intel` overview and `/{sport}` endpoints recheck freshness without training or placing bets. Existing regional/daily refresh entry points publish snapshots. Prop collection uses event-specific decimal odds and exact unique fixture matching; no arbitrary first-event association. Verified 30 inactive NBA candidate forecasts, but no fresh NBA prices/props in the current snapshot. Build, 24 new unit checks, seven Chromium tests and live API/desktop/mobile checks passed. Existing AI Picks tests passed; regional tests passed with one DB-gated skip. Repository-wide Fallow remains failing; the new TSX complexity findings were resolved. No active model promoted. Details: `stages/03-build/output/betting-intelligence-20261020.md`.

## Football form coverage and candidate — 2026-10-19

Added `etl.fetch_football_form`: dated last-five W/D/L exports and validated completed-result imports across ten football-data.org competitions. Captured 1,204 results and 106 upcoming fixtures; 96 have five provider-covered results on both sides, ten remain incomplete. This is limited provider coverage, not complete betPawa/all-competition coverage. Candidate `team_form_20261019` uses 11,235 completed fixtures; reproduced chronological test accuracy 49.00%, log loss 1.021729 on 1,847 matches. Active model unchanged. PSV matches the reported WLWLL; Porto source yields LWWWL versus reported WWWWL, unresolved. 20 tests passed. See `stages/03-build/output/team-form-training-20261019.md` and `upcoming-team-form-20261019.md`.

## March Madness tournament page — 2026-10-19

NCAAB March Madness navigation now resolves to `/college/bracket` on desktop, mobile and the NCAAB subnav. The old generated sample bracket is replaced by the Heritage-styled tournament results and team directory, backed by `/api/v1/ncaab/bracket`. The 2026 snapshot contains 67 real games and 68 teams from ESPN, including First Four through championship; fetch timestamps and stale-refresh notices reflect actual data. See `stages/03-build/output/march-madness-update-20261019.md`.

## Fantasy Sports navigation — 2026-10-19

FPL now has an Edit team dialog with catalog replacements, starter selection, captain/vice-captain controls and account/gameweek-scoped browser persistence. `POST /api/v1/fpl/team/evaluate` reuses optimizer constraints and recalculates totals from cached player data. No official FPL account submission. See `stages/03-build/output/fpl-team-edit-20261019.md`.

FPL Advisor now uses the Heritage visual system throughout: serif headings, shared cards/buttons/footer, a responsive FPL toolkit, summary metrics, position-grouped formation, keyboard-accessible player disclosures and consistent data states. Details: `stages/03-build/output/fpl-ui-refresh-20261019.md`.

The shared navbar links Fantasy Sports → Fantasy Premier League to the existing protected `/fpl-advisor` route on desktop and mobile. The FPL page uses the Fantasy Premier League title, a responsive header and higher-contrast selected tabs. See `stages/03-build/output/fantasy-navigation-20261019.md` for verification.

## Scrapling odds for 18 October — collected 2026-10-17

46-source public run captured 1,545 complete football 1X2 snapshots; 900 within 18 October Kampala time (892 Bovada, four betPawa, four SportPesa). Twelve quotes matched four stored EPL fixtures and were price-verified in the DB; duplicate-safe repeat inserted zero. Other captured fixtures remain in the dated export. See `stages/03-build/output/scrapling-tomorrow-20261018.md` and companion JSON for source limitations, collection time and verification.

## Football name matching repaired — 2026-10-17

Reviewed Brighton/Sunderland/Hull variants now resolve to existing candidate feature keys and share official-result identity without changing global training normalization. All eight rejected inputs now forecast; all 22 successful forecasts reproduce; live API accepts all three names. Artifacts and immutable trials unchanged. 36 Python tests passed, one DB test skipped. Existing excluded-fixture retry remains separate. Evidence: `stages/03-build/output/football-alias-fix-20261017.md`.

## Paper-trial logic audit — 2026-10-17

Read-only recomputation: 30 automatic fixtures, 22 forecasts, eight false missing-history exclusions, 12 selections (six settled/six pending); no EV-rule decision mismatches. Missing Brighton/Sunderland/Hull aliases and unconditional seen-fixture locking prevent retries. Newcastle manual pick settled as a loss separately and correctly does not enter the frozen-model denominator. Collector currently healthy. Findings and evidence: `stages/03-build/output/paper-trial-logic-audit-20261017.md`. No trial policy or immutable record changed.

## Model Lab team search — 2026-10-17

Candidate previews now use searchable home/away dropdowns sourced from saved candidate history through read-only `/api/v1/sport-models/teams`. The newest candidate is selected automatically and typing remains available while suggestions load or fail. Teams are scoped to the selected candidate and training league; changing candidates clears both fields. Supports keyboard selection, duplicate prevention and retry. Details: `stages/03-build/output/model-lab-team-search-20261017.md`.

## BALLDONTLIE source check — 2026-10-16

Supplied key verified against NFL games; collected all 285 regular/postseason 2025 games and independently matched all results to nflverse, with zero conflicts/unmatched games. NFL odds/opening odds and NCAAF games/odds/opening odds returned 401. Provider docs require sport-specific GOAT odds access; opening snapshots document `opened_at` but were inaccessible with this key. No duplicate training data added and no model retrained. CSV/JSON capture and details: `stages/03-build/output/balldontlie-check-20261016.md`. Credential remains local/ignored, separate from the public placeholder.

## NFL/CFBD sources and models — 2026-10-15

Added resumable `etl.fetch_gridiron_sources`, native-ID adapters, causal nflfastR efficiency features, and `models.train_gridiron_sources`. Collected 32 checksummed sources: nflverse schedule, 2023–2025 nflfastR PBP, and 2013–2026 authenticated CFBD games/lines (28 API calls). Validated 7,096 NFL games/5,374 moneyline pairs and 11,668 FBS-participant college games/4,313 pairs. History candidate `20261015T194812812329Z` has NFL 64.56% and college 74.52% accuracy on chronological tests, verified through the live preview API. Archive-odds research models reached 68.00%/77.15% full-test accuracy but did not improve log loss over covered market baselines; quote times remain unverified. An additional recent-season nflfastR EPA/success-rate research model reached 61.67% on 120 test games. All five models reloaded with reproduced metrics; 29 tests passed. PFR returned 403 and was not harvested; its IDs are cross-references only. All models inactive. Details and exports: `stages/03-build/output/gridiron-models-20261015.md`.

## NBA archive research models — 2026-10-15

Free NBA moneylines acquired with Scrapling from Guy Dotan's public UCLA thesis data: 16,492 validated games from 2007–2020, with 16,491 complete price pairs. Isolated history and odds experts trained under `pipeline/models/model_store/research/nba_archive/20261015T165801405910Z/`. Same-test accuracy: 65.68% history, 67.59% odds-aware, 67.33% vig-free archive baseline. Quote timestamps and opening/closing basis are undocumented, so this is research-only, outside the candidate catalog; strict quote matching and active models are unchanged. Evidence: `stages/03-build/output/nba-free-odds-20261015.md` and `nba-archive-training-20261015.json`. The newer NBA-only history candidate is `20261015T163645187197Z` (8,114 games; 64.37% on a different test period). Odds API historical collection remains blocked by the configured free plan with zero remaining credits.

## Admin workspace refresh — 2026-10-15

All admin routes share the operations visual system. The sidebar links to sportsbook comparisons, probability/EV fixtures, and paper trials. Users/events/statistics/revenue/audit use authenticated Rust APIs; preferences are browser-local; SportsGPT uses `/ai-picks/chat`. Demo user mutations, metrics, logs, and chatbot replies were removed. Admin bet routes remain disabled and the page reports that limitation. Backend fixes cover analytics alignment/net revenue, bound user filters/filtered counts, and event pagination. Event editing preserves local kickoff time. Evidence: `stages/03-build/output/admin-pages-update-20261015.md`.

Generated: 2026-07-06 (previous: 2026-05-29)

## Overview

A comprehensive full-stack sports betting platform with AI-powered betting advice, real-time odds, responsible gambling features, ML-driven matchup predictions, and a RAG-enhanced chatbot assistant. An ICM (Iterative Context Management, Jake Van Clief) workspace layer sits at the root (`AGENTS.md`, `CONTEXT.md`, `stages/`, `_config/`, `shared/`, `setup/`) on top of the four service directories.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Rust (Actix-web 4.4, Tokio, SQLx 0.7, rustls, Argon2, AES-256-GCM) |
| **Frontend** | React 19.1, Vite 7, TailwindCSS 4, Zustand 5, TanStack Query 5, Zod 4, React Router 7 |
| **ML Pipeline** | Python 3, FastAPI, SQLAlchemy, XGBoost/LightGBM stacking ensemble, PostgreSQL |
| **Chatbot** | Node.js/Express, Genkit + Google Gemini, ioredis, pg (RAG over pgvector) |
| **Database** | PostgreSQL 14+ (2 databases: football_betting + football_heritage) |

## Project Structure & Size

```
FootballHeritage/
├── AGENTS.md, CONTEXT.md      # ICM L0/L1 — workspace identity, routing, load tables
├── _config/                   # ICM L3 — brand, conventions, tech-stack, glossary
├── stages/00..05/             # ICM pipeline — intake → discovery → architecture → build → test → deploy
├── setup/                     # Onboarding questionnaire
├── shared/                    # Cross-stage reference (this index, domain-notes, prompt-history)
├── backend/                   # Rust API server — 39 .rs files, ~8.9K lines
│   ├── src/handlers/          # auth, betting, wallet, sports, parlay, player_props,
│   │   └── admin/             # users, events, bets, analytics, monitoring
│   ├── src/middleware/        # jwt_auth, admin_auth, rate_limit, security_headers, monitoring
│   ├── src/bin/               # init_admin, init_wallets, reset_wallets
│   └── migrations/            # SQLx migrations (auto-run re-enabled 2026-07-06)
├── frontend/                  # React SPA — 28 pages, ~30 components, 6 hooks, 4 Zustand stores (~16K lines)
├── pipeline/                  # Python ML pipeline (~16K+ lines)
│   ├── etl/                   # 31 modules (fetch/ingest/transform/load, elo, devig, backtesting)
│   ├── models/                # train_model_v2/predict_v2 (calibrated stacking ensemble), evaluate
│   ├── api/                   # FastAPI — routes.py aggregates api/routers/* domain modules
├── chatbot/                   # Express + Genkit RAG service (JWT-validated, Redis-cached)
└── scripts/                   # DB backup/restore utilities
```

## Data Flow

**Odds Ingestion:** The Odds API → fetch_raw_data → ingest_oddsapi_offers → match_oddsapi_events → compute_intelligence(_v2) → devigged_odds/ev_bets/arbitrage

**ML Predictions:** fetch_raw_data → transform (Parquet) → load_to_db → train_model_v2 (calibrated stacking ensemble, val 56.8%) → predict_v2 → sync_to_backend. Scheduled via run_daily_fetch_with_sync.bat / run_weekly_retrain.bat (Windows Task Scheduler).

**Chatbot:** Frontend → Rust backend (JWT proxy) → Node.js chatbot → intent routing → Redis cache → PostgreSQL hybrid retrieval → Gemini → response. Note: `pipeline/api/routes.py` also contains a separate hand-rolled `/smart-assistant` intent router that overlaps with this.

## Security

- AES-256-GCM wallet encryption; Argon2 password hashing + zxcvbn strength check
- JWT auth (shared secret across Rust/Node services); account lockout; age verification (21+)
- Rate limiting (governor: global IP, per-user betting/login); security headers middleware
- RBAC user/admin/superadmin — enforced server-side AND frontend AdminRoute gates /admin by role (2026-07-06)
- Frontend token in sessionStorage; idle logout driven by VITE_SESSION_TIMEOUT (default 15 min)

## Known Issues (verified 2026-07-06)

- Live admin operations dashboard (2026-10-15): `/admin/dashboard` now reads real collection, sportsbook, forecast/EV, and paper-study evidence instead of demo users/revenue/alerts. Added read-only `/api/v1/prediction-dashboard/operations` with complete-fixture coverage, latest fresh valid prices, active-model coverage, and sanitized capture/collector summaries. Admin route guards remain. Supports source search/filtering, refresh/retry, snapshot export, responsive layout, and direct prediction-tab links. Verified by 13 Python checks, 12 Chromium checks, production build, and direct browser requests at `http://localhost:5173/admin/dashboard`. See `stages/03-build/output/admin-operations-update-20261015.md` and live evidence JSON/PNGs.

- Paper-trial refresh repair (2026-10-15): upcoming-only fixture batches inferred SQL TEXT for all-null scores, causing collector failures. Loader staging tables now receive explicit nullable integer score types. Continuation records fresh frozen-policy forecasts throughout the existing 14-day fixture window instead of only the current day; date-specific capture files prevent collisions. Future fixtures remain pending without result-provider calls. Live collector succeeded and API/UI verification showed 10 batches, 14 pending forecasts (six selected paper picks), and seven preserved settled selections. See `stages/03-build/output/paper-trials-update-20261015.md` and companion JSON.

- Probability/EV refresh (2026-10-15): appended 28 active-model forecasts using averaged fresh database quotes, preserving prior prediction rows and model artifact hashes. Verified all 84 home/draw/away EV comparisons and their visibility through the live dashboard API. Ten fixtures lacked fresh quotes and were left unchanged. CSV/JSON evidence: `stages/03-build/output/probability-ev-outcomes-20261015.*`. Fourteen existing dashboard/AI-picks tests, including rollback-only PostgreSQL cases, passed. Positive estimated EV remains a model estimate, not a settled return or demonstrated profitable edge.

- Scrapling collection (2026-10-15): optional `--transport scrapling` uses an isolated `pipeline/.venv-scrapling` runtime and the existing verified sportsbook parsers, including metadata discovery and pagination. Crawl-policy checks precede public requests. A live run covered the 46 configured sources, collected 1,190 snapshots from seven books, inserted and price-verified 84 quotes across 28 fixtures, imported 60 EPL observations, and synced 1,733 matches to the backend with zero errors. Dashboard HTTP verification passed; unsupported or restricted sources remain explicit. See `stages/03-build/output/scrapling-update-20261015.md` and its JSON evidence.

- Pipeline JSON recovery (2026-10-15): collector health and one sportsbook import (manifest and Parquet) were entirely zero-filled. Preserved all three in `pipeline/data/processed/_quarantine/`; no matching raw source survived, so the damaged import is explicitly excluded. Verified 247 remaining import checksums. Optional health no longer blocks settlement; manifests remain strict, and JSON publication now uses flushed/fsynced temporary files and atomic replacement. Fetch jobs report provider failures instead of false success, and structured logs redact URL credentials. Regional refresh and training preflight passed; details in `stages/03-build/output/pipeline-json-recovery-20261015.md`.

- Bookmaker network inspection (2026-10-14): inspected all 47 resolved operator URLs and recorded the seven unresolved entries. Browser network requests identified Betika Uganda's paginated soccer feed and Fortebet's current GET prematch endpoint. Both are now collected and linked to the dashboard: four bookmakers provide 36 fresh quotes across nine Champions League fixtures. Verified by 44 focused Python and four Chromium checks, duplicate-safe live ingestion and cookie-free curl replays. The remaining operator/endpoint results are in `stages/03-build/output/bookmaker-network-discovery-20261014.json`; curl examples and limitations are in its companion Markdown report.

- Bookmaker grid coverage (2026-10-13): `_config/bookmakers.json` is the canonical 54-source inventory. Dashboard columns persist across pages/competition filters. betPawa's collector now includes Champions League; exact competition/team/kickoff ingestion links CL snapshots from betPawa and Bovada. Live verification: 18 quotes across nine CL fixtures; 38 Python and four Chromium checks passed. Other sources need adapters or access/source repairs; the configured odds provider is out of usage credits. See `stages/03-build/output/bookmaker-grid-coverage-20261013.md` and its per-source JSON audit.

- Backend warning cleanup (2026-10-13): unused imports/request type removed, withdrawal metrics recorded after commit, event date and eight odds fields now persisted by admin updates, reserved superadmin middleware explicitly allowed, and unconditional Windows `/LTCG` removed. Verified by offline check, 32 existing tests, and a PostgreSQL temporary-table handler regression. SQLx 0.7.4 future-compatibility notice remains. See `stages/03-build/output/backend-warning-fixes-20261013.md`.

- ~~No CI~~ — .github/workflows/ci.yml added 2026-07-06 (cargo check+test, eslint+build, chatbot/pipeline syntax)
- **No Docker/compose** — 5-service + 2-DB stack must be started manually
- **frontend/.env is committed** (URLs/flags only, no secrets) — port 8888 is correct (matches backend .env.example PORT=8888); older docs referencing 8080 are outdated
- ~~No root .gitignore~~ — added 2026-07-06; ICM layer committed, 237 stale data files untracked
- ~~Migrations disabled~~ — re-enabled 2026-07-06; ad-hoc SQL folded into migrations (incl. transactions.status fix — wallet endpoints depended on it), migrations.disabled/ removed, RAG SQL moved to chatbot/sql/
- **backend/package.json** ("pg" only) — used by backend/scripts/import_betpawa_data.js and import_sample_data.js data-import scripts (not stray; node_modules correctly untracked)
- ~~Versioned-file duplication~~ — v1 train/predict + sync scraper deleted 2026-07-06; compute_intelligence(_v2) both kept intentionally (v2 wraps v1)
- ~~pipeline/api/routes.py monolith~~ — split 2026-07-06 into api/routers/{intelligence,predictions,core,matchup,assistant,parlay,fpl,ncaab}.py + api/db.py + api/odds_math.py; fixed shadowed /predictions/* routes and blocking-sync-in-async endpoints
- Scheduler: Windows Task Scheduler + .bat files is the single supported path (scheduler.py and Airflow DAG deleted 2026-07-06)
- **Uneven test coverage** — frontend coverage updated below; chatbot has no tests; pipeline test_*.py are manual scripts, not a pytest suite; backend has unit tests in 5 modules
- **Doc sprawl** — 18 loose .md status files in pipeline/, 13 .md/.sql at backend root

## Frontend routing update — 2026-10-08

- Public `/` now renders the supplied landing design with a separate Register/Login
  navbar. `/app` preserves the general sports homepage; sport, AI Picks, account,
  betting and administration URLs remain. SPA fallback is required for direct links.
- React 19.2, TypeScript 7 (strict new TS/TSX; legacy JSX remains JS), Vite 7 and
  Tailwind 4 are verified by the frontend build. The existing Zustand/React Query/API
  authentication flow remains; no template identity or hash router is imported.
- Default authentication redirect remains `/dashboard`. Internal `returnTo` and
  protected-route destinations are validated; external/looping paths are rejected.
- Current browser tests include `betting-flow`, `heritage-navigation`, `landing` and
  `template-reference` specs. Test API fixtures are explicitly mocked. Opt-in
  `frontend/scripts/smoke-live-auth.mjs` exercises real local registration/login.
- Final landing integration run: 76 browser checks passed in Chromium/Firefox; strict
  TypeScript/build passed, lint zero errors with one existing admin warning, audit zero
  vulnerabilities. Real local registration/login and validated profile return succeeded.
- Standings/newsroom and synchronized preferences remain unavailable; generation only
  enables Football and still requires statistical/model services. Refer to
  `frontend/UI_INTEGRATION.md` for current frontend contracts and coverage limitations.

## AI Picks generation update — 2026-10-08

- Rust `POST /api/v1/ai-picks/generate` now calls pipeline `GET /api/v1/ai-picks`.
  Development defaults to `http://127.0.0.1:5555/api/v1`; root and legacy `/api`
  configuration values are normalized. Production requires an explicit service URL.
- Pipeline filters upcoming fixtures by competition and UTC date before ranking,
  selects one recent active-model prediction per fixture, and uses recent observed
  bookmaker quotes only. Missing quotes produce model predictions with null odds
  and value metrics. Quote-backed value comparisons rank ahead of predictions.
- Run history preserves requested filters, selections, summary and evidence metadata.
  Generation remains Football-only; Rust RAG chat configuration is independent.
- Verified locally: authenticated POST returned 10 model v2.0.0 predictions; league
  alias/date filters returned 18 Champions League and 6 Premier League fixtures.
  Saved history, validation, authentication and cross-account isolation passed.
  Python 22 tests, Rust URL regression, frontend build/lint and 8 Chromium/Firefox
  browser checks passed. No upcoming fixtures currently have bookmaker quotes.

## Rust RAG chat update — 2026-10-08

- AI Picks chat runs `backend/src/rag.rs` in the Rust API. It retrieves recent
  predictions directly from PostgreSQL via `RAG_DATABASE_URL`, plus knowledge
  documents through full-text search. Gemini generation is called directly from
  Rust; evidence-only replies remain available when generation is disabled or fails.
- `RAG_GEMINI_API_KEY`, `RAG_GEMINI_MODEL`, `RAG_CHAT_MODE`, and `RAG_MODEL_VERSION`
  configure chat. This feature has no chatbot service dependency.
- Conversation turns and source metadata save atomically. User-scoped request IDs
  make concurrent retries idempotent, and server-owned context rejects forged or
  stale client history. Reads/writes check ownership. Rate limit: 12 new turns/minute.
- Verified live: HTTP 200 with Gemini source citations; concurrent retry, follow-up,
  saved evidence, authentication and ownership checks passed. Evidence-only mode
  worked with pipeline HTTP disabled. Rust 23 unit tests, frontend build/lint and
  four single-worker Chromium/Firefox chat checks passed.
- See `stages/03-build/output/rust-rag-chat.md` for verification and current limits.

## Rebuild Checklist (original service setup)


### Prediction model milestone — 2026-10-08

- `pipeline/models/data.py` canonicalizes fixture dates and explicit team identities,
  excludes samples and duplicate normalized source files, validates final-score labels,
  and joins odds by fixture day rather than team names alone. Licensed CSV import:
  `py -3 -m models.import_historical`; new downloads remain pending by user choice.
- `models/features.py` is the v2.1 contract for training, replay, and candidate serving.
  Histories use only completed matches from prior UTC days; windows and defaults match.
  The active v2.0 artifact retains its legacy contract until a candidate is reviewed.
- Training now uses chronological train/tune/calibration/test blocks and temporal
  stacking. Candidates are isolated under `models/model_store/candidates/`, with frozen
  datasets and reproducible evaluation. `models/backtest.py` evaluates the complete
  calibrated ensemble across expanding future periods.
- The matchup route uses the same prediction service as batch inference; repaired
  artifact loading was verified with a real local HTTP 200. Upcoming-fixture SQL and
  read-only candidate inference were verified for all nine current fixtures.
- The daily fetch-and-sync batch now generates active-model predictions before sync.
  The weekly trainer creates candidates instead of overwriting production artifacts.
  CI adds fixture identity, causal features, calibration, and import behavioral tests.
- Initial candidate: 10,107 completed fixtures, held-out accuracy 33.97% / log loss
  1.3215. Only 108/1,260 held-out fixtures have real odds (63.0% accuracy on that subset).
  Candidate remains inactive; these results establish a data-coverage problem rather
  than verified performance improvement. Old random-split accuracy is not comparable.
- All 17 behavioral tests pass. Full 200-tree rolling evaluations also complete:
  overall accuracy 51.54%, 53.88%, and 44.29% across the three future windows; model
  log loss is worse than the matched bookmaker baseline in each window. No activation.
- Runbook: `pipeline/MODEL_IMPROVEMENTS.md`; stage evidence:
  `stages/03-build/output/prediction-model-milestone.md`.

### Odds-aware prediction candidate — 2026-10-08

- The v2.1 trainer now defaults to separate calibrated market/history experts,
  selecting regularized logistic regression or histogram gradient boosting on
  chronological tuning data. `--strategy stacking` preserves the earlier stack.
  History predictions exclude odds inputs; market fitting requires observed odds.
- Candidate `20261008T170059291611Z` shares the previous candidate's frozen dataset.
  Held-out accuracy improved 33.97% → 50.08%, log loss 1.3215 → 1.0086, and Brier
  score 0.7474 → 0.6034. All three rolling windows improved accuracy and log loss.
  These are retrospective historical comparisons, requiring fresh future acceptance.
- No demonstrated bookmaker advantage: odds-backed test log loss 0.91025 versus
  market 0.91010. Active v2.0 and stored predictions remain unchanged. All 28 Python
  behavioral tests passed; saved candidate metrics were reproduced exactly.
  Read-only inference validated probabilities for all 28 current upcoming fixtures.
- Details: `stages/03-build/output/odds-aware-prediction-model.md`.

### Bookmaker evidence demo — 2026-10-08

- `models/market_demo.py` exports a self-contained HTML report, full fixture CSV and
  provenance JSON using the checked frozen evaluation bundle. All 108 odds-backed
  test fixtures are retained; paired fixture-day bootstrap intervals span zero for
  accuracy, log loss and Brier differences. No bookmaker probability edge established.
- Fixed 5% EV flat-stake paper policy: 80 bets, +10.62 units (+13.28% ROI), with
  day-bootstrap ROI interval -38.83% to +72.24%. No real bets or model activation.
- All 33 Python behavioral tests passed. Demo:
  `stages/03-build/output/bookmaker-demo/demo.html`; methods and limits:
  `stages/03-build/output/bookmaker-demo.md`.

Auth-header follow-up: `/login` and `/register` reuse
`frontend/src/landing/LandingNavbar.tsx` without the scoreboard or sports navbar.
Landing styles are scoped to the header wrapper, not the existing auth forms;
account links preserve return URL/state. Application navigation remains on `/app`
and existing sports/protected pages.
Login/registration presentation now reuses typed `landing/AuthForms.tsx` components
and scoped `auth.css`, with existing hooks/schemas/age confirmation unchanged.

### Sportsbook collection — 2026-10-08

- `pipeline/etl/scrape_sportsbooks.py` attempts the 20 requested public targets,
  stores timestamped raw responses and reports denial/failure independently of
  extracted odds. Optional provider fallback uses existing configuration without
  recording credentials. `etl/sportsbook_parsers.py` parses Bovada regulation 1x2.
- Run `20261008T174556306527Z`: 1,706 direct Bovada + 378 provider snapshots,
  2,084 total across 12 books; eight remain uncovered. No database/model changes.
- Methods, source coverage and repeat commands:
  `stages/03-build/output/sportsbook-scrape-20261008.md`.

### Sportsbook training import — 2026-10-08

- `models/import_sportsbook_odds.py` imported 2,084 captured odds observations into
  checksummed processed parquet storage. The shared training/backtest loader now
  reads these files and joins only exact kickoffs with unambiguous team pairs.
- No captured observation matches a completed fixture yet: all 2,084 pending.
  No scores/labels invented and no candidate fitted or activated. Existing 10,107
  completed fixtures remain the supervised training corpus.
- All 41 behavioral tests passed. Details and commands:
  `stages/03-build/output/sportsbook-training-import-20261008.md`.

### Separate sport models — 2026-10-09

- `models/train_sports.py` builds isolated sport candidates. Run
  `20261009T100528981075Z`: football trained on 10,107 completed fixtures; basketball
  on 8,586 games. NBA test accuracy 64.42% (1,082 games); full basketball test
  61.52% versus fixed-prior 54.25%. No usable basketball odds baseline available.
- American football (163), baseball (265), hockey (26) have data adapters and
  feature profiles but remain below the 500-game gate. NCAA basketball is test-only
  transfer evaluation and cannot be previewed as a trained league.
- Sport histories are isolated by league; results wait for availability; one
  conflicting NBA fixture quarantined; provider IDs preserve baseball doubleheaders.
- Candidate catalog and explicit previews: `GET /api/v1/sport-models` and
  `POST /api/v1/sport-models/preview`. No active-model changes. Saved artifacts and
  live API smoke checks passed; 51 behavioral tests passed. Details:
  `stages/03-build/output/sport-models-20261009.md`.

### WNBA and NCAA models — 2026-10-09

- Dedicated `wnba`, `ncaab` and `ncaabw` profiles and candidate weights. Final run
  `20261009T103733107847Z`: 1,631 WNBA, 35,324 NCAA men, 32,757 NCAA women games.
  Held-out accuracy: 70.86%, 71.19%, 74.94%; fixed-prior baselines: 57.91%, 63.56%,
  59.75%. Insufficient historical odds to establish bookmaker advantage.
- Public ESPN WNBA results and SportsDataverse seasonal college releases are
  imported by `etl/fetch_basketball_history.py`. College releases replace capped
  January samples. WNBA All-Star exhibitions excluded; no mixed-gender weights.
- Neutral-court inputs are supported by training and previews. All 59 behavioral
  tests passed; dedicated API previews and saved-model reload verified. No active
  production artifact changes. Details:
  `stages/03-build/output/wnba-ncaa-models-20261009.md`.

### NFL and college football models — 2026-10-09

- Dedicated `nfl` and `ncaaf` models trained in candidate `20261009T144354530070Z`.
  NFL: 2,852 historical games, 406 scored test games, 63.30% accuracy vs 55.91%
  fixed-prior baseline. College: 9,026 FBS-participant games, 1,357 test games,
  75.68% vs 66.84%. Model weights and histories are league-isolated.
- `etl/fetch_americanfootball_history.py` captures ESPN NFL and SportsDataverse
  college seasonal results with checksums; nflverse cross-check found zero missing
  NFL games through 2026-10-06. Preseason/exhibitions are excluded. NFL's ten ties
  update history but do not receive winner labels; previews state probabilities
  conditional on no final tie, for ties-void settlement only.
- Boundary labels are purged before tuning/calibration/test. No bookmaker advantage
  established: market outperformed NFL on 63 matched test games; college has no
  exact timestamped odds joins. Both currently use their history expert.
- All 68 behavioral tests passed; saved metrics reproduced; NFL/college live
  previews returned 200 and invalid league/team requests 422. Candidates remain
  inactive. Results and commands:
  `stages/03-build/output/nfl-college-football-models-20261009.md`.

### Cross-sport bookmaker comparisons — 2026-10-09

- `models/sport_market_demo.py` compared saved NBA, WNBA, NCAA men/women, NFL,
  college football and soccer candidates. No bookmaker advantage established.
  Matched model/market accuracy: NBA 85.71%/100% (14 games), NCAA men 80%/70%
  (10), NFL 58.73%/60.32% (63), college football 78.82%/86.47% (170), soccer
  60.19%/59.26% (108). No WNBA/NCAA women stored quotes; basketball samples small.
- Two-way model histories stop at conservative quote-time bounds. Exact ESPN ID
  aliases resolve college names; identical bookmaker event IDs resolve NBA tip-off
  minute changes. Same-capture per-book probabilities form the consensus; actual
  individual book prices settle the fixed 5% EV flat-unit paper policy.
- Paper ROI: NBA -82.91%, NCAA men -10.25%, NFL -3.07%, college -53.10%, soccer
  +13.28%. Soccer's ROI interval spans losses and its historical odds have no
  precise observation time. No production model or real-money changes.
- All 74 behavioral tests passed. Independent exported-ledger verification
  reproduced scoring/profits and checked actual quotes and source checksums.
  Final dashboard: `stages/03-build/output/bookmaker-comparisons-20261009-final/index.html`.
  Methods: `stages/03-build/output/bookmaker-comparisons-20261009.md`.

### Predictions page baseline data audit — 2026-10-09

- `/predictions` uses the pipeline directly; `/ai-picks` separately uses the Rust
  backend. New sport candidates are not automatically used by either route.
- Live audit: all 30 fetched fixtures had active v2.0.0 predictions but no odds.
  Pipeline odds are decimal; the Predictions frontend incorrectly applies
  American odds math. Soccer fixture cards omit draw probabilities.
- API's 30-day 30.69% accuracy (404 rows) includes 380 unknown kickoff dates;
  only 24 rows are confirmed pre-kickoff. Do not treat this as verified forward
  performance. History correctness filters run after pagination and leave totals
  unfiltered. Stored quote timestamps were null.
- Review and proposed contract: `stages/03-build/output/predictions-page-data-review-20261009.md`.
  Read-only reproducer: `pipeline/scripts/audit_predictions_page.py`.
  These observations preceded the dashboard implementation below. The original
  live-audit JSON was refreshed during implementation; the written baseline
  review preserves the initial findings.

### Predictions dashboard implementation — 2026-10-09

- `/predictions` now uses `/api/v1/prediction-dashboard/fixtures`: server-side
  upcoming filters, nearest-kickoff order, pagination, active model provenance,
  all three soccer outcomes and actual latest-per-book decimal quotes.
- Estimated unit EV requires fresh predictions and complete quotes observed
  within 24h. Time-unknown/stale prices remain unavailable. Consensus removes
  margin per bookmaker and averages books separately from best actual prices.
- History and accuracy share one latest valid pre-kickoff prediction per fixture.
  Filters/counts precede history pagination, end dates include the entire day,
  null kickoff dates are excluded and disclosed, and empty accuracy is null.
  Live 30-day sample: 24 fixtures, 10 correct, 41.67%; 380 undated rows excluded.
- Model lab previews actual saved soccer/NBA/WNBA/NCAA men/women/NFL/college
  candidates, with explicit outcome and settlement rules. None are promoted.
- 15 live API checks and 83 Python behavioral tests passed; feature browser checks
  cover real API data plus explicit mocked quote/error/mobile cases. Database
  integration tests are opt-in and use rollback-only temporary tables.
- Final UI checks: six feature and 18 navigation Chromium cases passed;
  lint/typecheck/build passed; Fallow 3.32 audit introduced no findings. Source
  input provenance and bookmaker baseline/calibration remain unavailable; the
  page explicitly identifies those limitations rather than fabricating evidence.
- Implementation/verification: `stages/03-build/output/predictions-ui-update-20261009.md`.
  Current live API snapshot: `stages/03-build/output/predictions-ui-live-verification-20261009.json`.

### Prospective profitable-edge assessment — 2026-10-10

- Independently reproduced all five populated bookmaker comparison ledgers; no
  candidate or production model has established a profitable edge. Soccer's
  +13.28% historical paper ROI has a 95% interval spanning losses and untimestamped
  historical quotes. Two other leagues have no matched bookmaker evidence.
- `pipeline/scripts/record_edge_trial.py` records frozen candidate forecasts from
  validated public snapshots, rejects stale/started or training/history-after-quote
  inputs, retains SHA-256 provenance, and computes ordinary/stressed estimated EV.
- First EPL trial: five forecasts before kickoff, four paper selections, one
  missing-history exclusion. Candidate remains inactive. No results/profit yet.
  `stages/03-build/output/epl-edge-trial-20261010.json` preserves forecasts;
  `profitable-edge-assessment-20261010.md` declares a fixed prospective study.
- Full Python discovery: 86 tests run, 81 passed, five opt-in database checks
  skipped. Existing model-versus-bookmaker verifier passed all populated ledgers.
  No training, application data changes, deployment, or bets occurred.

### Additional regional bookmakers — 2026-10-10

- Inventory now retains 54 unique brands: original 20 plus all 34 new requests.
  Regional source URLs and unresolved domains are explicit; provider keys are not
  assumed. The collector supports inventory URLs and reports unresolved sources.
- Public-source probe: 21 pages needing adapters, three access denials, three
  connection failures, seven unresolved sources. Zero normalized new-source odds;
  HTML captures are not training data. No active models or trial policies changed.
- Seven targeted collector tests passed; Fallow before/after audits passed without
  introduced findings. Evidence: `stages/03-build/output/african-bookmaker-check-20261010.md`.

### Verified regional adapters and trial settlement — 2026-10-10

- Three Uganda sources now normalize complete prematch 1X2 prices: betPawa
  (upcoming EPL), Fortebet (football full offer), AbaBet (selected-day EPL).
  SportPesa UG links to a global offering; no Uganda prices have been verified.
- UTC loader/session handling fixes the three-hour kickoff cast. Fifteen bounded,
  source-verified EPL fixtures were corrected; replay inserts no duplicate odds.
  Reviewed lookup aliases preserve raw names and frozen model feature keys.
- Latest exercised capture has 61 EPL snapshots from four books; 38 exact joins
  and five fresh active v2.0.0 predictions. All five upcoming EPL API fixtures have
  Bovada plus the three UG books. New odds still need final results for labels.
- Daily batch runners now call `scripts.refresh_regional_pipeline`: collect,
  exact sync/import, append fresh predictions with artifact/quote provenance,
  continue the frozen Bovada policy for new fixtures and refresh pending trial
  results across prior dates. No new scheduler task or model promotion occurred.
- Immutable trial SHA checks, exact regulation-time result joins and separate
  settlement receipts power the new Predictions **Paper trials** tab. Original
  five forecasts remain pending; ROI is null and no profitable edge is established.
- All 103 Python tests, seven Chromium feature checks and lint/typecheck/build pass. Fallow 3.32 reports
  zero introduced findings. Python/PostgreSQL safeguards include a real non-UTC
  loader regression and prior-date result refresh with provider-failure recovery.
- Details: `stages/03-build/output/regional-pipeline-update-20261010.md`;
  live evidence: `regional-pipeline-live-verification-20261010.json`.

### SportPesa global feed retry — 2026-10-10

- User-supplied global football page exposes anonymous prematch JSON through its
  published client. Adapter validates football market 10 (standard 1X2), preserves
  GLOBAL region, handles HTTP 206 and retains Content-Range metadata.
- Live capture at 13:50 UTC supplied 19 EPL SportPesa snapshots; 12 exact database
  joins. Combined cycle: 76 EPL snapshots, 46 joins, five fresh predictions.
  All five upcoming EPL fixtures have five bookmaker sources in the real API.
- No active weights or frozen trial policy changed. Official result refresh now
  has one losing paper selection and four pending forecasts; no established edge.
- All 105 Python tests passed, including new SportPesa market/identity/time guards.
  Evidence: `stages/03-build/output/sportpesa-adapter-20261010.md`.

### Weekly runner data reuse — 2026-10-10

- `run_weekly_retrain.bat` now runs training and prediction generation only;
  duplicate fetch/transform/load steps were removed. Run daily ingestion first.
- Training consumes existing processed snapshots, local histories and imported
  odds; candidate saving and active-model prediction behavior are preserved.
- Details: `stages/03-build/output/weekly-retrain-data-reuse-20261010.md`.

### Completed-game prospective evidence — 2026-10-10

- Refreshed official EPL results and settled all five eligible frozen candidate
  forecasts separately from their immutable source. Candidate v2.1.0 winner
  accuracy: 2/5 (40%). Four fixed-policy paper selections lost 0.5 units on four
  units staked: ROI -12.5%, stressed ROI -14.25%. United was skipped by that policy;
  Sunderland lacked candidate training history. No profitable edge established.
- Read-only database audit found six dated football fixtures today, each with a
  valid active v2.0.0 pregame forecast. Exact official provider ID/team/UTC kickoff
  joins verified all six final results: 3/6 winners correct (50%). Five latest
  forecasts have regional audit provenance; Arsenal's older forecast does not.
  Latest pregame forecasts do not prove which forecast appeared at bet placement.
- Candidate log loss/Brier 1.0140/0.6163 versus frozen Bovada baseline
  0.9803/0.5814 on the same five games. Today's evidence does not support candidate
  superiority. Active six-game metrics are a different cohort and cannot be
  directly ranked against those five-game rows.
- Official account-wide matches endpoint returned an empty TIER_ONE scope; the
  PL endpoint supplied all six finals. No claim of worldwide result coverage.
  No active model, application match rows, weights, or trial thresholds changed.
  Captures/hashes, forecasts, settlements, independent arithmetic checks and
  coverage limits: `stages/03-build/output/today-prediction-evidence-20261010.md`.
  Formal frozen trial progress: four settled selections across one fixture day.

### Frozen trial automation and assessment — 2026-10-10

- Installed `FootballHeritage-PaperTrial-Collection`: windowless Python every
  15 minutes under the current interactive user. Keep the computer awake and
  signed in with PostgreSQL available. Task-launched run verified result 0.
- `scripts.run_trial_collection` prevents overlap, refreshes bounded official EPL
  fixtures once per UTC day, collects quotes/forecasts, settles prior pending
  results and attempts formal assessment. Logs/status expose failures. Unrelated
  provider ingestion and weekly retraining are not part of this scheduled job.
- Paper trials API/UI aggregate batches by frozen artifact manifest/policy/book,
  deduplicate fixtures and show progress against 200 selections/60 UTC days.
  Current progress remains 4/200 and 1/60, with ROI -12.5% and no formal interval.
- First complete chronological qualifying cohort is frozen before one seeded
  10,000-resample day-bootstrap assessment. Earlier pending selections block it;
  saved official result captures must reproduce the scores and hashes. Calibration,
  paired market metrics and drawdown are reported. A failed decision is not
  repeatedly retested on later batches. Executable profitability stays unverified.
- Full enabled-database suite: 118 passed; subsequent provenance/retry regressions
  passed targeted checks. Nine Chromium feature checks, lint/typecheck/build,
  real API verification and Fallow audit passed (zero introduced findings).
  Runbook and limitations: `stages/03-build/output/trial-automation-20261010.md`.

### Manual paper selection workflow — 2026-10-12

- `scripts.record_manual_paper_pick` records user-selected one-unit prematch
  choices using fresh complete quotes and captures the active forecast as context.
  Repeated choices are idempotent; existing outcomes cannot be overwritten.
- Manual policies/studies remain separate from frozen model trials and are
  labeled in Predictions **Paper trials**. The existing collector settles them;
  frozen continuation excludes manual entries from its already-seen fixture set.
- User's Newcastle away-win pick versus Coventry was saved at 18:50 UTC, before
  19:00 kickoff, at AbaBet UG 2.05. The original model-policy skip remains intact.
- Evidence: `stages/03-build/output/manual-paper-pick-20261012.md`.

### Bookmaker comparison grid — 2026-10-11

- Predictions **Bookmaker grid** uses the existing fixture feed with 20 rows
  per page. FootballHeritage appears first, followed by available bookmaker
  sources. Each group has home/draw/away cells.
- Selector switches margin-removed outcome probabilities and per-book estimated
  EV at actual decimal prices. FootballHeritage remains the labeled probability
  baseline. Missing/stale markets and stale-model EV are unavailable.
- `market.quotes[].fair_probabilities` exposes the API's existing within-book
  normalization. The cream/green/gold grid supports mobile scrolling.
- Implementation and evidence:
  `stages/03-build/output/bookmaker-grid-20261011.md`.

1. Install prerequisites: Rust 1.70+, Node.js 18+, PostgreSQL 14+, Redis 7+, Python 3.10+
2. Configure `.env` files in backend/, frontend/, pipeline/, chatbot/
3. Start backend — sqlx::migrate! runs automatically; install all deps, start services
4. Initialize RAG embeddings via chatbot/sync-embeddings.js
5. Schedule run_daily_fetch_with_sync.bat (daily) + run_weekly_retrain.bat (weekly) in Windows Task Scheduler

## Supplied bookmaker feeds — 2026-10-14

- AbaBet restored by explicit user instruction after the removal. Current catalog:
  46. Its verified selected-day collector now accepts EPL and UEFA Champions
  League, with Como Calcio mapped to Como 1907. Live page confirms LASK kickoff
  19:45 Africa/Kampala, versus the pasted 9:45. Nine quotes matched and imported,
  zero on repeat. Live API: ten sources with nine fresh quotes each. Evidence:
  `stages/03-build/output/ababet-restored-20261014.md` and `.json`.
- User preference: use Browserbase for future website navigation/data discovery
  when available. No Browserbase tools are exposed in this session; recorded in
  `shared/WORKFLOW.md`.

- BookMaker's public Champions League HTML page is now a verified scheduled
  collector. Nine valid full-game moneylines matched/imported; repeat inserted
  zero. Cached page update time is preserved, and reversed team order carries
  prices with the named teams. Live API: nine sources with nine fresh quotes each;
  inventory remains 45. Evidence: `stages/03-build/output/bookmaker-feed-20261014.md`.

- Bet365's supplied `gamingservices/.../getallgamesv2` request returned HTTP 200
  anonymously but is a casino game catalog, not a sports odds feed. No import or
  inventory change. Evidence: `stages/03-build/output/bet365-supplied-request-20261014.md`.

- Subsequent user-requested removal: AbaBet, AdmiralBet, BetMGM, BetLion, BetKing,
  Bally Bet, Bangbet, Bet.co.za ZA, Bet9ja NG and BetRivers. Current inventory: 45.
  The grid treats the catalog as authoritative so historical quotes cannot restore
  removed columns. AbaBet was removed from regional refresh targets. Evidence:
  `stages/03-build/output/bookmaker-removals-20261014.md`.

- Cloudbet, 1xBet, 22Bet UG and BetOnline anonymous Champions League collectors
  are integrated into the regional refresh and bookmaker grid. Inventory: 55.
- Nine full-match quotes per source match reviewed teams at exact UTC kickoff.
  Live API verification and idempotency are recorded in the linked artifact.
- BetOnline uses UTC-offset zero, excludes alternate child markets and aligns
  named-team prices when the source line order differs from the fixture order.
- Caesars returned 403 anonymously and 202 WAF HTML with the supplied token;
  no odds are attributed to it. Session secrets are not stored in code.
- Evidence: `stages/03-build/output/supplied-bookmaker-feeds-20261014.md` and `.json`.

## Pegasus worker and sync — 2026-10-13

- Pegasus runs a Premier League collection/transform/load/backup job at 06:00 Africa/Kampala via systemd; 20 unique matches and a readable backup were verified in the user-provided journal.
- Windows scripts/sync_pegasus.ps1 and pipeline/sync_to_backend.py support SSH-forwarded source credentials, read-only previews, stable external event identity, preserved missing odds, and atomic batch failure. Six regression checks (including isolated PostgreSQL schemas) passed; a local three-fixture preview passed.
- Actual Pegasus transport/application and Windows scheduling remain pending SSH authentication. See pipeline/docs/PEGASUS_SYNC.md and stages/03-build/output/pegasus-sync-20261013.md. Existing Windows/pipeline work was preserved.
- Follow-up verified: actual Pegasus SSH transport and 20-fixture apply passed; source fields, all 20 event UUIDs and moneyline pairs matched, with 4,189 backend events and updates-only repeat preview. A dedicated Windows SSH key and scripts/install_pegasus_sync.ps1 were prepared. Public-key installation and task registration remain pending.
- Automation verified: the key is installed and FootballHeritagePegasusSync runs at sign-in and every 30 minutes while the Windows user is signed in. First scheduled sync processed 20 fixtures with LastTaskResult=0; task returned to Ready. An independent key tunnel also passed and closed automatically. See stages/03-build/output/pegasus-sync-schedule-20261013.json. This supersedes the earlier pending-authentication notes above.
- Schedule changed at the user's request on 2026-10-13: Pegasus collection now runs at 08:00 Africa/Kampala; the timer shows next run 2026-10-14 08:00 EAT. Windows sync remains every 30 minutes while signed in.

## User dashboard UI - 2026-10-22

`/dashboard` now uses isolated Heritage styles in `frontend/src/pages/Dashboard.css`, account/open/settled metrics, sorted filterable activity, canonical feature links and reactive browser-session budget progress. Loading, empty, retry and unavailable-data states are explicit; win rate excludes pending/void outcomes. Existing API hooks and route protection retained. Build and scoped lint passed; 12 Chromium/Firefox browser checks passed at desktop/tablet/mobile widths. Fallow remains failing, including estimated-uncovered dashboard complexity findings. No deployment or backend changes. See `stages/03-build/output/user-dashboard-ui-20261022.md`.


## Production feature management ? 2026-10-23

Added audited global/emergency/user/role feature controls, maintenance restrictions, current-role admin authorization, last-superadmin protection, admin UI and frontend gates. Python requests now use a private token-authenticated Rust gateway; hosted database URLs and production templates/CI/runbooks are provided. Verified 26 Rust tests (three ignored), 269 Python tests (14 skips), frontend production build/lint/typecheck, 38 selected Chromium checks, six expanded cross-browser feature checks and real isolated API/CORS/funding-denial smoke tests. Full migration chain passed on temporary PostgreSQL. Docker image and hosted deployment remain unverified after daemon failure; no production release occurred. See `docs/PRODUCTION_AUDIT.md`, `docs/VERCEL_DEPLOYMENT.md`, `docs/FEATURE_MANAGEMENT.md`, `docs/PRODUCTION_CHECKLIST.md` and `stages/04-test/output/production-readiness-20261023.md`. Existing uncommitted feature work remains separate and must be included in a reviewed release checkout.
