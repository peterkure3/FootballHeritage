"""
Sync pipeline data to backend database.
Transfers matches and odds from pipeline DB to backend's events table.
"""

import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import uuid

import psycopg2
from psycopg2.extras import execute_batch
from psycopg2.extensions import register_adapter
import logging

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_to_backend.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def decimal_to_american_odds(decimal_odds: float) -> int:
    """
    Convert decimal odds to American odds format.
    
    Args:
        decimal_odds: Decimal odds (e.g., 2.50)
    
    Returns:
        American odds (e.g., +150 or -125)
    """
    if decimal_odds >= 2.0:
        # Positive American odds
        return int((decimal_odds - 1) * 100)
    else:
        # Negative American odds
        return int(-100 / (decimal_odds - 1))


def standardize_sport_name(sport: str) -> str:
    """
    Standardize sport name to match frontend constants.
    
    Args:
        sport: Raw sport name from data source
        
    Returns:
        Standardized sport name (SOCCER, NFL, BASKETBALL, etc.)
    """
    if not sport:
        return 'SOCCER'  # Default to SOCCER if not specified
        
    sport_lower = sport.strip().lower()
    
    # Basketball variations
    if any(kw in sport_lower for kw in ['basketball', 'nba', 'wnba', 'euroleague', 'euro cup']):
        if 'nba_cup' in sport_lower or 'in-season' in sport_lower:
            return 'NBA_CUP'
        return 'BASKETBALL'
        
    # Football variations
    if any(kw in sport_lower for kw in ['football', 'soccer', 'premier league', 'la liga', 'bundesliga', 'serie a', 'champions league', 'europa league']):
        if any(kw in sport_lower for kw in ['nfl', 'ncaa football', 'college football', 'american football']):
            return 'NFL'
        return 'SOCCER'
        
    # Other sports
    sport_mapping = {
        'baseball': 'BASEBALL',
        'mlb': 'BASEBALL',
        'hockey': 'HOCKEY',
        'nhl': 'HOCKEY',
        'tennis': 'TENNIS',
        'golf': 'GOLF',
        'mma': 'MMA',
        'ufc': 'UFC',
        'boxing': 'BOXING',
        'esports': 'ESPORTS',
        'esports': 'ESPORTS'
    }
    
    return sport_mapping.get(sport_lower, 'SOCCER')  # Default to SOCCER if no match

def get_sport_from_competition(competition: str) -> str:
    """
    Determine sport type from competition name.
    
    Args:
        competition: Competition name
    
    Returns:
        Sport type in UPPERCASE (SOCCER, NFL, BASKETBALL, etc.)
    """
    if not competition:
        return 'SOCCER'  # Default to SOCCER if competition is empty
        
    return standardize_sport_name(competition)


def sync_matches_to_backend():
    """Main sync function."""
    logger.info("=" * 60)
    logger.info("STARTING PIPELINE → BACKEND SYNC")
    logger.info("=" * 60)
    
    # Database connections
    pipeline_conn = None
    backend_conn = None
    
    try:
        # Connect to pipeline database
        logger.info("Connecting to pipeline database...")
        pipeline_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='football_betting',
            user='postgres',
            password='jumpman13'
        )
        
        # Connect to backend database
        logger.info("Connecting to backend database...")
        backend_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='football_heritage',
            user='postgres',
            password='jumpman13'
        )
        
        pipeline_cur = pipeline_conn.cursor()
        backend_cur = backend_conn.cursor()
        
        # Fetch all matches from pipeline with odds
        logger.info("Fetching matches and odds from pipeline database...")
        
        # First, get football matches
        pipeline_cur.execute("""
            SELECT 
                m.match_id::TEXT as match_id,
                m.competition,
                m.season::TEXT as season,
                m.date,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.result,
                m.status,
                o.home_win,
                o.draw,
                o.away_win,
                'SOCCER' as sport_type  -- Standardized sport type
            FROM matches m
            LEFT JOIN odds o ON m.match_id = o.match_id
            WHERE m.match_id IS NOT NULL
                AND m.date IS NOT NULL
                AND m.home_team IS NOT NULL
                AND m.away_team IS NOT NULL
            
            UNION ALL
            
            -- Add NBA games
            SELECT 
                game_id::TEXT as match_id,
                sport_title as competition,
                EXTRACT(YEAR FROM commence_time)::TEXT as season,
                commence_time as date,
                home_team,
                away_team,
                home_score,
                away_score,
                CASE 
                    WHEN completed = true AND home_score > away_score THEN 'H'
                    WHEN completed = true AND away_score > home_score THEN 'A'
                    WHEN completed = true AND home_score = away_score THEN 'D'
                    ELSE NULL
                END as result,
                CASE 
                    WHEN completed = true THEN 'FINISHED'
                    ELSE 'SCHEDULED'
                END as status,
                NULL as home_win,  -- These would come from NBA odds if available
                NULL as draw,
                NULL as away_win,
                'BASKETBALL' as sport_type  -- Standardized sport type
            FROM nba_games
            WHERE commence_time IS NOT NULL
                AND home_team IS NOT NULL
                AND away_team IS NOT NULL
            
            ORDER BY date DESC
        """)
        
        matches = pipeline_cur.fetchall()
        logger.info(f"Found {len(matches)} matches to sync (including NBA games)")
        
        # Log count by sport type for debugging
        match_types = {}
        for match in matches:
            sport_type = match[13] if len(match) > 13 else 'unknown'
            match_types[sport_type] = match_types.get(sport_type, 0) + 1
        
        for sport_type, count in match_types.items():
            logger.info(f"  - {sport_type}: {count} matches")
        
        if not matches:
            logger.warning("No matches to sync")
            return
        
        # Prepare data for backend
        events_to_insert = []
        synced_count = 0
        skipped_count = 0
        
        for match in matches:
            (match_id, competition, season, date, home_team, away_team,
             home_score, away_score, result, status, home_win_odds,
             draw_odds, away_win_odds, sport_type) = match
            
            try:
                # Standardize the sport type to match frontend constants and ensure uppercase
                sport = standardize_sport_name(sport_type).upper()  # Force uppercase
                
                # Ensure sport is uppercase
                sport = sport.upper() if sport else 'SOCCER'
                
                # Map status
                status_map = {
                    'FINISHED': 'FINISHED',
                    'SCHEDULED': 'UPCOMING',
                    'LIVE': 'LIVE',
                    'POSTPONED': 'CANCELLED',
                    'CANCELLED': 'CANCELLED'
                }
                backend_status = status_map.get(status, 'UPCOMING')
                
                # Convert odds to American format
                moneyline_home = None
                moneyline_away = None
                
                if home_win_odds and away_win_odds:
                    try:
                        moneyline_home = decimal_to_american_odds(float(home_win_odds))
                        moneyline_away = decimal_to_american_odds(float(away_win_odds))
                    except (ValueError, ZeroDivisionError) as e:
                        logger.warning(f"Could not convert odds for match {match_id}: {e}")
                
                # Check if event already exists (by home_team, away_team, and date)
                backend_cur.execute("""
                    SELECT id FROM events 
                    WHERE home_team = %s 
                    AND away_team = %s 
                    AND event_date = %s
                """, (home_team, away_team, date))
                
                existing = backend_cur.fetchone()
                
                if existing:
                    # Update existing event
                    backend_cur.execute("""
                        UPDATE events SET
                            sport = %s,
                            league = %s,
                            status = %s,
                            home_score = %s,
                            away_score = %s,
                            moneyline_home = %s,
                            moneyline_away = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        sport,
                        competition,
                        backend_status,
                        home_score,
                        away_score,
                        moneyline_home,
                        moneyline_away,
                        existing[0]
                    ))
                    logger.debug(f"Updated event: {home_team} vs {away_team}")
                else:
                    # Insert new event
                    event_uuid = str(uuid.uuid4())  # Convert to string
                    backend_cur.execute("""
                        INSERT INTO events (
                            id, sport, league, home_team, away_team, event_date,
                            status, home_score, away_score, moneyline_home, moneyline_away,
                            created_at, updated_at
                        ) VALUES (
                            %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """, (
                        event_uuid,
                        sport,
                        competition,
                        home_team,
                        away_team,
                        date,
                        backend_status,
                        home_score,
                        away_score,
                        moneyline_home,
                        moneyline_away
                    ))
                    logger.debug(f"Inserted event: {home_team} vs {away_team}")
                
                # Commit after each successful insert/update
                backend_conn.commit()
                synced_count += 1
                
            except Exception as e:
                # Rollback this transaction and continue
                backend_conn.rollback()
                logger.error(f"Error processing match {match_id}: {e}")
                skipped_count += 1
                continue
        
        # Commit changes
        backend_conn.commit()
        
        logger.info("=" * 60)
        logger.info(f"✓ Sync completed successfully!")
        logger.info(f"  Total matches processed: {len(matches)}")
        logger.info(f"  Successfully synced: {synced_count}")
        logger.info(f"  Skipped (errors): {skipped_count}")
        logger.info("=" * 60)
        
        # Show summary
        backend_cur.execute("SELECT COUNT(*) FROM events")
        total_events = backend_cur.fetchone()[0]
        logger.info(f"Backend database now has {total_events} total events")
        
        backend_cur.execute("""
            SELECT sport, COUNT(*) 
            FROM events 
            GROUP BY sport 
            ORDER BY COUNT(*) DESC
        """)
        sport_counts = backend_cur.fetchall()
        logger.info("Events by sport:")
        for sport, count in sport_counts:
            logger.info(f"  {sport}: {count}")
        
        backend_cur.execute("""
            SELECT status, COUNT(*) 
            FROM events 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        """)
        status_counts = backend_cur.fetchall()
        logger.info("Events by status:")
        for status, count in status_counts:
            logger.info(f"  {status}: {count}")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        if backend_conn:
            backend_conn.rollback()
        sys.exit(1)
        
    finally:
        # Close connections
        if pipeline_conn:
            pipeline_conn.close()
        if backend_conn:
            backend_conn.close()
        logger.info("Database connections closed")


def main():
    """Main entry point."""
    try:
        sync_matches_to_backend()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
