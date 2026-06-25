# ADR-002: Player Props Data Model

## Status
Accepted

## Context
Player props (player-specific bets: points, rebounds, goals, passing yards, etc.) vary significantly by sport. Storing them as columns would explode the schema. Two options:
1. **JSONB column** on `events` table — flexible, no schema changes per sport
2. **Separate `player_props` table** — queryable, indexable, normalised

## Decision
Use a separate `player_props` table. While JSONB on `events` is simpler initially, player props need:
- Per-player filtering and searching
- Odds history tracking (line movement)
- Independent refresh cadence from events
- Aggregation queries ("show all props for LeBron James")

A normalized table supports all of these with proper indexes.

## Consequences
- (+) Queryable, indexable by player, market, sport
- (+) Independent refresh from events
- (+) Supports odds history via separate timestamps
- (-) Additional join required when fetching event + props together
- (-) Migration needed to create the table
