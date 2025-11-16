-- Add parlay calculator tables for Expected Value calculations
-- Migration: 20251027000001_add_parlay_calculator

-- Parlays table - stores saved parlay combinations
CREATE TABLE IF NOT EXISTS parlays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100),
    total_stake DECIMAL(15,2) NOT NULL CHECK (total_stake > 0),
    combined_odds DECIMAL(10,2) NOT NULL,
    combined_probability DECIMAL(5,4) NOT NULL CHECK (combined_probability >= 0 AND combined_probability <= 1),
    expected_value DECIMAL(15,2) NOT NULL,
    potential_payout DECIMAL(15,2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')),
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'WON', 'LOST', 'PUSH', 'CANCELLED')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Parlay legs - individual bets within a parlay
CREATE TABLE IF NOT EXISTS parlay_legs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parlay_id UUID NOT NULL REFERENCES parlays(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    team_name VARCHAR(100) NOT NULL,
    bet_type VARCHAR(20) NOT NULL CHECK (bet_type IN ('MONEYLINE', 'SPREAD', 'TOTAL')),
    selection VARCHAR(10) NOT NULL CHECK (selection IN ('HOME', 'AWAY', 'OVER', 'UNDER')),
    odds DECIMAL(6,2) NOT NULL,
    win_probability DECIMAL(5,4) CHECK (win_probability >= 0 AND win_probability <= 1),
    leg_order INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Parlay calculations history - ephemeral calculations for analytics
CREATE TABLE IF NOT EXISTS parlay_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    num_legs INTEGER NOT NULL CHECK (num_legs > 0),
    total_stake DECIMAL(15,2) NOT NULL,
    combined_odds DECIMAL(10,2) NOT NULL,
    combined_probability DECIMAL(5,4) NOT NULL,
    expected_value DECIMAL(15,2) NOT NULL,
    expected_profit DECIMAL(15,2) NOT NULL,
    potential_payout DECIMAL(15,2) NOT NULL,
    break_even_probability DECIMAL(5,4) NOT NULL,
    kelly_criterion DECIMAL(5,4),
    risk_level VARCHAR(20) NOT NULL,
    recommendation TEXT NOT NULL,
    calculation_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_parlays_user_id ON parlays(user_id);
CREATE INDEX IF NOT EXISTS idx_parlays_status ON parlays(status);
CREATE INDEX IF NOT EXISTS idx_parlays_created_at ON parlays(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_parlay_legs_parlay_id ON parlay_legs(parlay_id);
CREATE INDEX IF NOT EXISTS idx_parlay_legs_event_id ON parlay_legs(event_id);
CREATE INDEX IF NOT EXISTS idx_parlay_calculations_user_id ON parlay_calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_parlay_calculations_created_at ON parlay_calculations(created_at DESC);

-- Trigger to update updated_at on parlays
CREATE OR REPLACE FUNCTION update_parlay_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_parlay_updated_at
    BEFORE UPDATE ON parlays
    FOR EACH ROW
    EXECUTE FUNCTION update_parlay_updated_at();

-- Comments for documentation
COMMENT ON TABLE parlays IS 'Stores saved parlay combinations with EV calculations';
COMMENT ON TABLE parlay_legs IS 'Individual bets that make up a parlay';
COMMENT ON TABLE parlay_calculations IS 'History of all parlay calculations for analytics';
COMMENT ON COLUMN parlays.combined_odds IS 'Product of all individual bet odds';
COMMENT ON COLUMN parlays.combined_probability IS 'Product of all individual win probabilities';
COMMENT ON COLUMN parlays.expected_value IS 'Expected value as percentage of stake';
COMMENT ON COLUMN parlay_calculations.kelly_criterion IS 'Kelly Criterion suggested stake percentage (0-0.25)';
