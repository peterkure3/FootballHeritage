"""
Wrapper script for fetching NBA data with default parameters.
This is used by the daily pipeline to fetch current NBA data using The Odds API.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import requests
from config import (
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    NBA_DATA_DIR,
    LOG_LEVEL,
    ODDS_API_REGIONS,
    ODDS_API_MARKETS
)
from etl.utils import setup_logger, ensure_dir, save_json

# Set up logger
logger = setup_logger(__name__, LOG_LEVEL)

class NbaOddsFetcher:
    """Fetches NBA odds data from The Odds API."""
    
    def __init__(self):
        self.base_url = THE_ODDS_API_BASE_URL
        self.api_key = THE_ODDS_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FootballHeritage/1.0 (pipeline data collection)"
        })
        ensure_dir(NBA_DATA_DIR)
    
    def fetch_nba_odds(self, sport: str = "basketball_nba"):
        """Fetch NBA odds from The Odds API."""
        url = f"{self.base_url}/sports/{sport}/odds"
        
        params = {
            "apiKey": self.api_key,
            "regions": ODDS_API_REGIONS,
            "markets": ODDS_API_MARKETS,
            "oddsFormat": "decimal"
        }
        
        try:
            logger.info(f"Fetching NBA odds from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            odds_data = response.json()
            logger.info(f"Fetched {len(odds_data)} NBA odds records")
            
            # Save the raw data
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = NBA_DATA_DIR / f"nba_odds_{timestamp}.json"
            save_json(odds_data, output_file)
            logger.info(f"Saved NBA odds to {output_file}")
            
            return odds_data
            
        except Exception as e:
            logger.error(f"Error fetching NBA odds: {e}")
            return []
    
    def fetch_nba_scores(self, sport: str = "basketball_nba"):
        """Fetch NBA scores from The Odds API."""
        url = f"{self.base_url}/sports/{sport}/scores"
        
        params = {
            "apiKey": self.api_key,
            "daysFrom": 1  # Get scores from the last day
        }
        
        try:
            logger.info(f"Fetching NBA scores from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            scores_data = response.json()
            logger.info(f"Fetched {len(scores_data)} NBA scores")
            
            # Save the raw data
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = NBA_DATA_DIR / f"nba_scores_{timestamp}.json"
            save_json(scores_data, output_file)
            logger.info(f"Saved NBA scores to {output_file}")
            
            return scores_data
            
        except Exception as e:
            logger.error(f"Error fetching NBA scores: {e}")
            return []

def main():
    """Fetch current NBA data using The Odds API."""
    try:
        if not THE_ODDS_API_KEY or THE_ODDS_API_KEY == "YOUR_THE_ODDS_API_KEY":
            logger.error("THE_ODDS_API_KEY is not set in the environment variables")
            sys.exit(1)
            
        fetcher = NbaOddsFetcher()
        
        # Fetch and save NBA odds
        logger.info("Fetching NBA odds...")
        odds = fetcher.fetch_nba_odds()
        
        # Fetch and save NBA scores
        logger.info("Fetching NBA scores...")
        scores = fetcher.fetch_nba_scores()
        
        logger.info("NBA data fetch completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in NBA data fetch: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    main()
