"""
Fetch NCAA Basketball (NCAAB) odds and scores from The Odds API.
Supports March Madness and regular season games.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import requests
from config import (
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    NCAAB_DATA_DIR,
    LOG_LEVEL,
    ODDS_API_REGIONS,
    ODDS_API_MARKETS
)
from etl.utils import setup_logger, ensure_dir, save_json

logger = setup_logger(__name__, LOG_LEVEL)


class NcaabOddsFetcher:
    """Fetches NCAA Basketball odds and scores from The Odds API."""
    
    SPORT_KEY = "basketball_ncaab"
    
    def __init__(self):
        self.base_url = THE_ODDS_API_BASE_URL
        self.api_key = THE_ODDS_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FootballHeritage/1.0 (pipeline data collection)"
        })
        ensure_dir(NCAAB_DATA_DIR)
    
    def fetch_odds(self) -> list:
        """
        Fetch NCAAB odds from The Odds API.
        
        Returns:
            List of odds records
        """
        url = f"{self.base_url}/sports/{self.SPORT_KEY}/odds"
        
        params = {
            "apiKey": self.api_key,
            "regions": ODDS_API_REGIONS,
            "markets": ODDS_API_MARKETS,
            "oddsFormat": "decimal"
        }
        
        try:
            logger.info(f"Fetching NCAAB odds from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            odds_data = response.json()
            remaining = response.headers.get("x-requests-remaining", "unknown")
            
            logger.info(f"Fetched {len(odds_data)} NCAAB odds records")
            logger.info(f"API requests remaining: {remaining}")
            
            # Save raw data
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = NCAAB_DATA_DIR / f"ncaab_odds_{timestamp}.json"
            save_json(odds_data, output_file)
            logger.info(f"Saved NCAAB odds to {output_file}")
            
            return odds_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("NCAAB odds not available (404) - may be off-season")
                return []
            logger.error(f"HTTP error fetching NCAAB odds: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching NCAAB odds: {e}")
            return []
    
    def fetch_scores(self, days_from: int = 3) -> list:
        """
        Fetch NCAAB scores from The Odds API.
        
        Args:
            days_from: Number of days to look back for completed games
            
        Returns:
            List of score records
        """
        url = f"{self.base_url}/sports/{self.SPORT_KEY}/scores"
        
        params = {
            "apiKey": self.api_key,
            "daysFrom": days_from
        }
        
        try:
            logger.info(f"Fetching NCAAB scores from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            scores_data = response.json()
            remaining = response.headers.get("x-requests-remaining", "unknown")
            
            logger.info(f"Fetched {len(scores_data)} NCAAB scores")
            logger.info(f"API requests remaining: {remaining}")
            
            # Save raw data
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = NCAAB_DATA_DIR / f"ncaab_scores_{timestamp}.json"
            save_json(scores_data, output_file)
            logger.info(f"Saved NCAAB scores to {output_file}")
            
            return scores_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("NCAAB scores not available (404) - may be off-season")
                return []
            logger.error(f"HTTP error fetching NCAAB scores: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching NCAAB scores: {e}")
            return []
    
    def fetch_events(self) -> list:
        """
        Fetch upcoming NCAAB events (games) from The Odds API.
        
        Returns:
            List of event records
        """
        url = f"{self.base_url}/sports/{self.SPORT_KEY}/events"
        
        params = {
            "apiKey": self.api_key,
        }
        
        try:
            logger.info(f"Fetching NCAAB events from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            events_data = response.json()
            remaining = response.headers.get("x-requests-remaining", "unknown")
            
            logger.info(f"Fetched {len(events_data)} NCAAB events")
            logger.info(f"API requests remaining: {remaining}")
            
            # Save raw data
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = NCAAB_DATA_DIR / f"ncaab_events_{timestamp}.json"
            save_json(events_data, output_file)
            logger.info(f"Saved NCAAB events to {output_file}")
            
            return events_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("NCAAB events not available (404) - may be off-season")
                return []
            logger.error(f"HTTP error fetching NCAAB events: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching NCAAB events: {e}")
            return []


def fetch_all_ncaab_data():
    """Fetch all NCAAB data (odds, scores, events)."""
    if not THE_ODDS_API_KEY or THE_ODDS_API_KEY == "YOUR_THE_ODDS_API_KEY":
        logger.error("THE_ODDS_API_KEY is not set in environment variables")
        return False
    
    fetcher = NcaabOddsFetcher()
    
    logger.info("=" * 60)
    logger.info("Fetching NCAA Basketball (NCAAB) Data")
    logger.info("=" * 60)
    
    # Fetch odds
    odds = fetcher.fetch_odds()
    
    # Fetch scores
    scores = fetcher.fetch_scores(days_from=3)
    
    # Fetch events
    events = fetcher.fetch_events()
    
    logger.info("=" * 60)
    logger.info(f"NCAAB Data Summary:")
    logger.info(f"  - Odds records: {len(odds)}")
    logger.info(f"  - Score records: {len(scores)}")
    logger.info(f"  - Event records: {len(events)}")
    logger.info("=" * 60)
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch NCAA Basketball odds and scores")
    parser.add_argument(
        "--type",
        choices=["odds", "scores", "events", "all"],
        default="all",
        help="Type of data to fetch (default: all)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Days to look back for scores (default: 3)"
    )
    
    args = parser.parse_args()
    
    if not THE_ODDS_API_KEY or THE_ODDS_API_KEY == "YOUR_THE_ODDS_API_KEY":
        logger.error("THE_ODDS_API_KEY is not set in environment variables")
        sys.exit(1)
    
    fetcher = NcaabOddsFetcher()
    
    try:
        if args.type == "all":
            fetch_all_ncaab_data()
        elif args.type == "odds":
            fetcher.fetch_odds()
        elif args.type == "scores":
            fetcher.fetch_scores(days_from=args.days)
        elif args.type == "events":
            fetcher.fetch_events()
        
        logger.info("NCAAB data fetch completed successfully")
        
    except Exception as e:
        logger.error(f"NCAAB data fetch failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
