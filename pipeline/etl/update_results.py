"""
Update match results for completed games.
Fetches final scores from football-data.org and updates the database.
Run this periodically (e.g., daily) to keep results current.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from sqlalchemy import create_engine, text

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import (
    FOOTBALL_DATA_ORG_API_KEY,
    FOOTBALL_DATA_ORG_BASE_URL,
    TRACKED_COMPETITIONS,
    API_TIMEOUT,
    API_RETRY_ATTEMPTS,
    API_RETRY_BACKOFF_FACTOR,
    LOG_LEVEL,
    DATABASE_URI,
)
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


def get_db_connection():
    """Get database connection using config."""
    return create_engine(DATABASE_URI)


def fetch_finished_matches(competition_code: str, days_back: int = 7) -> list:
    """
    Fetch finished matches from football-data.org.
    
    Args:
        competition_code: Competition code (e.g., 'PL', 'CL')
        days_back: Number of days to look back
        
    Returns:
        List of finished matches with scores
    """
    headers = {
        "X-Auth-Token": FOOTBALL_DATA_ORG_API_KEY,
        "Content-Type": "application/json"
    }
    
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    
    url = f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions/{competition_code}/matches"
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "status": "FINISHED"
    }
    
    for attempt in range(1, API_RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return data.get("matches", [])
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < API_RETRY_ATTEMPTS:
                wait_time = API_RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(f"Attempt {attempt}/{API_RETRY_ATTEMPTS} failed for {competition_code}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch matches for {competition_code} after {API_RETRY_ATTEMPTS} attempts: {e}")
                return []
        except requests.RequestException as e:
            logger.error(f"Failed to fetch matches for {competition_code}: {e}")
            return []
    
    return []


def update_match_result(db, match_data: dict) -> bool:
    """
    Update a single match result in the database.
    
    Args:
        db: Database engine
        match_data: Match data from API
        
    Returns:
        True if updated, False otherwise
    """
    match_id = match_data.get("id")
    home_team = match_data.get("homeTeam", {}).get("name")
    away_team = match_data.get("awayTeam", {}).get("name")
    
    score = match_data.get("score", {})
    full_time = score.get("fullTime", {})
    home_score = full_time.get("home")
    away_score = full_time.get("away")
    
    if home_score is None or away_score is None:
        logger.debug(f"No score for match {match_id}")
        return False
    
    # Determine result
    if home_score > away_score:
        result = "home_win"
    elif home_score < away_score:
        result = "away_win"
    else:
        result = "draw"
    
    # Update by match_id first, then try by team names
    update_query = text("""
        UPDATE matches 
        SET home_score = :home_score,
            away_score = :away_score,
            result = :result,
            status = 'FINISHED',
            updated_at = NOW()
        WHERE match_id = :match_id
          AND (result IS NULL OR home_score IS NULL)
        RETURNING match_id
    """)
    
    with db.connect() as conn:
        result_row = conn.execute(update_query, {
            "match_id": match_id,
            "home_score": home_score,
            "away_score": away_score,
            "result": result,
        }).fetchone()
        conn.commit()
        
        if result_row:
            logger.info(f"Updated match {match_id}: {home_team} {home_score}-{away_score} {away_team}")
            return True
    
    # Try matching by team names if match_id didn't work
    update_by_teams = text("""
        UPDATE matches 
        SET home_score = :home_score,
            away_score = :away_score,
            result = :result,
            status = 'FINISHED',
            updated_at = NOW()
        WHERE home_team = :home_team
          AND away_team = :away_team
          AND CAST(date AS DATE) = CAST(:match_date AS DATE)
          AND (result IS NULL OR home_score IS NULL)
        RETURNING match_id
    """)
    
    match_date = match_data.get("utcDate", "")[:10]  # Get date part only
    
    with db.connect() as conn:
        result_row = conn.execute(update_by_teams, {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": match_date,
            "home_score": home_score,
            "away_score": away_score,
            "result": result,
        }).fetchone()
        conn.commit()
        
        if result_row:
            logger.info(f"Updated match by teams: {home_team} {home_score}-{away_score} {away_team}")
            return True
    
    return False


def update_all_results(days_back: int = 7):
    """
    Update results for all tracked competitions.
    
    Args:
        days_back: Number of days to look back for finished matches
    """
    db = get_db_connection()
    total_updated = 0
    
    for comp_code in TRACKED_COMPETITIONS:
        logger.info(f"Fetching finished matches for {comp_code}...")
        matches = fetch_finished_matches(comp_code, days_back)
        logger.info(f"Found {len(matches)} finished matches for {comp_code}")
        
        updated = 0
        for match in matches:
            if update_match_result(db, match):
                updated += 1
        
        logger.info(f"Updated {updated} matches for {comp_code}")
        total_updated += updated
    
    logger.info(f"Total matches updated: {total_updated}")
    return total_updated


def get_pending_results_count():
    """Get count of matches without results."""
    db = get_db_connection()
    
    query = text("""
        SELECT COUNT(*) 
        FROM matches m
        JOIN predictions p ON m.match_id = p.match_id
        WHERE m.result IS NULL
          AND m.date < NOW()
    """)
    
    with db.connect() as conn:
        count = conn.execute(query).scalar()
    
    return count or 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update match results from API")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--check", action="store_true", help="Only check pending count")
    args = parser.parse_args()
    
    if args.check:
        pending = get_pending_results_count()
        print(f"Matches with predictions but no results: {pending}")
    else:
        print(f"Updating results for last {args.days} days...")
        updated = update_all_results(args.days)
        print(f"Done! Updated {updated} matches.")
        
        pending = get_pending_results_count()
        print(f"Remaining matches with predictions but no results: {pending}")
