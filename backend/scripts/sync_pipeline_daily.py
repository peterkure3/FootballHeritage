"""
Daily sync script: Load new pipeline matches into Football Heritage events.
Run this via cron/scheduler to keep events table updated.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import uuid

DB_USER = "postgres"
DB_PASSWORD = "jumpman13"
DB_HOST = "localhost"
DB_PORT = "5432"

SOURCE_DB = "football_betting"
SOURCE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{SOURCE_DB}"

TARGET_DB = "football_heritage"
TARGET_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB}"


def sync_new_matches():
    """Sync only new/updated matches from last 7 days."""
    
    print(f"🔄 Syncing pipeline matches... {datetime.now()}")
    
    try:
        source_engine = create_engine(SOURCE_URI)
        target_engine = create_engine(TARGET_URI)
        
        # Get matches from last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        
        with source_engine.connect() as source_conn:
            # Get new/updated matches
            matches = source_conn.execute(text("""
                SELECT 
                    m.match_id,
                    m.competition,
                    m.date,
                    m.home_team,
                    m.away_team,
                    m.home_score,
                    m.away_score,
                    m.status,
                    o.home_win,
                    o.away_win
                FROM matches m
                LEFT JOIN odds o ON m.match_id = o.match_id
                WHERE m.date >= :cutoff_date
                ORDER BY m.date DESC
            """), {"cutoff_date": cutoff_date}).fetchall()
        
        if not matches:
            print("✓ No new matches to sync")
            return
        
        print(f"📊 Found {len(matches)} matches from last 7 days")
        
        # Get existing external_ids
        with target_engine.connect() as target_conn:
            existing = target_conn.execute(text("""
                SELECT external_id FROM events 
                WHERE external_source = 'football_pipeline'
            """)).fetchall()
            existing_ids = {row[0] for row in existing}
        
        # Insert new matches
        new_count = 0
        updated_count = 0
        
        with target_engine.begin() as target_conn:
            for match in matches:
                match_id_str = str(match[0])
                
                # Status mapping
                status_map = {
                    'scheduled': 'UPCOMING',
                    'finished': 'FINISHED',
                    'live': 'LIVE',
                    'postponed': 'UPCOMING',
                    'cancelled': 'CANCELLED'
                }
                status = status_map.get(match[7].lower() if match[7] else '', 'UPCOMING')
                
                if match_id_str in existing_ids:
                    # Update existing event (scores, status, odds)
                    target_conn.execute(text("""
                        UPDATE events SET
                            status = :status,
                            home_score = :home_score,
                            away_score = :away_score,
                            moneyline_home = :ml_home,
                            moneyline_away = :ml_away,
                            updated_at = :updated_at
                        WHERE external_id = :external_id
                        AND external_source = 'football_pipeline'
                    """), {
                        "status": status,
                        "home_score": match[5],
                        "away_score": match[6],
                        "ml_home": match[8],
                        "ml_away": match[9],
                        "updated_at": datetime.now(),
                        "external_id": match_id_str
                    })
                    updated_count += 1
                else:
                    # Insert new event
                    target_conn.execute(text("""
                        INSERT INTO events (
                            id, sport, league, home_team, away_team, event_date,
                            status, home_score, away_score, moneyline_home, moneyline_away,
                            external_id, external_source, created_at, updated_at
                        ) VALUES (
                            :id, :sport, :league, :home_team, :away_team, :event_date,
                            :status, :home_score, :away_score, :ml_home, :ml_away,
                            :external_id, :external_source, :created_at, :updated_at
                        )
                    """), {
                        "id": str(uuid.uuid4()),
                        "sport": "SOCCER",
                        "league": match[1] or "Unknown",
                        "home_team": match[3],
                        "away_team": match[4],
                        "event_date": match[2],
                        "status": status,
                        "home_score": match[5],
                        "away_score": match[6],
                        "ml_home": match[8],
                        "ml_away": match[9],
                        "external_id": match_id_str,
                        "external_source": "football_pipeline",
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    })
                    new_count += 1
        
        print(f"✓ Sync complete:")
        print(f"  • New events: {new_count}")
        print(f"  • Updated events: {updated_count}")
        
    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    sync_new_matches()
