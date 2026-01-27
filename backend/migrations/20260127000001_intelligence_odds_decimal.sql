-- ============================================================================
-- Migration: Convert betting intelligence odds columns to decimal
-- Date: 2026-01-27
-- ============================================================================

-- Drop unique indexes that depend on the odds column types
DROP INDEX IF EXISTS uq_devigged_odds_snapshot;
DROP INDEX IF EXISTS uq_ev_bets_snapshot;

-- Convert American odds (integer) to decimal odds (double precision)
ALTER TABLE devigged_odds
    ALTER COLUMN odds_a TYPE DOUBLE PRECISION
        USING (
            CASE
                WHEN odds_a = 0 THEN 1.0
                WHEN odds_a > 0 THEN 1.0 + (odds_a::DOUBLE PRECISION / 100.0)
                ELSE 1.0 + (100.0 / ABS(odds_a::DOUBLE PRECISION))
            END
        );

ALTER TABLE devigged_odds
    ALTER COLUMN odds_b TYPE DOUBLE PRECISION
        USING (
            CASE
                WHEN odds_b = 0 THEN 1.0
                WHEN odds_b > 0 THEN 1.0 + (odds_b::DOUBLE PRECISION / 100.0)
                ELSE 1.0 + (100.0 / ABS(odds_b::DOUBLE PRECISION))
            END
        );

ALTER TABLE ev_bets
    ALTER COLUMN odds TYPE DOUBLE PRECISION
        USING (
            CASE
                WHEN odds = 0 THEN 1.0
                WHEN odds > 0 THEN 1.0 + (odds::DOUBLE PRECISION / 100.0)
                ELSE 1.0 + (100.0 / ABS(odds::DOUBLE PRECISION))
            END
        );

-- Restore NOT NULL constraints (original schema enforced NOT NULL)
ALTER TABLE devigged_odds
    ALTER COLUMN odds_a SET NOT NULL,
    ALTER COLUMN odds_b SET NOT NULL;

ALTER TABLE ev_bets
    ALTER COLUMN odds SET NOT NULL;

-- Recreate unique indexes using the new decimal columns
CREATE UNIQUE INDEX IF NOT EXISTS uq_devigged_odds_snapshot
ON devigged_odds (pipeline_match_id, bookmaker, market, outcome_a, outcome_b, odds_a, odds_b, source_updated_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ev_bets_snapshot
ON ev_bets (pipeline_match_id, bookmaker, market, selection, odds, stake, true_probability, source_updated_at);
