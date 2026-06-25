# Scope Document — FootballHeritage

## Project Overview
FootballHeritage is a comprehensive AI-powered sports betting platform with real-time odds, prediction analytics, responsible gambling features, and an end-to-end data pipeline for sports data ingestion, modeling, and API serving.

## Current State (as of Intake)

### What Exists

**Backend (Rust + Actix-web):**
- 40+ REST API endpoints across auth, betting, wallet, sports, parlay, intelligence, admin, and chat modules
- PostgreSQL with 17+ tables: users, wallets, transactions, events, bets, gambling_limits, parlays, fraud_alerts, devigged_odds, ev_bets, arbitrage
- JWT authentication with session management, role-based access (user/admin/superadmin)
- AES-256-GCM wallet encryption, bcrypt/Argon2id password hashing
- Token-bucket rate limiting (per-user and per-IP)
- Betting intelligence endpoints reading from devigged/EV/arbitrage tables
- Admin endpoints for user/event/analytics/monitoring management
- Parlay calculator with ML enrichment endpoints
- Middleware stack: JWT auth, admin auth, rate limiting, security headers, metrics

**Frontend (React 19 + Vite 7 + TailwindCSS 4):**
- 27 pages covering: dashboard, odds, bet history, smart assistant, sports, predictions, devigged odds, EV bets, arbitrage, best bets, parlay calculator, profile, college sports, FPL advisor, and 10 admin pages
- 20+ shared components (Navbar, OddsRow, BetCard, WalletModal, AgeVerificationModal, PredictionCard, etc.)
- Admin components: layout, navbar, sidebar, chatbot
- Parlay components: builder sidebar, leg display, results, search, suggestions
- Prediction components: history viewer with filters, accuracy metrics, confidence charts
- Zustand stores: auth, betting session limits, parlay builder (persisted), app settings/themes (persisted)
- React Query hooks for all API data fetching with auto-refetch intervals
- Dark/light/system theme support

**Data Pipeline (Python + FastAPI):**
- 31 ETL modules covering fetch, transform, load for multiple data sources
- 3 external data APIs: football-data.org, The Odds API, balldontlie.io (NBA)
- 2 web scrapers: Basketball Reference, NCAA API
- FPL (Fantasy Premier League) integration
- V2 stacking ensemble ML model (XGBoost + LightGBM + RandomForest + GradientBoosting) with isotonic calibration
- 38 features: odds-derived, ELO ratings, H2H stats, weighted form, venue stats
- Elo rating model with league-specific parameters
- True probability calculator (5-method ensemble: sharp book devigging, consensus odds, Elo, power method, Shin)
- Intelligence pipeline: devigging, EV calculation, arbitrage detection (v1 and v2)
- Model accuracy: 72.74% live, 94.86% high-confidence tier
- 24 FastAPI endpoints for predictions, intelligence, smart assistant, parlay, FPL, NCAAB
- ~874.5K train + 218.6K validation samples
- Dual database setup: football_betting (main) + football_heritage (intelligence)

**Chatbot (Node.js + Express + Genkit):**
- RAG-enhanced AI assistant using Gemini 2.0 Flash
- Query router with intent classification (games, betting, statistics, account, help, general)
- Hybrid retrieval: pgvector cosine similarity + PostgreSQL full-text search + Reciprocal Rank Fusion
- Redis caching with intent-aware TTLs (15-18ms cached, 95-110ms uncached, 65-70% hit rate)
- Knowledge base ingestion (league docs, team docs)
- Rate limited (12 req/min per user default)
- Embedded as microservice behind Rust backend proxy

**Infrastructure:**
- PostgreSQL 14+ (dual database)
- Redis 7+ for caching
- Docker-ready (docker-compose)
- GitHub Actions CI (frontend)
- Database backup/restore scripts

### Metrics & Performance
- ML Live Accuracy: 72.74% overall, 94.86% high-confidence
- Model: v2.0.0 Stacking Ensemble, 38 features
- RAG: 15-18ms cached, 95-110ms uncached, 65-70% hit rate
- Training data: 874.5K train + 218.6K validation
- 543+ predictions tracked with outcomes
- 40+ Rust API endpoints, 24 Python API endpoints, 2 chatbot endpoints

### Known Issues (from codebase)
- Frontend `.env` port mismatch (8888 vs 8080)
- `VITE_PIPELINE_API_URL` missing from frontend `.env`
- Playwright test config disabled
- Frontend README references React 18 but codebase uses React 19
- Admin bet management routes commented out

## Goals (Next 3 Months)

### Primary
1. **Improve ML prediction accuracy** — push overall accuracy beyond 75%, high-confidence beyond 96%
2. **UI improvements** — polish existing pages, improve responsive design, enhance data visualizations
3. **Expand sports coverage** — add more soccer leagues, additional sports (NFL, MLB, NHL), more college sports
4. **Expand betting options** — more bet types, live betting support, enhanced parlay features

### Secondary
5. Improve test coverage (backend unit tests, frontend component tests, E2E)
6. Production hardening (monitoring, alerting, backup automation)
7. Documentation improvements (API docs, deployment guide, runbook)

## Out of Scope (for next 3 months)
- Mobile app development (React Native/Expo already scaffolded but deferred)
- Formal gambling license acquisition
- Multi-tenant/multi-jurisdiction support
- Real-money payment gateway integration (use play money/wallet system)
- Native mobile push notifications
- Third-party affiliate/referral system

## Constraints
- **Solo developer** — scope must be achievable by one person
- **Self-regulated** — no formal compliance burden, but responsible gambling features must remain intact
- **Free-tier APIs** — Gemini free tier, The Odds API free tier limits
- **Existing architecture** — must work within current Rust/Python/Node.js stack

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| The Odds API rate limits | Data freshness | Caching tier, staggered polling |
| ML accuracy plateau | User trust | Feature engineering, ensemble tuning |
| Solo dev bottleneck | Velocity | Prioritize high-impact features, defer nice-to-haves |
| API key exposure | Security | Env var management, .gitignore discipline |
| PostgreSQL scaling | Performance | Connection pooling, query optimization |
