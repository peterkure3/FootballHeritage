# Changelog — Stage 03 Build

## Changes Implemented

### 1. Sports Expansion (Pipeline Config)
- **File:** `pipeline/config.py`
- Added 5 new sport keys to `ODDS_API_SPORTS`: `soccer_netherlands_eredivisie`, `soccer_portugal_primeira_liga`, `americanfootball_nfl`, `americanfootball_ncaaf`, `baseball_mlb`, `icehockey_nhl`
- Added 3 new sport configs to `SPORT_CONFIGS`: `americanfootball`, `baseball`, `icehockey` with appropriate num_classes, draw settings, and form windows

### 2. Player Props Database Migration
- **File:** `backend/migrations/20260210000001_add_player_props.sql`
- Created `player_props` table with indexes on event_id, market, player_name, active filter

### 3. Player Props Backend API
- **File:** `backend/src/handlers/player_props.rs` (new)
- `GET /api/v1/player-props` — list player props with optional filters (sport, event_id, player, market)
- `GET /api/v1/player-props/event/{id}` — get props for a specific event

### 4. Player Props Frontend Page
- **File:** `frontend/src/pages/PlayerProps.jsx` (new)
- Sport filter buttons, loading/empty/error states, prop cards with odds
- Route at `/player-props`, link in Navbar AI Tools

### 5. Navbar Updates
- **File:** `frontend/src/components/Navbar.jsx`
- Quick Filters: added Baseball and Hockey (now shows all 5 sports)
- Player Props link in AI Tools dropdown

### 6. Player Props ETL Pipeline
- **File:** `pipeline/etl/ingest_player_props.py` (new)
- Fetches player props from The Odds API for all tracked sports
- Supports markets: player_points, player_rebounds, player_assists, player_passing_yards, player_rushing_yards, player_receiving_yards, player_touchdowns, player_home_runs, player_strikeouts, player_goalscorer
- Upserts into `player_props` table via SQLAlchemy
- Run: `python -m etl.ingest_player_props`

### 7. Enhanced Parlays Migration
- **File:** `backend/migrations/20260210000002_add_enhanced_parlays.sql` (new)
- Added `parlay_type` column (STANDARD, SYSTEM_N_M, TEASER, PLEASER)
- Added `system_min_legs`, `total_combinations`, `combined_edge`, `correlation_score` columns
- Created `parlay_correlation_warnings` table (per-leg-pair correlation with severity)
- Created `parlay_system_results` table (individual combination results for system bets)

### 8. Understat xG Scraper
- **File:** `pipeline/etl/fetch_xg_data.py` (new)
- Fetches match-level xG, xGA, deep, PPDA data for all major European leagues
- Calculates rolling xG averages (5-match window) as ML features
- Saves to Parquet for model training ingestion
- Run: `python -m etl.fetch_xg_data`

## Verification
- ✅ Backend compiles (`cargo check` passed)
- ✅ Frontend builds (`vite build` production build successful)
- ✅ All new features documented in build-artifacts.md

## To Apply Migrations
```bash
cd backend
cargo sqlx migrate run
```
