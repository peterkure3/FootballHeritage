-- Create database
CREATE DATABASE football_heritage;

-- Connect to database
\c football_heritage;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    CONSTRAINT check_age CHECK (EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth)) >= 21)
);

-- Wallets table with encrypted balance
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    encrypted_balance TEXT NOT NULL,
    encryption_iv TEXT NOT NULL,
    total_deposits DECIMAL(15,2) DEFAULT 0.00,
    total_withdrawals DECIMAL(15,2) DEFAULT 0.00,
    total_winnings DECIMAL(15,2) DEFAULT 0.00,
    total_losses DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_encrypted_balance_not_empty CHECK (encrypted_balance IS NOT NULL AND encrypted_balance != '')
);

-- Transactions table for audit trail
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'BET_PLACED', 'BET_WON', 'BET_LOST')),
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    balance_before DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_fraud_flagged BOOLEAN DEFAULT FALSE
);

-- Sports events table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sport VARCHAR(50) NOT NULL,
    league VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'UPCOMING' CHECK (status IN ('UPCOMING', 'LIVE', 'FINISHED', 'CANCELLED')),
    home_score INTEGER,
    away_score INTEGER,
    moneyline_home DECIMAL(6,2),  -- Odds for home team
    moneyline_away DECIMAL(6,2),  -- Odds for away team
    point_spread DECIMAL(5,1),    -- Point spread
    spread_home_odds DECIMAL(6,2), -- Odds for home team with spread
    spread_away_odds DECIMAL(6,2), -- Odds for away team with spread
    total_points DECIMAL(5,1),    -- Over/under total
    over_odds DECIMAL(6,2),       -- Odds for over
    under_odds DECIMAL(6,2),      -- Odds for under
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bets table
CREATE TABLE bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    bet_type VARCHAR(20) NOT NULL CHECK (bet_type IN ('MONEYLINE', 'SPREAD', 'TOTAL')),
    selection VARCHAR(10) NOT NULL CHECK (selection IN ('HOME', 'AWAY', 'OVER', 'UNDER')),
    odds DECIMAL(6,2) NOT NULL,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    potential_win DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'WON', 'LOST', 'PUSH', 'CANCELLED')),
    settled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Responsible gambling limits
CREATE TABLE gambling_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_loss_limit DECIMAL(15,2),
    weekly_loss_limit DECIMAL(15,2),
    monthly_loss_limit DECIMAL(15,2),
    daily_bet_limit DECIMAL(15,2),
    weekly_bet_limit DECIMAL(15,2),
    monthly_bet_limit DECIMAL(15,2),
    max_single_bet DECIMAL(15,2),
    session_time_limit INTEGER, -- in minutes
    self_exclusion_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User activity tracking for fraud detection
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    is_suspicious BOOLEAN DEFAULT FALSE
);

-- Betting patterns analysis
CREATE TABLE betting_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_data JSONB NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_flagged BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id),
    review_notes TEXT
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_wallets_user_id ON wallets(user_id);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_events_sport ON events(sport);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_bets_user_id ON bets(user_id);
CREATE INDEX idx_bets_event_id ON bets(event_id);
CREATE INDEX idx_bets_status ON bets(status);
CREATE INDEX idx_bets_created_at ON bets(created_at);
CREATE INDEX idx_gambling_limits_user_id ON gambling_limits(user_id);
CREATE INDEX idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_user_activity_timestamp ON user_activity(timestamp);
CREATE INDEX idx_user_activity_ip ON user_activity(ip_address);

-- Create trigger for updating updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bets_updated_at BEFORE UPDATE ON bets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gambling_limits_updated_at BEFORE UPDATE ON gambling_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample NFL events with realistic odds
INSERT INTO events (sport, league, home_team, away_team, event_date, moneyline_home, moneyline_away, point_spread, spread_home_odds, spread_away_odds, total_points, over_odds, under_odds) VALUES
('Football', 'NFL', 'Kansas City Chiefs', 'Buffalo Bills', CURRENT_TIMESTAMP + INTERVAL '2 days', -150, +130, -3.5, -110, -110, 52.5, -105, -115),
('Football', 'NFL', 'San Francisco 49ers', 'Dallas Cowboys', CURRENT_TIMESTAMP + INTERVAL '3 days', -125, +105, -2.5, -115, -105, 48.5, -110, -110),
('Football', 'NFL', 'Philadelphia Eagles', 'Miami Dolphins', CURRENT_TIMESTAMP + INTERVAL '4 days', +110, -130, +1.5, -105, -115, 54.5, -115, -105),
('Football', 'NFL', 'Detroit Lions', 'Tampa Bay Buccaneers', CURRENT_TIMESTAMP + INTERVAL '5 days', -140, +120, -4.5, -105, -115, 47.5, -110, -110),
('Football', 'NFL', 'Baltimore Ravens', 'Cincinnati Bengals', CURRENT_TIMESTAMP + INTERVAL '6 days', -160, +140, -6.5, -115, -105, 45.5, -105, -115),
('Football', 'NFL', 'Green Bay Packers', 'Minnesota Vikings', CURRENT_TIMESTAMP + INTERVAL '7 days', -105, -115, -1.5, -110, -110, 51.5, -115, -105),
('Football', 'NFL', 'New York Jets', 'New England Patriots', CURRENT_TIMESTAMP + INTERVAL '8 days', +130, -150, +3.5, -115, -105, 42.5, -110, -110),
('Football', 'NFL', 'Los Angeles Rams', 'Seattle Seahawks', CURRENT_TIMESTAMP + INTERVAL '9 days', -120, +100, -2.0, -110, -110, 49.5, -105, -115),
('Football', 'NFL', 'Arizona Cardinals', 'San Francisco 49ers', CURRENT_TIMESTAMP + INTERVAL '10 days', +180, -220, +7.5, -105, -115, 44.5, -110, -110),
('Football', 'NFL', 'Cleveland Browns', 'Pittsburgh Steelers', CURRENT_TIMESTAMP + INTERVAL '11 days', +105, -125, +1.0, -115, -105, 46.5, -115, -105);
