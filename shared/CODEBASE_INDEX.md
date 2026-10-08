# Football Heritage - Codebase Index

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

## Rebuild Checklist (original service setup)

Auth-header follow-up: `/login` and `/register` reuse
`frontend/src/landing/LandingNavbar.tsx` without the scoreboard or sports navbar.
Landing styles are scoped to the header wrapper, not the existing auth forms;
account links preserve return URL/state. Application navigation remains on `/app`
and existing sports/protected pages.
Login/registration presentation now reuses typed `landing/AuthForms.tsx` components
and scoped `auth.css`, with existing hooks/schemas/age confirmation unchanged.

1. Install prerequisites: Rust 1.70+, Node.js 18+, PostgreSQL 14+, Redis 7+, Python 3.10+
2. Configure `.env` files in backend/, frontend/, pipeline/, chatbot/
3. Start backend — sqlx::migrate! runs automatically; install all deps, start services
4. Initialize RAG embeddings via chatbot/sync-embeddings.js
5. Schedule run_daily_fetch_with_sync.bat (daily) + run_weekly_retrain.bat (weekly) in Windows Task Scheduler
