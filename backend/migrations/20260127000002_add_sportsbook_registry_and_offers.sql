-- ============================================================================
-- Migration: Sportsbook registry + normalized OddsAPI offers storage
-- Date: 2026-01-27
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- sportsbook_registry
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sportsbook_registry (
    book_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'oddsapi',
    provider_book_key TEXT NOT NULL,
    region TEXT NOT NULL CHECK (region IN ('us', 'eu', 'uk', 'au', 'global')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    supports_sports JSONB NOT NULL DEFAULT '[]'::jsonb,
    supports_markets JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_sharp_reference BOOLEAN NOT NULL DEFAULT FALSE,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_enabled_region
ON sportsbook_registry (enabled, region);

CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_provider
ON sportsbook_registry (provider, provider_book_key);

CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_priority
ON sportsbook_registry (priority ASC);

-- ------------------------------------------------------------
-- provider_events
-- Maps OddsAPI provider_event_id -> canonical events.id (when known)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provider_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider TEXT NOT NULL,
    provider_event_id TEXT NOT NULL,

    sport VARCHAR(50),
    league VARCHAR(100),
    home_team TEXT,
    away_team TEXT,
    commence_time TIMESTAMP WITH TIME ZONE,

    -- canonical event_id in football_heritage.events when matched
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,

    source_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_events
ON provider_events (provider, provider_event_id);

CREATE INDEX IF NOT EXISTS idx_provider_events_event_id
ON provider_events (event_id);

CREATE INDEX IF NOT EXISTS idx_provider_events_commence_time
ON provider_events (commence_time);

-- ------------------------------------------------------------
-- odds_offers
-- Normalized odds rows (one selection per row). All odds are decimal.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS odds_offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    provider TEXT NOT NULL,
    provider_event_id TEXT NOT NULL,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,

    book_key TEXT NOT NULL REFERENCES sportsbook_registry(book_key) ON DELETE RESTRICT,

    -- canonical market key: h2h | spreads | totals | player_props
    market TEXT NOT NULL,

    -- selection conventions:
    -- - h2h: HOME/AWAY/DRAW
    -- - totals: OVER/UNDER
    -- - spreads: HOME/AWAY (line stored in line)
    selection TEXT NOT NULL,

    -- spreads/totals/props line (e.g. -3.5, 47.5, player line)
    line DOUBLE PRECISION,

    -- optional participant (player name for props; can also store team name)
    participant TEXT,

    odds_decimal DOUBLE PRECISION NOT NULL CHECK (odds_decimal > 1.0),

    source_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_odds_offers_provider_event
ON odds_offers (provider, provider_event_id);

CREATE INDEX IF NOT EXISTS idx_odds_offers_event_id
ON odds_offers (event_id);

CREATE INDEX IF NOT EXISTS idx_odds_offers_book_market
ON odds_offers (book_key, market);

CREATE INDEX IF NOT EXISTS idx_odds_offers_created_at
ON odds_offers (created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_odds_offers_snapshot
ON odds_offers (provider, provider_event_id, book_key, market, selection, line, participant, source_updated_at, odds_decimal);

-- ------------------------------------------------------------
-- Seed registry with a starter set of common books.
-- NOTE: Provider keys may vary by region/availability in your OddsAPI plan.
-- ------------------------------------------------------------
INSERT INTO sportsbook_registry (
    book_key,
    display_name,
    provider,
    provider_book_key,
    region,
    enabled,
    supports_sports,
    supports_markets,
    is_sharp_reference,
    priority
) VALUES
    ('pinnacle', 'Pinnacle', 'oddsapi', 'pinnacle', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, TRUE, 1),
    ('betfair', 'Betfair', 'oddsapi', 'betfair', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, TRUE, 2),

    ('draftkings', 'DraftKings', 'oddsapi', 'draftkings', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 10),
    ('fanduel', 'FanDuel', 'oddsapi', 'fanduel', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 11),
    ('betmgm', 'BetMGM', 'oddsapi', 'betmgm', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 12),
    ('caesars', 'Caesars', 'oddsapi', 'caesars', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 13),
    ('pointsbet', 'PointsBet', 'oddsapi', 'pointsbetus', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 14),
    ('betrivers', 'BetRivers', 'oddsapi', 'betrivers', 'us', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals","player_props"]'::jsonb, FALSE, 15),
    ('barstool', 'Barstool', 'oddsapi', 'barstool', 'us', FALSE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 16),

    ('williamhill', 'William Hill', 'oddsapi', 'williamhill', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 20),
    ('ladbrokes', 'Ladbrokes', 'oddsapi', 'ladbrokes', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 21),
    ('coral', 'Coral', 'oddsapi', 'coral', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 22),
    ('paddypower', 'Paddy Power', 'oddsapi', 'paddypower', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 23),
    ('bet365', 'bet365', 'oddsapi', 'bet365', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 24),

    ('unibet', 'Unibet', 'oddsapi', 'unibet', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 30),
    ('betway', 'Betway', 'oddsapi', 'betway', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 31),
    ('bwin', 'bwin', 'oddsapi', 'bwin', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 32),
    ('marathonbet', 'Marathonbet', 'oddsapi', 'marathonbet', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 33),
    ('tipico', 'Tipico', 'oddsapi', 'tipico', 'eu', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 34),
    ('skybet', 'Sky Bet', 'oddsapi', 'skybet', 'uk', TRUE, '["football","basketball"]'::jsonb, '["h2h","spreads","totals"]'::jsonb, FALSE, 35)
ON CONFLICT (book_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    provider = EXCLUDED.provider,
    provider_book_key = EXCLUDED.provider_book_key,
    region = EXCLUDED.region,
    enabled = EXCLUDED.enabled,
    supports_sports = EXCLUDED.supports_sports,
    supports_markets = EXCLUDED.supports_markets,
    is_sharp_reference = EXCLUDED.is_sharp_reference,
    priority = EXCLUDED.priority,
    updated_at = CURRENT_TIMESTAMP;
