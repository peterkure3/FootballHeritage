#!/usr/bin/env python3
"""
Script to standardize sport types in the database.

This script will update all sport types to use consistent values:
- FOOTBALL (for all football/soccer events)
- BASKETBALL (for all basketball events)
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a connection to the database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)

def standardize_sport_types():
    """Standardize sport types in the database."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # First, log the current distribution of sport types
        logger.info("Current sport type distribution:")
        cur.execute("""
            SELECT sport, COUNT(*) as count 
            FROM events 
            GROUP BY sport 
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            logger.info(f"  {row['sport']}: {row['count']}")
        
        # Update all sport types to be consistent
        logger.info("\nStandardizing sport types...")
        
        # Update all variations of football/soccer to FOOTBALL
        cur.execute("""
            UPDATE events 
            SET sport = 'FOOTBALL' 
            WHERE LOWER(sport) IN ('football', 'soccer', 'soccer ', 'soccer  ')
        """)
        football_updates = cur.rowcount
        logger.info(f"  Updated {football_updates} records to FOOTBALL")
        
        # Update all variations of basketball to BASKETBALL
        cur.execute("""
            UPDATE events 
            SET sport = 'BASKETBALL' 
            WHERE LOWER(sport) IN ('basketball', 'basketball ', 'basketball  ')
        """)
        basketball_updates = cur.rowcount
        logger.info(f"  Updated {basketball_updates} records to BASKETBALL")
        
        # Commit the changes
        conn.commit()
        
        # Log the new distribution
        logger.info("\nNew sport type distribution:")
        cur.execute("""
            SELECT sport, COUNT(*) as count 
            FROM events 
            GROUP BY sport 
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            logger.info(f"  {row['sport']}: {row['count']}")
            
        logger.info("\nSport type standardization complete!")
        
    except Exception as e:
        logger.error(f"Error standardizing sport types: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Verify required environment variables
    required_vars = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please set these variables in your .env file or environment.")
        sys.exit(1)
    
    # Run the standardization
    standardize_sport_types()
