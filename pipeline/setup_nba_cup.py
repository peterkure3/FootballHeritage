"""
NBA Cup Setup Script
====================

Quick setup script to initialize NBA Cup support.
Runs all necessary steps in correct order.

Usage:
    python setup_nba_cup.py
"""

import sys
import subprocess
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from etl.fetch_nba_cup_data import NbaCupFetcher
from etl.transform_nba_cup import NbaCupTransformer
from etl.utils import setup_logger, ensure_dir
from config import LOG_LEVEL, THE_ODDS_API_DIR

logger = setup_logger(__name__, LOG_LEVEL)


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step_num, text):
    """Print step number and description."""
    print(f"\n[{step_num}/5] {text}")
    print("-" * 60)


def check_database_connection():
    """Check if database is accessible."""
    try:
        import psycopg2
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def run_migration():
    """Run database migration."""
    print_step(1, "Running Database Migration")
    
    migration_file = Path(__file__).parent.parent / "backend" / "migrations" / "add_nba_cup_support.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    try:
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        import psycopg2
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"✗ Migration failed: {e}")
        print("\nTry running manually:")
        print(f"  psql -U postgres -d {DB_NAME} -f {migration_file}")
        return False


def fetch_nba_cup_data():
    """Fetch NBA Cup data from APIs."""
    print_step(2, "Fetching NBA Cup Data")
    
    try:
        # Ensure output directory exists
        nba_cup_dir = THE_ODDS_API_DIR / "nba_cup"
        ensure_dir(nba_cup_dir)
        
        # Initialize fetcher
        fetcher = NbaCupFetcher()
        
        # Fetch current season data
        current_season = 2024
        data = fetcher.fetch_all_nba_cup_data(season=current_season)
        
        # Save to JSON
        from etl.utils import save_json, get_timestamp_str
        timestamp = get_timestamp_str()
        filename = f"nba_cup_{current_season}_{timestamp}.json"
        filepath = nba_cup_dir / filename
        
        save_json(data, filepath)
        
        games_count = len(data.get("games", {}).get("data", []))
        odds_count = len(data.get("odds", []))
        
        print(f"✓ Fetched {games_count} games and {odds_count} odds records")
        print(f"✓ Saved to: {filepath}")
        
        return filepath
        
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        print(f"✗ Data fetch failed: {e}")
        return None


def transform_data(data_file):
    """Transform NBA Cup data."""
    print_step(3, "Transforming NBA Cup Data")
    
    try:
        # Load data
        with open(data_file, 'r') as f:
            raw_data = json.load(f)
        
        # Transform
        transformer = NbaCupTransformer()
        transformed = transformer.transform_all(raw_data)
        
        events_count = len(transformed['events'])
        odds_count = len(transformed['odds'])
        
        print(f"✓ Transformed {events_count} events")
        print(f"✓ Transformed {odds_count} odds records")
        
        return transformed
        
    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        print(f"✗ Transformation failed: {e}")
        return None


def load_to_database(transformed_data):
    """Load transformed data to database."""
    print_step(4, "Loading Data to Database")
    
    try:
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        import psycopg2
        from psycopg2.extras import execute_values
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Load events
        events_df = transformed_data['events']
        if not events_df.empty:
            # Delete existing NBA Cup events for this season
            cursor.execute("DELETE FROM events WHERE league = 'nba_cup' AND season = 2024")
            
            # Insert new events
            events_values = [
                (
                    row['external_id'],
                    row['sport'],
                    row['league'],
                    row['home_team'],
                    row['away_team'],
                    row['event_date'],
                    row['status'],
                    row.get('home_score'),
                    row.get('away_score'),
                    row.get('season'),
                    row['created_at'],
                    row['updated_at']
                )
                for _, row in events_df.iterrows()
            ]
            
            execute_values(
                cursor,
                """
                INSERT INTO events (
                    external_id, sport, league, home_team, away_team,
                    event_date, status, home_score, away_score, season,
                    created_at, updated_at
                ) VALUES %s
                ON CONFLICT (external_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    updated_at = EXCLUDED.updated_at
                """,
                events_values
            )
            
            print(f"✓ Loaded {len(events_values)} events")
        
        # Load odds
        odds_df = transformed_data['odds']
        if not odds_df.empty:
            # Delete existing NBA Cup odds
            cursor.execute("DELETE FROM odds WHERE league = 'nba_cup'")
            
            # Insert new odds
            odds_values = [
                (
                    row['external_id'],
                    row['sport'],
                    row['league'],
                    row['home_team'],
                    row['away_team'],
                    row['event_date'],
                    row['bookmaker'],
                    row.get('moneyline_home'),
                    row.get('moneyline_away'),
                    row.get('spread_home'),
                    row.get('spread_away'),
                    row.get('spread_odds_home'),
                    row.get('spread_odds_away'),
                    row.get('total'),
                    row.get('over_odds'),
                    row.get('under_odds'),
                    row['created_at'],
                    row['updated_at']
                )
                for _, row in odds_df.iterrows()
            ]
            
            execute_values(
                cursor,
                """
                INSERT INTO odds (
                    external_id, sport, league, home_team, away_team,
                    event_date, bookmaker,
                    moneyline_home, moneyline_away,
                    spread_home, spread_away, spread_odds_home, spread_odds_away,
                    total, over_odds, under_odds,
                    created_at, updated_at
                ) VALUES %s
                """,
                odds_values
            )
            
            print(f"✓ Loaded {len(odds_values)} odds records")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Database load failed: {e}")
        print(f"✗ Database load failed: {e}")
        return False


def verify_setup():
    """Verify NBA Cup setup."""
    print_step(5, "Verifying Setup")
    
    try:
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        import psycopg2
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Check events
        cursor.execute("SELECT COUNT(*) FROM events WHERE league = 'nba_cup'")
        events_count = cursor.fetchone()[0]
        
        # Check odds
        cursor.execute("SELECT COUNT(*) FROM odds WHERE league = 'nba_cup'")
        odds_count = cursor.fetchone()[0]
        
        # Check view
        cursor.execute("SELECT COUNT(*) FROM nba_cup_upcoming_games")
        upcoming_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✓ Events in database: {events_count}")
        print(f"✓ Odds records in database: {odds_count}")
        print(f"✓ Upcoming games: {upcoming_count}")
        
        if events_count > 0 and odds_count > 0:
            print("\n✅ NBA Cup setup completed successfully!")
            return True
        else:
            print("\n⚠️ Setup completed but no data found")
            return False
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        print(f"✗ Verification failed: {e}")
        return False


def main():
    """Main setup function."""
    print_header("NBA CUP SETUP")
    print("This script will set up NBA Cup support for your betting platform.")
    print("It will:")
    print("  1. Run database migration")
    print("  2. Fetch NBA Cup data from APIs")
    print("  3. Transform data to standard format")
    print("  4. Load data into database")
    print("  5. Verify setup")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    # Check database connection
    print("\nChecking database connection...")
    if not check_database_connection():
        print("✗ Cannot connect to database. Please check your configuration.")
        return False
    print("✓ Database connection successful")
    
    # Run migration
    if not run_migration():
        print("\n⚠️ Migration failed. You may need to run it manually.")
        print("See NBA_CUP_INTEGRATION_GUIDE.md for instructions.")
        return False
    
    # Fetch data
    data_file = fetch_nba_cup_data()
    if not data_file:
        print("\n✗ Data fetch failed. Check your API keys and internet connection.")
        return False
    
    # Transform data
    transformed = transform_data(data_file)
    if not transformed:
        print("\n✗ Data transformation failed.")
        return False
    
    # Load to database
    if not load_to_database(transformed):
        print("\n✗ Database load failed.")
        return False
    
    # Verify
    if not verify_setup():
        print("\n⚠️ Verification failed. Check database manually.")
        return False
    
    print_header("SETUP COMPLETE")
    print("NBA Cup support is now active!")
    print("\nNext steps:")
    print("  1. Rebuild Rust backend: cd backend && cargo build --release")
    print("  2. Start backend: cargo run --release")
    print("  3. Start frontend: cd frontend && npm run dev")
    print("  4. Navigate to /odds and select 'NBA Cup' from dropdown")
    print("\nFor detailed instructions, see NBA_CUP_INTEGRATION_GUIDE.md")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n✗ Setup failed: {e}")
        print("\nFor help, see NBA_CUP_INTEGRATION_GUIDE.md")
        sys.exit(1)
