-- PostgreSQL schema for football betting pipeline
-- Run this script to create the required database tables

-- Create database (run separately as superuser if needed)
-- CREATE DATABASE football_betting;

-- Connect to database
-- \c football_betting;

-- Matches table (supports both football and basketball)
CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    sport_type TEXT DEFAULT 'football' CHECK (sport_type IN ('football', 'basketball')),
    competition TEXT,
    season DATE,
    date TIMESTAMP,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    result TEXT CHECK (result IN ('home_win', 'draw', 'away_win')),
    home_shots INTEGER,
    away_shots INTEGER,
    home_possession FLOAT,
    away_possession FLOAT,
    home_corners INTEGER,
    away_corners INTEGER,
    home_yellow_cards INTEGER,
    away_yellow_cards INTEGER,
    home_red_cards INTEGER,
    away_red_cards INTEGER,
    home_xg FLOAT,
    away_xg FLOAT,
    venue TEXT,
    referee TEXT,
    attendance INTEGER,
    status TEXT NOT NULL,
    data_source TEXT NOT NULL,
    home_team_wins_last_n INTEGER DEFAULT 0,
    home_team_draws_last_n INTEGER DEFAULT 0,
    home_team_losses_last_n INTEGER DEFAULT 0,
    away_team_wins_last_n INTEGER DEFAULT 0,
    away_team_draws_last_n INTEGER DEFAULT 0,
    away_team_losses_last_n INTEGER DEFAULT 0,
    home_team_avg_gd_last_n FLOAT DEFAULT 0.0,
    away_team_avg_gd_last_n FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Odds table
CREATE TABLE IF NOT EXISTS odds (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
    bookmaker TEXT NOT NULL,
    home_win FLOAT,
    draw FLOAT,
    away_win FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Predictions table (current/updatable predictions)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
    model_version TEXT NOT NULL,
    winner TEXT NOT NULL CHECK (winner IN ('home_win', 'draw', 'away_win')),
    home_prob FLOAT NOT NULL CHECK (home_prob >= 0 AND home_prob <= 1),
    draw_prob FLOAT NOT NULL CHECK (draw_prob >= 0 AND draw_prob <= 1),
    away_prob FLOAT NOT NULL CHECK (away_prob >= 0 AND away_prob <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prediction history table (immutable archive of first predictions)
-- Used for accuracy tracking - never overwritten once match is finished
CREATE TABLE IF NOT EXISTS prediction_history (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
    model_version TEXT NOT NULL,
    winner TEXT NOT NULL CHECK (winner IN ('home_win', 'draw', 'away_win')),
    home_prob FLOAT NOT NULL CHECK (home_prob >= 0 AND home_prob <= 1),
    draw_prob FLOAT NOT NULL CHECK (draw_prob >= 0 AND draw_prob <= 1),
    away_prob FLOAT NOT NULL CHECK (away_prob >= 0 AND away_prob <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP,  -- Set when match finishes, prediction becomes immutable
    UNIQUE(match_id)  -- Only one historical prediction per match
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team);

CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker);

CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);

CREATE INDEX IF NOT EXISTS idx_prediction_history_match_id ON prediction_history(match_id);
CREATE INDEX IF NOT EXISTS idx_prediction_history_locked_at ON prediction_history(locked_at);

-- Create updated_at trigger for matches table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_matches_updated_at 
    BEFORE UPDATE ON matches 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- Sample queries for verification
-- SELECT COUNT(*) FROM matches;
-- SELECT COUNT(*) FROM odds;
-- SELECT COUNT(*) FROM predictions;
