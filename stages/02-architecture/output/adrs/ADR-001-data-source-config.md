# ADR-001: Config-Driven Data Source Expansion

## Status
Accepted

## Context
Adding new sports (NFL, MLB, NHL, more soccer) requires changes across pipeline ETL, backend API, and frontend UI. Each sport needs:
- API sport key configuration
- ETL pipeline steps (fetch → transform → load)
- UI pages/filters

## Decision
Use environment variable-driven configuration for sport coverage. The existing `ODDS_API_SPORTS` env var in the pipeline already supports comma-separated sport keys. Extend this approach:
- **Pipeline:** `config.py` reads a `SPORTS_CONFIG` JSON that maps sport key → league metadata (display name, icon, bet types available)
- **Backend:** `events.sport` and `events.league` columns are generic strings — no schema changes needed
- **Frontend:** Sport filter dropdown populated from `GET /api/v1/sports` endpoint (already exists, returns sports with event counts)

New sports require:
1. Add sport key to `ODDS_API_SPORTS`
2. Add league metadata to `SPORTS_CONFIG`
3. (Optional) Create sport-specific transform module if data needs differ

## Consequences
- (+) Adding a sport is a config change, not a code change
- (+) Reuses existing ETL/API/UI architecture
- (-) Must ensure The Odds API free tier quota accommodates new sports
- (-) Sport-specific data nuances (e.g., NHL overtime rules) need custom transform logic
