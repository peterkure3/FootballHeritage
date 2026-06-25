-- Enhanced Parlays: Add system bet support and correlation tracking
-- Migration: 20260210000002_add_enhanced_parlays

ALTER TABLE parlays ADD COLUMN IF NOT EXISTS parlay_type VARCHAR(20) DEFAULT 'STANDARD'
    CHECK (parlay_type IN ('STANDARD', 'SYSTEM_2_3', 'SYSTEM_3_4', 'SYSTEM_2_4', 'SYSTEM_3_5', 'TEASER', 'PLEASER'));

ALTER TABLE parlays ADD COLUMN IF NOT EXISTS system_min_legs INTEGER
    CHECK (system_min_legs IS NULL OR system_min_legs > 0);

ALTER TABLE parlays ADD COLUMN IF NOT EXISTS total_combinations INTEGER;
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS combined_edge DECIMAL(10,4);
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS correlation_score DECIMAL(5,4) DEFAULT 0;

-- Correlation warnings for parlay legs
CREATE TABLE IF NOT EXISTS parlay_correlation_warnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parlay_id UUID NOT NULL REFERENCES parlays(id) ON DELETE CASCADE,
    leg_a_id UUID NOT NULL REFERENCES parlay_legs(id) ON DELETE CASCADE,
    leg_b_id UUID NOT NULL REFERENCES parlay_legs(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    reason TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parlay_correlation_parlay ON parlay_correlation_warnings(parlay_id);

-- Tournament brackets for system bet combinatorics
CREATE TABLE IF NOT EXISTS parlay_system_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parlay_id UUID NOT NULL REFERENCES parlays(id) ON DELETE CASCADE,
    combination_number INTEGER NOT NULL,
    leg_ids UUID[] NOT NULL,
    combined_odds DECIMAL(10,2) NOT NULL,
    combined_probability DECIMAL(5,4),
    potential_payout DECIMAL(15,2),
    is_winning BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parlay_system_parlay ON parlay_system_results(parlay_id);

COMMENT ON COLUMN parlays.parlay_type IS 'Type of parlay: STANDARD, SYSTEM_N_M (N of M must win), TEASER, PLEASER';
COMMENT ON COLUMN parlays.system_min_legs IS 'For system bets: minimum number of legs that must win';
COMMENT ON COLUMN parlays.correlation_score IS '0-1 score where higher means more correlated bets';
COMMENT ON TABLE parlay_correlation_warnings IS 'Correlation warnings between pairs of legs in a parlay';
COMMENT ON TABLE parlay_system_results IS 'Individual combination results for system bets';
