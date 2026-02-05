-- Migration: Add prediction_history table for preserving original predictions
-- Run this migration before using the updated regenerate_predictions.py

-- Prediction history table - stores the FIRST prediction made for each match
-- These are never overwritten and used for accuracy tracking
CREATE TABLE IF NOT EXISTS prediction_history (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
    model_version TEXT NOT NULL,
    winner TEXT NOT NULL CHECK (winner IN ('home_win', 'draw', 'away_win')),
    home_prob FLOAT NOT NULL CHECK (home_prob >= 0 AND home_prob <= 1),
    draw_prob FLOAT NOT NULL CHECK (draw_prob >= 0 AND draw_prob <= 1),
    away_prob FLOAT NOT NULL CHECK (away_prob >= 0 AND away_prob <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP,  -- When the match finished and prediction was locked
    UNIQUE(match_id)  -- Only one historical prediction per match
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_prediction_history_match_id ON prediction_history(match_id);
CREATE INDEX IF NOT EXISTS idx_prediction_history_locked_at ON prediction_history(locked_at);

-- Migrate existing predictions for finished matches to history
-- This preserves current predictions before the new logic takes effect
INSERT INTO prediction_history (match_id, model_version, winner, home_prob, draw_prob, away_prob, created_at, locked_at)
SELECT DISTINCT ON (p.match_id)
    p.match_id,
    p.model_version,
    p.winner,
    p.home_prob,
    p.draw_prob,
    p.away_prob,
    p.created_at,
    CASE WHEN m.status = 'FINISHED' THEN CURRENT_TIMESTAMP ELSE NULL END
FROM predictions p
JOIN matches m ON p.match_id = m.match_id
WHERE NOT EXISTS (
    SELECT 1 FROM prediction_history ph WHERE ph.match_id = p.match_id
)
ORDER BY p.match_id, p.created_at ASC;

-- Show migration results
SELECT 
    'Migrated ' || COUNT(*) || ' predictions to history' as result,
    COUNT(CASE WHEN locked_at IS NOT NULL THEN 1 END) || ' locked (finished matches)' as locked_count
FROM prediction_history;
