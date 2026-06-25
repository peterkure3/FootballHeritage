# Build Artifacts — Stage 03 Build

## Configuration Changes
| File | Change |
|------|--------|
| `pipeline/.env` | Add `americanfootball_nfl`, `baseball_mlb`, `icehockey_nhl`, etc. to `ODDS_API_SPORTS` |
| `backend/.env` | No changes needed |

## New Migrations
| Migration | Description |
|-----------|-------------|
| `20260210000001_add_player_props.sql` | Create player_props table with indexes |

## New API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/player-props` | List player props (filters: sport, event_id, player, market) |
| GET | `/api/v1/player-props/event/{id}` | Get props by event ID |

## New Frontend Routes
| Route | Page | Description |
|-------|------|-------------|
| `/player-props` | PlayerProps | Browse player props across all sports |

## Env Var Changes
| Variable | Service | Required | Default |
|----------|---------|----------|---------|
| `ODDS_API_SPORTS` | Pipeline | No | Updated list includes NFL, MLB, NHL, NCAAB, more soccer |

## Database Migrations
Run `cargo sqlx migrate run` in `backend/` to apply the player_props table.
