"""
Verify the football_heritage database after migration.
Quick script to check if data was copied correctly.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from sqlalchemy import create_engine, text
from heritage_config import DATABASE_URI, get_connection_info


def verify_database():
    """Verify the heritage database."""
    print("="*80)
    print("FOOTBALL HERITAGE DATABASE VERIFICATION")
    print("="*80)
    
    # Show connection info
    info = get_connection_info()
    print(f"\nConnecting to: {info['uri']}")
    
    try:
        engine = create_engine(DATABASE_URI)
        
        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            print("✓ Connection successful")
            
            # Check tables exist
            print("\n" + "-"*80)
            print("TABLES")
            print("-"*80)
            
            tables = ['matches', 'odds', 'predictions']
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    count = result[0]
                    print(f"✓ {table:15} {count:,} records")
                except Exception as e:
                    print(f"✗ {table:15} Error: {str(e)}")
            
            # Get sample data
            print("\n" + "-"*80)
            print("SAMPLE MATCHES")
            print("-"*80)
            
            matches = pd.read_sql("""
                SELECT 
                    match_id,
                    home_team,
                    away_team,
                    home_score,
                    away_score,
                    result,
                    date
                FROM matches
                ORDER BY date DESC
                LIMIT 5
            """, conn)
            
            if len(matches) > 0:
                for _, match in matches.iterrows():
                    score = f"{match['home_score']}-{match['away_score']}" if pd.notna(match['home_score']) else "vs"
                    print(f"{match['match_id']:6} | {match['home_team']:25} {score:5} {match['away_team']:25} | {match['result'] or 'TBD'}")
            else:
                print("No matches found")
            
            # Get predictions
            print("\n" + "-"*80)
            print("SAMPLE PREDICTIONS")
            print("-"*80)
            
            predictions = pd.read_sql("""
                SELECT 
                    p.match_id,
                    m.home_team,
                    m.away_team,
                    p.winner,
                    p.home_prob,
                    p.draw_prob,
                    p.away_prob
                FROM predictions p
                JOIN matches m ON p.match_id = m.match_id
                LIMIT 5
            """, conn)
            
            if len(predictions) > 0:
                for _, pred in predictions.iterrows():
                    print(f"{pred['match_id']:6} | {pred['home_team']:20} vs {pred['away_team']:20}")
                    print(f"         Predicted: {pred['winner']:10} (H:{pred['home_prob']*100:.1f}% D:{pred['draw_prob']*100:.1f}% A:{pred['away_prob']*100:.1f}%)")
            else:
                print("No predictions found")
            
            # Statistics
            print("\n" + "-"*80)
            print("STATISTICS")
            print("-"*80)
            
            stats = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT competition) as competitions,
                    COUNT(DISTINCT home_team) + COUNT(DISTINCT away_team) as teams,
                    MIN(date) as earliest_match,
                    MAX(date) as latest_match
                FROM matches
            """)).fetchone()
            
            print(f"Competitions:    {stats[0] or 0}")
            print(f"Unique Teams:    {stats[1] or 0}")
            print(f"Date Range:      {stats[2]} to {stats[3]}")
            
            # Check data quality
            print("\n" + "-"*80)
            print("DATA QUALITY")
            print("-"*80)
            
            quality = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN home_score IS NULL THEN 1 END) as missing_scores,
                    COUNT(CASE WHEN result IS NULL THEN 1 END) as missing_results,
                    COUNT(CASE WHEN competition IS NULL THEN 1 END) as missing_competition
                FROM matches
            """)).fetchone()
            
            print(f"Total Matches:        {quality[0]:,}")
            print(f"Missing Scores:       {quality[1]:,}")
            print(f"Missing Results:      {quality[2]:,}")
            print(f"Missing Competition:  {quality[3]:,}")
            
            # Foreign key integrity
            print("\n" + "-"*80)
            print("REFERENTIAL INTEGRITY")
            print("-"*80)
            
            orphaned_odds = conn.execute(text("""
                SELECT COUNT(*) 
                FROM odds o
                LEFT JOIN matches m ON o.match_id = m.match_id
                WHERE m.match_id IS NULL
            """)).fetchone()[0]
            
            orphaned_predictions = conn.execute(text("""
                SELECT COUNT(*) 
                FROM predictions p
                LEFT JOIN matches m ON p.match_id = m.match_id
                WHERE m.match_id IS NULL
            """)).fetchone()[0]
            
            print(f"Orphaned Odds:        {orphaned_odds} {'✓' if orphaned_odds == 0 else '✗'}")
            print(f"Orphaned Predictions: {orphaned_predictions} {'✓' if orphaned_predictions == 0 else '✗'}")
            
            print("\n" + "="*80)
            if orphaned_odds == 0 and orphaned_predictions == 0:
                print("✓ DATABASE VERIFICATION PASSED")
            else:
                print("⚠ DATABASE HAS INTEGRITY ISSUES")
            print("="*80)
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'football_heritage' exists")
        print("3. Credentials in .env are correct")
        print("\nRun migration first:")
        print("  python load_to_heritage_db.py")


if __name__ == "__main__":
    verify_database()
