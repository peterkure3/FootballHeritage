-- ==========================================================================
-- Migration: Betting Intelligence Layer
-- Description: Adds devigging, EV, and arbitrage tables (source of truth: Postgres)
-- Date: 2026-01-24
-- ==========================================================================

-- Ensure UUID generation is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ======================================================
-- devigged_odds
-- Stores fair probabilities after removing bookmaker vig
-- ======================================================
CREATE TABLE IF NOT EXISTS devigged_odds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Link to backend events when available
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,

    -- Link back to pipeline match_id (The Odds API event id or football-data match id)
    pipeline_match_id TEXT,

    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'h2h',

    outcome_a TEXT NOT NULL,
    outcome_b TEXT NOT NULL,

    -- Odds are stored in American format (int)
    odds_a INTEGER NOT NULL,
    odds_b INTEGER NOT NULL,

    fair_prob_a DOUBLE PRECISION NOT NULL CHECK (fair_prob_a >= 0 AND fair_prob_a <= 1),
    fair_prob_b DOUBLE PRECISION NOT NULL CHECK (fair_prob_b >= 0 AND fair_prob_b <= 1),
    vig DOUBLE PRECISION NOT NULL,

    source_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devigged_odds_event_id ON devigged_odds(event_id);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_pipeline_match_id ON devigged_odds(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_book_market ON devigged_odds(bookmaker, market);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_created_at ON devigged_odds(created_at DESC);

-- Prevent duplicates for the same odds snapshot
CREATE UNIQUE INDEX IF NOT EXISTS uq_devigged_odds_snapshot
ON devigged_odds (pipeline_match_id, bookmaker, market, outcome_a, outcome_b, odds_a, odds_b, source_updated_at);

-- ======================================
-- ev_bets
-- Stores expected value computations
-- ======================================
CREATE TABLE IF NOT EXISTS ev_bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    pipeline_match_id TEXT,

    bookmaker TEXT,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,

    odds INTEGER NOT NULL,
    stake DECIMAL(15,2) NOT NULL CHECK (stake > 0),
    true_probability DOUBLE PRECISION NOT NULL CHECK (true_probability >= 0 AND true_probability <= 1),

    -- EV in stake currency units
    expected_value DOUBLE PRECISION NOT NULL,
    -- EV normalized by stake (e.g. 0.05 = +5%)
    expected_value_pct DOUBLE PRECISION NOT NULL,

    source_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ev_bets_event_id ON ev_bets(event_id);
CREATE INDEX IF NOT EXISTS idx_ev_bets_pipeline_match_id ON ev_bets(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_ev_bets_market ON ev_bets(market);
CREATE INDEX IF NOT EXISTS idx_ev_bets_ev_pct ON ev_bets(expected_value_pct DESC);
CREATE INDEX IF NOT EXISTS idx_ev_bets_created_at ON ev_bets(created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ev_bets_snapshot
ON ev_bets (pipeline_match_id, bookmaker, market, selection, odds, stake, true_probability, source_updated_at);

-- ======================================
-- arbitrage
-- Stores cross-book guaranteed profit
-- ======================================
CREATE TABLE IF NOT EXISTS arbitrage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    pipeline_match_id TEXT,

    market TEXT NOT NULL DEFAULT 'h2h',
    selection_a TEXT NOT NULL,
    selection_b TEXT NOT NULL,

    book_a TEXT NOT NULL,
    book_b TEXT NOT NULL,

    -- Decimal odds used for arbitrage math
    odds_a DOUBLE PRECISION NOT NULL,
    odds_b DOUBLE PRECISION NOT NULL,

    -- edge in [0, 1), e.g. 0.0123 for 1.23%
    arb_percentage DOUBLE PRECISION NOT NULL,

    total_stake DECIMAL(15,2) NOT NULL CHECK (total_stake > 0),
    stake_a DECIMAL(15,2) NOT NULL CHECK (stake_a > 0),
    stake_b DECIMAL(15,2) NOT NULL CHECK (stake_b > 0),

    source_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_arbitrage_event_id ON arbitrage(event_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_pipeline_match_id ON arbitrage(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_market ON arbitrage(market);
CREATE INDEX IF NOT EXISTS idx_arbitrage_edge ON arbitrage(arb_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_created_at ON arbitrage(created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_arbitrage_snapshot
ON arbitrage (pipeline_match_id, market, selection_a, selection_b, book_a, book_b, odds_a, odds_b, total_stake, source_updated_at);
