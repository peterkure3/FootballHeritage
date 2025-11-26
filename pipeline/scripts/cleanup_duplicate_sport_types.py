"""
Clean up duplicate sport types in the backend database.
This script removes any non-standard sport type entries.
"""
import psycopg2
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_duplicate_sport_types():
    """Remove non-standard sport type entries from the database."""
    conn = None
    try:
        # Connect to the backend database
        logger.info("Connecting to backend database...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='football_heritage',
            user='postgres',
            password='jumpman13'
        )
        
        with conn.cursor() as cur:
            # First, check what we're going to delete
            cur.execute("""
                SELECT sport, COUNT(*) as count 
                FROM events 
                WHERE LOWER(sport) = 'basketball' AND sport != 'BASKETBALL'
                GROUP BY sport
            """)
            
            rows = cur.fetchall()
            if not rows:
                logger.info("No duplicate basketball sport types found.")
                return
                
            logger.info("Found the following non-standard basketball sport types:")
            for sport, count in rows:
                logger.info(f"  - {sport}: {count} records")
            
            # Delete the duplicate records
            cur.execute("""
                DELETE FROM events 
                WHERE LOWER(sport) = 'basketball' AND sport != 'BASKETBALL'
                RETURNING id, sport, home_team, away_team, event_date
            """)
            
            deleted_count = cur.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Successfully deleted {deleted_count} records with non-standard basketball sport types.")
                
                # Log the new counts
                cur.execute("""
                    SELECT sport, COUNT(*) as count 
                    FROM events 
                    WHERE LOWER(sport) = 'basketball' OR sport = 'BASKETBALL'
                    GROUP BY sport
                """)
                logger.info("Remaining basketball sport types:")
                for sport, count in cur.fetchall():
                    logger.info(f"  - {sport}: {count} records")
            else:
                logger.info("No records were deleted.")
                
    except Exception as e:
        logger.error(f"Error cleaning up sport types: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == "__main__":
    print("=" * 60)
    print("CLEANING UP DUPLICATE SPORT TYPES")
    print("=" * 60)
    clean_duplicate_sport_types()
