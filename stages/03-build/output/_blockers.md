# Blockers — Stage 03 Build

## No Critical Blockers

### Items to Complete
1. **Player props ETL** — pipeline needs a new ETL module to ingest player props from The Odds API (`/v4/sports/{sport}/odds?markets=player_props`). Not yet implemented.
2. **Enhanced parlays** — parlay type column migration and correlation engine not yet built.
3. **xG integration** — Understat scraper and feature engineering deferred.
4. **Rust compilation** — verify `cargo build` passes after adding `player_props` handler (requires `rust_decimal` and `chrono` in Cargo.toml — check dependencies).
