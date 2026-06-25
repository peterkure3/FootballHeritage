# Data Model — FootballHeritage

## Database Architecture
Two PostgreSQL databases with distinct responsibilities:

### football_betting (Pipeline / ML)
| Purpose | Pipeline ETL storage, ML training, prediction serving |
|---------|-------------------------------------------------------|
| **Key Tables** | `matches`, `odds`, `predictions`, `nba_games` |
| **Owner** | Python pipeline |
| **Schema** | Managed by pipeline/etl/load_to_db.py |

### football_heritage (Platform)
| Purpose | User accounts, bets, wallets, events, intelligence |
|---------|----------------------------------------------------|
| **Key Tables** | `users`, `wallets`, `transactions`, `bets`, `events`, `gambling_limits`, `parlays`, `devigged_odds`, `ev_bets`, `arbitrage`, `fraud_alerts`, `admin_logs` |
| **Owner** | Rust backend (SQLx migrations) |
| **Schema** | Managed by backend/migrations/ |

## Core Entity Relationships

```
users 1─* wallets
users 1─* bets
users 1─1 gambling_limits
users 1─* transactions
users 1─* user_activity_log

events 1─* bets
events 1─* devigged_odds
events 1─* ev_bets
events 1─* arbitrage

parlays 1─* parlay_legs
parlays 1─* parlay_calculations

users *─* parlays (via parlay_legs user_id)

bets 1─* betting_patterns (fraud detection)
users 1─* fraud_alerts
```

## Key Schema Details

### events
```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    sport VARCHAR(50) NOT NULL,       -- 'soccer', 'basketball', 'americanfootball', 'baseball', 'icehockey'
    league VARCHAR(50) NOT NULL,      -- 'EPL', 'NBA', 'NFL', 'MLB', 'NHL' etc.
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    event_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'UPCOMING',  -- UPCOMING, LIVE, FINISHED, CANCELLED
    moneyline_home DECIMAL(10,2),
    moneyline_away DECIMAL(10,2),
    point_spread DECIMAL(5,1),
    spread_home_odds DECIMAL(10,2),
    spread_away_odds DECIMAL(10,2),
    total_points DECIMAL(5,1),
    over_odds DECIMAL(10,2),
    under_odds DECIMAL(10,2),
    -- Player props (new for expansion)
    props_home JSONB,                  -- {player_name: {market: odds, ...}}
    props_away JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Design note:** Using `JSONB` for player props to avoid schema explosion per sport. Each sport has different prop types (goalscorer for soccer, passing yards for NFL, points for NBA, home runs for MLB). JSONB allows flexible storage without migrations.

### Proposed: player_props (separate table, preferred for queryability)
```sql
CREATE TABLE player_props (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id),
    sport VARCHAR(50) NOT NULL,
    league VARCHAR(50) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    team VARCHAR(100),
    market VARCHAR(50) NOT NULL,       -- 'points', 'rebounds', 'passing_yards', 'goalscorer', 'home_runs'
    line DECIMAL(10,2),
    over_odds DECIMAL(10,2),
    under_odds DECIMAL(10,2),
    source VARCHAR(50) DEFAULT 'the_odds_api',
    source_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_player_props_event ON player_props(event_id);
CREATE INDEX idx_player_props_market ON player_props(sport, market);
```

### Proposed: enhanced_parlays (extending current parlay model)
```sql
-- Extending existing parlays table with system bet support
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS parlay_type VARCHAR(20) DEFAULT 'standard';
-- parlay_type: 'standard', 'system_2_3', 'system_3_4', 'system_2_4', 'teaser', 'pleaser'

ALTER TABLE parlays ADD COLUMN IF NOT EXISTS system_combinations INT;  -- number of winning combos needed
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS total_combinations INT;   -- total possible combos
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS combined_edge DECIMAL(10,4);
```

### matches (football_betting DB — pipeline schema)
```sql
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    competition VARCHAR(50),
    season VARCHAR(20),
    match_date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INT,
    away_score INT,
    status VARCHAR(20),
    -- Odds columns for various bookmakers
    bet365_home DECIMAL(10,2), bet365_draw DECIMAL(10,2), bet365_away DECIMAL(10,2),
    pinnacle_home DECIMAL(10,2), pinnacle_draw DECIMAL(10,2), pinnacle_away DECIMAL(10,2),
    -- ML features populated during transform
    elo_home DECIMAL(10,2),
    elo_away DECIMAL(10,2),
    form_home DECIMAL(10,2),
    form_away DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Data Flow Summary
```
The Odds API ──► fetch_raw_data.py ──► ingest_oddsapi_offers.py ──► match_oddsapi_events.py ──► 
    ├── football_betting.odds
    ├── football_heritage.odds_offers (via heritage DB)
    └── compute_intelligence.py ──► football_heritage.devigged_odds / ev_bets / arbitrage

football-data.org ──► fetch_raw_data.py ──► transform.py (Parquet) ──► load_to_db.py ──► 
    └── football_betting.matches

ML Pipeline:
    transform.py (Parquet + features) ──► train_model_v2.py ──► predict_v2.py ──► 
        └── sync_to_backend.py ──► football_heritage.predictions
```
