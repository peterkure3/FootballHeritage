-- ==========================================================================
-- Migration: Devigged Odds Archive Table
-- Description: Archive table for historical devigged odds analysis
-- Date: 2026-02-09
-- ==========================================================================

-- Archive table for devigged_odds historical analysis
-- Stores snapshots before each recompute for vig trend analysis
CREATE TABLE IF NOT EXISTS devigged_odds_archive (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Original record ID for reference
    original_id UUID,
    
    -- Link to backend events when available
    event_id UUID,
    
    -- Link back to pipeline match_id
    pipeline_match_id TEXT,
    
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'h2h',
    
    outcome_a TEXT NOT NULL,
    outcome_b TEXT NOT NULL,
    
    odds_a DOUBLE PRECISION NOT NULL,
    odds_b DOUBLE PRECISION NOT NULL,
    
    fair_prob_a DOUBLE PRECISION NOT NULL,
    fair_prob_b DOUBLE PRECISION NOT NULL,
    vig DOUBLE PRECISION NOT NULL,
    
    source_updated_at TIMESTAMP WITH TIME ZONE,
    original_created_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devigged_archive_event_id ON devigged_odds_archive(event_id);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_pipeline_match_id ON devigged_odds_archive(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_bookmaker ON devigged_odds_archive(bookmaker);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_archived_at ON devigged_odds_archive(archived_at DESC);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_source_updated ON devigged_odds_archive(source_updated_at);
