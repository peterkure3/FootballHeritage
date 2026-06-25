-- Player Props: Store player-specific betting markets
-- Supports props across all sports (NBA points/rebounds, NFL passing yards, MLB home runs, soccer goalscorer, etc.)

CREATE TABLE IF NOT EXISTS player_props (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    sport VARCHAR(50) NOT NULL,
    league VARCHAR(50) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    team VARCHAR(100),
    market VARCHAR(50) NOT NULL,
    line DECIMAL(10,2) NOT NULL,
    over_odds DECIMAL(10,2),
    under_odds DECIMAL(10,2),
    source VARCHAR(50) DEFAULT 'the_odds_api',
    source_updated_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_props_event ON player_props(event_id);
CREATE INDEX idx_player_props_market ON player_props(sport, market);
CREATE INDEX idx_player_props_player ON player_props(player_name);
CREATE INDEX idx_player_props_active ON player_props(event_id, is_active) WHERE is_active = true;
