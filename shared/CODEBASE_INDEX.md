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
│   └── migrations/            # SQLx migrations (auto-run DISABLED in main.rs)
├── frontend/                  # React SPA — 28 pages, ~30 components, 6 hooks, 4 Zustand stores (~16K lines)
├── pipeline/                  # Python ML pipeline (~16K+ lines)
│   ├── etl/                   # 31 modules (fetch/ingest/transform/load, elo, devig, backtesting)
│   ├── models/                # train/predict v1 + v2, evaluate
│   ├── api/                   # FastAPI — routes.py is a 3,502-line monolith
│   └── dags/                  # Airflow DAG (one of 4 competing schedulers)
├── chatbot/                   # Express + Genkit RAG service (JWT-validated, Redis-cached)
└── scripts/                   # DB backup/restore utilities
```

## Data Flow

**Odds Ingestion:** The Odds API → fetch_raw_data → ingest_oddsapi_offers → match_oddsapi_events → compute_intelligence(_v2) → devigged_odds/ev_bets/arbitrage

**ML Predictions:** fetch_raw_data → transform (Parquet) → load_to_db → train_model(_v2) (stacking ensemble) → predict(_v2) → sync_to_backend

**Chatbot:** Frontend → Rust backend (JWT proxy) → Node.js chatbot → intent routing → Redis cache → PostgreSQL hybrid retrieval → Gemini → response. Note: `pipeline/api/routes.py` also contains a separate hand-rolled `/smart-assistant` intent router that overlaps with this.

## Security

- AES-256-GCM wallet encryption; Argon2 password hashing + zxcvbn strength check
- JWT auth (shared secret across Rust/Node services); account lockout; age verification (21+)
- Rate limiting (governor: global IP, per-user betting/login); security headers middleware
- RBAC user/admin/superadmin — enforced server-side only; frontend `/admin` routes check auth but NOT role
- Frontend token in sessionStorage; 15-min client-side idle logout (hardcoded, ignores VITE_SESSION_TIMEOUT)

## Known Issues (verified 2026-07-06)

- **No CI** — no .github/workflows; nothing gates build/lint/test
- **No Docker/compose** — 5-service + 2-DB stack must be started manually
- **frontend/.env is committed** (URLs/flags only, no secrets) — port 8888 is correct (matches backend .env.example PORT=8888); older docs referencing 8080 are outdated
- **No root .gitignore** — root `target/`, `backups/`, `.vscode/`, pipeline data JSONs untracked/uncommitted clutter; ICM files themselves not yet committed
- **Migrations disabled** in backend main.rs; ad-hoc fix SQL files at backend root (fix_migrations.sql, reset_migrations.sql, update_admin_role.sql, …) and a migrations.disabled/ folder
- **backend/package.json** ("pg" only) — used by backend/scripts/import_betpawa_data.js and import_sample_data.js data-import scripts (not stray; node_modules correctly untracked)
- **Versioned-file duplication** — compute_intelligence/_v2, train_model/_v2, predict/_v2, fetch_basketball_reference/_async all coexist; scheduler.py imports both v1 and v2
- **pipeline/api/routes.py = 3,502 lines** — all routers, Pydantic models, odds math, and an intent-detection assistant in one file
- **4 competing schedulers** — scheduler.py, Airflow DAG, .bat files, Windows Task Scheduler docs
- **Thin test coverage** — one Playwright E2E spec (API-mocked); chatbot has no tests; pipeline test_*.py are manual scripts, not a pytest suite; backend has unit tests in 5 modules
- **Doc sprawl** — 18 loose .md status files in pipeline/, 13 .md/.sql at backend root

## Rebuild Checklist

1. Install prerequisites: Rust 1.70+, Node.js 18+, PostgreSQL 14+, Redis 7+, Python 3.10+
2. Configure `.env` files in backend/, frontend/, pipeline/, chatbot/
3. Run backend migrations (re-enable sqlx::migrate! or run manually), install all deps, start services
4. Initialize RAG embeddings via chatbot/sync-embeddings.js
5. Set up pipeline scheduling — pick ONE of scheduler.py / Airflow / Task Scheduler
