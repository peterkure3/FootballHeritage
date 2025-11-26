"""
Script to fix the case of sport names in the database.
Updates any lowercase 'basketball' entries to 'BASKETBALL'.
"""
import os
import psycopg2
from dotenv import load_dotenv

def fix_sport_case():
    """Fix the case of sport names in the database."""
    # Load environment variables
    load_dotenv()
    
    # Connect to the database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='football_heritage',
        user='postgres',
        password='jumpman13'
    )
    
    try:
        with conn.cursor() as cur:
            # Update events table
            cur.execute("""
                UPDATE events 
                SET sport = 'BASKETBALL'
                WHERE LOWER(sport) = 'basketball' AND sport != 'BASKETBALL'
                RETURNING id, sport
            """)
            updated_events = cur.rowcount
            
            print(f"Updated {updated_events} events with lowercase 'basketball' to 'BASKETBALL'")
            
            # Commit the changes
            conn.commit()
            
    except Exception as e:
        print(f"Error updating sport case: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Fixing sport case in database...")
    fix_sport_case()
    print("Done!")
