"""
Transform and load football pipeline data into Football Heritage events table.
Maps matches + odds → events with proper schema.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import uuid

# Database configuration
DB_USER = "postgres"
DB_PASSWORD = "jumpman13"  # Update with your password
DB_HOST = "localhost"
DB_PORT = "5432"

# Source: Your pipeline database
SOURCE_DB = "football_betting"
SOURCE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{SOURCE_DB}"

# Target: Football Heritage database
TARGET_DB = "football_heritage"
TARGET_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB}"


def transform_and_load():
    """Transform pipeline data and load into events table."""
    
    print("🚀 Starting data transformation and load...")
    print(f"Source: {SOURCE_DB}")
    print(f"Target: {TARGET_DB}")
    print("="*80)
    
    try:
        source_engine = create_engine(SOURCE_URI)
        target_engine = create_engine(TARGET_URI)
        
        # Step 1: Load matches and odds with JOIN
        print("\n📊 Loading matches and odds from pipeline...")
        
        query = """
        SELECT 
            m.match_id,
            m.competition,
            m.season,
            m.date,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.result,
            m.status,
            o.home_win as moneyline_home,
            o.away_win as moneyline_away,
            o.draw as draw_odds,
            o.bookmaker
        FROM matches m
        LEFT JOIN odds o ON m.match_id = o.match_id
        WHERE m.date IS NOT NULL
        ORDER BY m.date DESC
        """
        
        df = pd.read_sql(query, source_engine)
        print(f"✓ Loaded {len(df)} matches from pipeline")
        
        if len(df) == 0:
            print("⚠️  No data to load. Exiting.")
            return
        
        # Step 2: Transform to events schema
        print("\n🔄 Transforming data to events schema...")
        
        events_data = []
        
        for _, row in df.iterrows():
            # Map status
            status_map = {
                'scheduled': 'UPCOMING',
                'finished': 'FINISHED',
                'live': 'LIVE',
                'postponed': 'UPCOMING',
                'cancelled': 'CANCELLED'
            }
            status = status_map.get(row['status'].lower() if pd.notna(row['status']) else '', 'UPCOMING')
            
            event = {
                'id': str(uuid.uuid4()),
                'sport': 'SOCCER',
                'league': row['competition'] if pd.notna(row['competition']) else 'Unknown',
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'event_date': row['date'],
                'status': status,
                'home_score': int(row['home_score']) if pd.notna(row['home_score']) else None,
                'away_score': int(row['away_score']) if pd.notna(row['away_score']) else None,
                'moneyline_home': float(row['moneyline_home']) if pd.notna(row['moneyline_home']) else None,
                'moneyline_away': float(row['moneyline_away']) if pd.notna(row['moneyline_away']) else None,
                'point_spread': None,  # Not in your pipeline
                'spread_home_odds': None,
                'spread_away_odds': None,
                'total_points': None,
                'over_odds': None,
                'under_odds': None,
                'external_id': str(row['match_id']),
                'external_source': 'football_pipeline',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            events_data.append(event)
        
        events_df = pd.DataFrame(events_data)
        print(f"✓ Transformed {len(events_df)} events")
        
        # Step 3: Load into events table
        print("\n💾 Loading data into events table...")
        
        # Check for duplicates
        with target_engine.connect() as conn:
            existing = conn.execute(text(
                "SELECT external_id FROM events WHERE external_source = 'football_pipeline'"
            )).fetchall()
            existing_ids = {row[0] for row in existing}
        
        # Filter out duplicates
        new_events = events_df[~events_df['external_id'].isin(existing_ids)]
        
        if len(new_events) == 0:
            print("⚠️  All events already exist in database. No new data to load.")
            print(f"   Existing events: {len(existing_ids)}")
            return
        
        print(f"   New events to insert: {len(new_events)}")
        print(f"   Skipping duplicates: {len(events_df) - len(new_events)}")
        
        # Insert in batches
        batch_size = 100
        inserted = 0
        
        for i in range(0, len(new_events), batch_size):
            batch = new_events.iloc[i:i+batch_size]
            batch.to_sql(
                'events',
                target_engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            inserted += len(batch)
            print(f"   Inserted {inserted}/{len(new_events)} events...")
        
        print(f"\n✓ Successfully loaded {inserted} new events!")
        
        # Step 4: Summary
        print("\n" + "="*80)
        print("LOAD SUMMARY")
        print("="*80)
        
        with target_engine.connect() as conn:
            total_events = conn.execute(text(
                "SELECT COUNT(*) FROM events WHERE external_source = 'football_pipeline'"
            )).fetchone()[0]
            
            upcoming = conn.execute(text(
                "SELECT COUNT(*) FROM events WHERE external_source = 'football_pipeline' AND status = 'UPCOMING'"
            )).fetchone()[0]
            
            finished = conn.execute(text(
                "SELECT COUNT(*) FROM events WHERE external_source = 'football_pipeline' AND status = 'FINISHED'"
            )).fetchone()[0]
            
            print(f"Total pipeline events: {total_events:,}")
            print(f"  Upcoming: {upcoming:,}")
            print(f"  Finished: {finished:,}")
            print(f"  New this run: {inserted:,}")
        
        print("="*80)
        print("✓ Load completed successfully!")
        print("="*80)
        
        # Show sample
        print("\n📋 Sample loaded events:")
        with target_engine.connect() as conn:
            sample = conn.execute(text("""
                SELECT league, home_team, away_team, event_date, status
                FROM events 
                WHERE external_source = 'football_pipeline'
                ORDER BY event_date DESC
                LIMIT 5
            """)).fetchall()
            
            for row in sample:
                print(f"  • {row[0]}: {row[1]} vs {row[2]} ({row[4]}) - {row[3]}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    transform_and_load()
