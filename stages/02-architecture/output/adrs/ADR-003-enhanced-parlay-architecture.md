# ADR-003: Enhanced Parlay Architecture

## Status
Accepted

## Context
Current parlay system supports standard multi-leg parlays. User wants enhanced features:
- **System bets** — bet on N of M legs (e.g., 2 of 3, 3 of 4)
- **Correlation warnings** — flag same-game/same-league bets with correlated outcomes
- **Combined EV** — expected value across all legs

## Decision
Extend the existing parlay model incrementally:

1. **Parlay type column** — add `parlay_type` enum to `parlays` table (`standard`, `system_N_M`, `teaser`, `pleaser`)
2. **Enhanced calculation** — update `POST /api/v1/parlay/calculate` to handle system bet combinatorics (C(n,k) combinations)
3. **Correlation engine** — add `POST /api/v1/parlay/enrich` endpoint (exists in pipeline) to detect:
   - Same-game legs (correlated outcomes)
   - Same-league same-week legs (partial correlation)
   - Flag with severity level
4. **Combined EV** — compute as product of individual leg edges, accounting for correlation discount

Keep `ParlayBuilderSidebar` as the primary UI component, adding:
- Parlay type selector dropdown
- System bet configuration (N of M selector)
- Correlation warning badges on flagged legs

## Consequences
- (+) Incremental change — existing parlay functionality intact
- (+) Reuses existing `ParlayBuilderSidebar` and pipeline enrichment endpoint
- (-) System bet combinatorics add complexity to the calculation endpoint
- (-) Correlation detection is heuristic — may have false positives
