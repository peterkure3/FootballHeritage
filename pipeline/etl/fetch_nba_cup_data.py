"""
Fetch NBA Cup data from balldontlie.io and The Odds API.
NBA Cup (In-Season Tournament) is a mid-season competition separate from regular NBA games.

Free APIs Used:
- balldontlie.io: Game schedules, scores, team stats (NO API KEY REQUIRED)
- The Odds API: Betting odds for NBA Cup games (FREE TIER: 500 requests/month)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

import requests

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import (
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    THE_ODDS_API_DIR,
    API_TIMEOUT,
    LOG_LEVEL,
    NBA_CUP_CACHE_TTL,
    ODDS_CACHE_TTL,
)
from etl.utils import (
    setup_logger,
    retry_on_failure,
    save_json,
    get_timestamp_str,
    ensure_dir,
)
from etl.cache import load_cache, store_cache

logger = setup_logger(__name__, LOG_LEVEL)


class NbaCupFetcher:
    """
    Fetcher for NBA Cup data from balldontlie.io and The Odds API.
    
    NBA Cup Format:
    - All 30 NBA teams compete
    - Group stage + knockout rounds
    - Games count toward regular season standings
    - Separate championship trophy
    """
    
    def __init__(self):
        """Initialize NBA Cup fetcher with API configurations."""
        self.balldontlie_base_url = "https://api.balldontlie.io/v1"
        self.odds_api_key = THE_ODDS_API_KEY
        self.odds_api_base_url = THE_ODDS_API_BASE_URL
        self.session = requests.Session()
        
        # balldontlie.io doesn't require API key (free tier)
        self.balldontlie_headers = {
            "Content-Type": "application/json"
        }
        
        # Rate limiting: balldontlie.io allows 60 requests/minute
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
    
    def _rate_limit_wait(self):
        """Implement rate limiting to avoid hitting API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry_on_failure(max_attempts=3, backoff_factor=2)
    def fetch_nba_cup_games(self, season: int = 2024) -> Dict:
        """
        Fetch NBA Cup games from balldontlie.io.
        
        Args:
            season: NBA season year (e.g., 2024 for 2024-25 season)
        
        Returns:
            Dictionary containing NBA Cup games data
        
        API Endpoint: GET /games
        Query Params:
            - season: Year (e.g., 2024)
            - season_type: "Cup" for NBA Cup games
            - per_page: Number of results (max 100)
        
        Response Format:
        {
            "data": [
                {
                    "id": 12345,
                    "date": "2024-11-15T19:00:00.000Z",
                    "season": 2024,
                    "status": "Final",
                    "home_team": {
                        "id": 1,
                        "name": "Lakers",
                        "full_name": "Los Angeles Lakers",
                        "abbreviation": "LAL"
                    },
                    "visitor_team": {...},
                    "home_team_score": 110,
                    "visitor_team_score": 105
                }
            ],
            "meta": {
                "total_pages": 5,
                "current_page": 1,
                "per_page": 25
            }
        }
        """
        self._rate_limit_wait()
        
        url = f"{self.balldontlie_base_url}/games"
        params = {
            "season": season,
            "season_type": "Cup",  # Filter for NBA Cup games only
            "per_page": 100  # Max results per page
        }
        
        logger.info(f"Fetching NBA Cup games for season {season}")
        
        cache_key = {
            "endpoint": "nba_cup_games",
            "season": season,
        }
        cached = load_cache("nba_cup", cache_key, NBA_CUP_CACHE_TTL)
        if cached is not None:
            logger.info("Cache hit: NBA Cup games %s", season)
            return cached

        try:
            response = self.session.get(
                url,
                headers=self.balldontlie_headers,
                params=params,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Fetched {len(data.get('data', []))} NBA Cup games")
            store_cache("nba_cup", cache_key, data)
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"NBA Cup data not available for season {season}")
                return {"data": [], "meta": {}}
            raise
        except Exception as e:
            logger.error(f"Error fetching NBA Cup games: {e}")
            raise
    
    @retry_on_failure(max_attempts=3, backoff_factor=2)
    def fetch_nba_cup_odds(self, regions: str = "us", markets: str = "h2h,spreads,totals") -> Dict:
        """
        Fetch NBA Cup betting odds from The Odds API.
        
        Args:
            regions: Betting regions (e.g., "us", "uk", "eu")
            markets: Betting markets (h2h=moneyline, spreads, totals=over/under)
        
        Returns:
            Dictionary containing NBA Cup odds data
        
        API Endpoint: GET /sports/basketball_nba_cup/odds
        Query Params:
            - apiKey: Your API key
            - regions: Betting regions
            - markets: Betting markets
            - oddsFormat: "decimal" or "american"
        
        Response Format:
        [
            {
                "id": "abc123",
                "sport_key": "basketball_nba_cup",
                "sport_title": "NBA Cup",
                "commence_time": "2024-11-15T19:00:00Z",
                "home_team": "Los Angeles Lakers",
                "away_team": "Boston Celtics",
                "bookmakers": [
                    {
                        "key": "fanduel",
                        "title": "FanDuel",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Lakers", "price": 1.85},
                                    {"name": "Celtics", "price": 2.10}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        Note: Free tier limited to 500 requests/month
        """
        url = f"{self.odds_api_base_url}/sports/basketball_nba_cup/odds"
        params = {
            "apiKey": self.odds_api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal"  # Easier to work with than American odds
        }
        
        logger.info("Fetching NBA Cup odds from The Odds API")
        
        cache_key = {
            "endpoint": "nba_cup_odds",
            "regions": regions,
            "markets": markets,
        }
        cached = load_cache("the_odds_api", cache_key, ODDS_CACHE_TTL)
        if cached is not None:
            logger.info("Cache hit: NBA Cup odds")
            return cached

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Fetched odds for {len(data)} NBA Cup games")
            
            # Log remaining API quota
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            logger.info(f"The Odds API requests remaining: {remaining}")
            store_cache("the_odds_api", cache_key, data)
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Invalid API key for The Odds API")
            elif e.response.status_code == 429:
                logger.error("Rate limit exceeded for The Odds API")
            raise
        except Exception as e:
            logger.error(f"Error fetching NBA Cup odds: {e}")
            raise
    
    def fetch_all_nba_cup_data(self, season: int = 2024) -> Dict:
        """
        Fetch all NBA Cup data (games + odds) and combine them.
        
        Args:
            season: NBA season year
        
        Returns:
            Combined dictionary with games and odds
        """
        logger.info(f"Starting NBA Cup data fetch for season {season}")
        
        # Fetch games from balldontlie.io
        games_data = self.fetch_nba_cup_games(season=season)
        
        # Fetch odds from The Odds API
        odds_data = self.fetch_nba_cup_odds()
        
        # Combine data
        combined_data = {
            "games": games_data,
            "odds": odds_data,
            "fetched_at": datetime.utcnow().isoformat(),
            "season": season
        }
        
        logger.info("✓ NBA Cup data fetch completed successfully")
        return combined_data


def main():
    """
    Main function to fetch and save NBA Cup data.
    Run this script to fetch latest NBA Cup data.
    
    Usage:
        python fetch_nba_cup_data.py
    """
    # Ensure output directory exists
    nba_cup_dir = THE_ODDS_API_DIR / "nba_cup"
    ensure_dir(nba_cup_dir)
    
    # Initialize fetcher
    fetcher = NbaCupFetcher()
    
    # Fetch current season data (2024-25 season)
    current_season = 2024
    logger.info(f"Fetching NBA Cup data for {current_season}-{current_season+1} season")
    
    try:
        # Fetch all data
        data = fetcher.fetch_all_nba_cup_data(season=current_season)
        
        # Save to JSON file
        timestamp = get_timestamp_str()
        filename = f"nba_cup_{current_season}_{timestamp}.json"
        filepath = nba_cup_dir / filename
        
        save_json(data, filepath)
        logger.info(f"✓ NBA Cup data saved to {filepath}")
        
        # Print summary
        games_count = len(data.get("games", {}).get("data", []))
        odds_count = len(data.get("odds", []))
        
        print("\n" + "="*50)
        print("NBA CUP DATA FETCH SUMMARY")
        print("="*50)
        print(f"Season: {current_season}-{current_season+1}")
        print(f"Games fetched: {games_count}")
        print(f"Odds fetched: {odds_count}")
        print(f"Saved to: {filepath}")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to fetch NBA Cup data: {e}")
        raise


if __name__ == "__main__":
    main()
