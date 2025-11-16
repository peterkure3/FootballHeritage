-- Migration: Add NBA Cup Support
-- Description: Extend events table to support NBA Cup league
-- Date: 2025-11-04
-- Author: System
-- Note: This schema stores odds directly in events table (no separate odds table)

-- ============================================
-- STEP 1: Add league column if it doesn't exist
-- ============================================

-- Check if league column exists in events table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'events' 
        AND column_name = 'league'
    ) THEN
        ALTER TABLE events 
        ADD COLUMN league VARCHAR(50);
        
        RAISE NOTICE 'Added league column to events table';
    ELSE
        RAISE NOTICE 'League column already exists in events table';
    END IF;
END $$;

-- ============================================
-- STEP 2: Update existing data with default leagues
-- ============================================

-- Set default league for existing basketball events
UPDATE events 
SET league = 'nba' 
WHERE sport = 'basketball' 
AND league IS NULL;

-- Set default league for existing football events
UPDATE events 
SET league = 'nfl' 
WHERE sport = 'football' 
AND league IS NULL;

-- Set default league for existing soccer events
UPDATE events 
SET league = 'premier_league' 
WHERE sport = 'soccer' 
AND league IS NULL;

-- ============================================
-- STEP 3: Add indexes for better query performance
-- ============================================

-- Index on sport + league for fast filtering
CREATE INDEX IF NOT EXISTS idx_events_sport_league 
ON events(sport, league);

-- Index on league + event_date for upcoming games queries
-- Note: Removed WHERE clause with NOW() as it's not immutable
-- The query will still be fast with the index on (league, event_date)
CREATE INDEX IF NOT EXISTS idx_events_league_date 
ON events(league, event_date);

-- ============================================
-- STEP 4: Add constraints and comments
-- ============================================

-- Add check constraint for valid leagues
-- Note: Constraint is optional - commented out to allow flexibility
-- Uncomment if you want to enforce specific league values
/*
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'events_league_check'
    ) THEN
        ALTER TABLE events 
        ADD CONSTRAINT events_league_check 
        CHECK (league IN (
            'nba', 'nba_cup', 'wnba',
            'nfl', 'ncaa_football',
            'premier_league', 'la_liga', 'bundesliga', 'serie_a', 'ligue_1',
            'champions_league', 'europa_league', 'world_cup',
            'ncaa_basketball'
        ));
        
        RAISE NOTICE 'Added league check constraint to events table';
    END IF;
END $$;
*/

-- Skipping league check constraint to allow any league value
DO $$
BEGIN
    RAISE NOTICE 'Skipped league check constraint (allows any league value)';
END $$;

-- Add comments for documentation
COMMENT ON COLUMN events.league IS 'League or competition name (e.g., nba, nba_cup, nfl, premier_league)';

-- ============================================
-- STEP 5: Create view for NBA Cup games
-- ============================================

-- Drop view if exists
DROP VIEW IF EXISTS nba_cup_upcoming_games;

-- Create view for upcoming NBA Cup games with odds (odds stored in events table)
CREATE VIEW nba_cup_upcoming_games AS
SELECT 
    id,
    sport,
    league,
    home_team,
    away_team,
    event_date,
    status,
    home_score,
    away_score,
    moneyline_home,
    moneyline_away,
    point_spread,
    spread_home_odds,
    spread_away_odds,
    total_points,
    over_odds,
    under_odds,
    created_at,
    updated_at
FROM events
WHERE league = 'nba_cup'
AND event_date > NOW()
ORDER BY event_date ASC;

COMMENT ON VIEW nba_cup_upcoming_games IS 'Upcoming NBA Cup games with betting odds';

-- ============================================
-- STEP 6: Insert sample NBA Cup data (for testing)
-- ============================================

-- Only insert if no NBA Cup data exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM events WHERE league = 'nba_cup') THEN
        -- Insert sample NBA Cup games with odds (odds stored in events table)
        INSERT INTO events (
            sport, league, home_team, away_team, 
            event_date, status,
            moneyline_home, moneyline_away,
            point_spread, spread_home_odds, spread_away_odds,
            total_points, over_odds, under_odds,
            created_at, updated_at
        ) VALUES
        (
            'basketball',
            'nba_cup',
            'Los Angeles Lakers',
            'Boston Celtics',
            NOW() + INTERVAL '7 days',
            'UPCOMING',
            1.85,  -- Lakers moneyline
            2.10,  -- Celtics moneyline
            -3.5,  -- Point spread (Lakers favored by 3.5)
            1.91,  -- Lakers spread odds
            1.91,  -- Celtics spread odds
            215.5, -- Total points
            1.91,  -- Over odds
            1.91,  -- Under odds
            NOW(),
            NOW()
        ),
        (
            'basketball',
            'nba_cup',
            'Golden State Warriors',
            'Miami Heat',
            NOW() + INTERVAL '8 days',
            'UPCOMING',
            1.95,  -- Warriors moneyline
            1.95,  -- Heat moneyline
            -2.5,  -- Point spread (Warriors favored by 2.5)
            1.91,  -- Warriors spread odds
            1.91,  -- Heat spread odds
            220.5, -- Total points
            1.91,  -- Over odds
            1.91,  -- Under odds
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Inserted sample NBA Cup data';
    ELSE
        RAISE NOTICE 'NBA Cup data already exists, skipping sample insert';
    END IF;
END $$;

-- ============================================
-- STEP 7: Grant permissions
-- ============================================

-- Grant SELECT on view to application user
GRANT SELECT ON nba_cup_upcoming_games TO PUBLIC;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify migration success
SELECT 
    'Migration Complete' as status,
    COUNT(*) as nba_cup_events
FROM events 
WHERE league = 'nba_cup';

-- Show sample NBA Cup data
SELECT 
    home_team,
    away_team,
    event_date,
    status,
    moneyline_home,
    moneyline_away,
    point_spread,
    total_points
FROM nba_cup_upcoming_games
LIMIT 5;

-- ============================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================

/*
-- To rollback this migration, run:

-- Remove sample data
DELETE FROM events WHERE league = 'nba_cup';

-- Drop view
DROP VIEW IF EXISTS nba_cup_upcoming_games;

-- Drop indexes
DROP INDEX IF EXISTS idx_events_sport_league;
DROP INDEX IF EXISTS idx_events_league_date;

-- Remove constraint
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_league_check;

-- Remove league column (CAUTION: This will delete all league data)
-- ALTER TABLE events DROP COLUMN IF EXISTS league;
*/
