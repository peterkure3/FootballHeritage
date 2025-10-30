"""
Enhanced data fetcher to get more historical data.
Fetches data across multiple seasons and competitions.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent))

import requests
from config import (
    FOOTBALL_DATA_ORG_API_KEY,
    FOOTBALL_DATA_ORG_BASE_URL,
    FOOTBALL_DATA_ORG_DIR,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    THE_ODDS_API_DIR,
    ODDS_API_SPORTS,
    LOG_LEVEL,
)
from etl.utils import setup_logger, save_json, ensure_dir, get_timestamp_str

logger = setup_logger(__name__, LOG_LEVEL)


def fetch_all_available_competitions():
    """Fetch all available competitions and their details."""
    logger.info("Fetching all available competitions...")
    
    headers = {
        "X-Auth-Token": FOOTBALL_DATA_ORG_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        competitions = data.get("competitions", [])
        
        logger.info(f"Found {len(competitions)} competitions")
        
        # Save competition list
        timestamp = get_timestamp_str("%Y%m%d_%H%M%S")
        ensure_dir(FOOTBALL_DATA_ORG_DIR)
        save_json(data, FOOTBALL_DATA_ORG_DIR / f"all_competitions_{timestamp}.json")
        
        # Display available competitions
        print("\n" + "="*80)
        print("AVAILABLE COMPETITIONS")
        print("="*80)
        for comp in competitions:
            print(f"ID: {comp.get('id'):5} | Code: {comp.get('code', 'N/A'):5} | {comp.get('name')}")
            print(f"       Area: {comp.get('area', {}).get('name')} | Type: {comp.get('type')}")
            print()
        
        return competitions
        
    except Exception as e:
        logger.error(f"Failed to fetch competitions: {str(e)}")
        return []


def fetch_matches_for_competition(comp_id, comp_name, date_from=None, date_to=None):
    """Fetch matches for a specific competition."""
    logger.info(f"Fetching matches for {comp_name} (ID: {comp_id})...")
    
    headers = {
        "X-Auth-Token": FOOTBALL_DATA_ORG_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions/{comp_id}/matches"
    params = {}
    
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        matches = data.get("matches", [])
        
        logger.info(f"✓ Fetched {len(matches)} matches for {comp_name}")
        
        # Save matches
        timestamp = get_timestamp_str("%Y%m%d_%H%M%S")
        filename = f"matches_{comp_id}_{comp_name.replace(' ', '_')}_{timestamp}.json"
        save_json(data, FOOTBALL_DATA_ORG_DIR / filename)
        
        return matches
        
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"⚠ {comp_name} not available on your API tier")
        elif e.response.status_code == 404:
            logger.warning(f"⚠ {comp_name} not found")
        else:
            logger.error(f"✗ Error fetching {comp_name}: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"✗ Exception fetching {comp_name}: {str(e)}")
        return []


def fetch_all_odds_for_sports():
    """Fetch odds for all configured sports."""
    logger.info("Fetching odds for all sports...")
    
    total_events = 0
    
    for sport in ODDS_API_SPORTS:
        logger.info(f"Fetching odds for {sport}...")
        
        try:
            response = requests.get(
                f"{THE_ODDS_API_BASE_URL}/sports/{sport}/odds",
                params={
                    "apiKey": THE_ODDS_API_KEY,
                    "regions": "uk,us,eu",
                    "markets": "h2h",
                    "oddsFormat": "decimal"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                events = response.json()
                logger.info(f"✓ {sport}: {len(events)} events")
                logger.info(f"  Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")
                
                # Save odds
                timestamp = get_timestamp_str("%Y%m%d_%H%M%S")
                filename = f"odds_{sport}_{timestamp}.json"
                ensure_dir(THE_ODDS_API_DIR)
                save_json({"sport": sport, "events": events, "fetched_at": timestamp}, 
                         THE_ODDS_API_DIR / filename)
                
                total_events += len(events)
            else:
                logger.warning(f"⚠ {sport}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"✗ Error fetching {sport}: {str(e)}")
    
    logger.info(f"Total events fetched: {total_events}")
    return total_events


def fetch_historical_data():
    """Fetch historical data for multiple time periods."""
    logger.info("Fetching historical data...")
    
    # Define time periods
    periods = [
        # Last 3 months
        {
            "name": "Last 3 months",
            "date_from": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "date_to": datetime.now().strftime("%Y-%m-%d")
        },
        # Last 6 months
        {
            "name": "3-6 months ago",
            "date_from": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"),
            "date_to": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        },
        # Last year
        {
            "name": "6-12 months ago",
            "date_from": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "date_to": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        },
    ]
    
    # Priority competitions (most likely to have data)
    priority_comps = [
        (2021, "Premier League"),
        (2014, "La Liga"),
        (2002, "Bundesliga"),
        (2019, "Serie A"),
        (2015, "Ligue 1"),
        (2001, "Champions League"),
    ]
    
    total_matches = 0
    
    for period in periods:
        print(f"\n{'='*80}")
        print(f"Fetching: {period['name']}")
        print(f"From: {period['date_from']} To: {period['date_to']}")
        print(f"{'='*80}\n")
        
        for comp_id, comp_name in priority_comps:
            matches = fetch_matches_for_competition(
                comp_id, 
                comp_name,
                period['date_from'],
                period['date_to']
            )
            total_matches += len(matches)
            
            # Small delay to avoid rate limiting
            import time
            time.sleep(1)
    
    logger.info(f"Total historical matches fetched: {total_matches}")
    return total_matches


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("ENHANCED DATA FETCHER - Get More Historical Data")
    print("="*80)
    
    print("\nThis script will:")
    print("1. Fetch all available competitions")
    print("2. Fetch historical matches (last 12 months)")
    print("3. Fetch current odds for all configured sports")
    print("\nNote: This may use several API requests. Monitor your rate limits.")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    # Step 1: Get all competitions
    print("\n" + "="*80)
    print("STEP 1: Fetching all competitions")
    print("="*80)
    competitions = fetch_all_available_competitions()
    
    # Step 2: Fetch historical matches
    print("\n" + "="*80)
    print("STEP 2: Fetching historical matches")
    print("="*80)
    total_matches = fetch_historical_data()
    
    # Step 3: Fetch current odds
    print("\n" + "="*80)
    print("STEP 3: Fetching current odds")
    print("="*80)
    total_events = fetch_all_odds_for_sports()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Competitions found: {len(competitions)}")
    print(f"Historical matches fetched: {total_matches}")
    print(f"Current events with odds: {total_events}")
    print(f"\nData saved to:")
    print(f"  - {FOOTBALL_DATA_ORG_DIR}")
    print(f"  - {THE_ODDS_API_DIR}")
    print("\nNext steps:")
    print("1. Run: python -m etl.transform")
    print("2. Run: python -m etl.load_to_db")
    print("3. Run: python -m models.train_model")
    print("="*80)


if __name__ == "__main__":
    main()
