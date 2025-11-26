"""
Fetch NBA regular season data from balldontlie.io API.
Supports current season and historical data with caching.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import time
import json

sys.path.append(str(Path(__file__).parent.parent))

import requests
from config import (
    NBA_API_BASE_URL,
    NBA_DATA_DIR,
    NBA_SEASONS,
    NBA_CACHE_TTL,
    LOG_LEVEL,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    ODDS_API_REGIONS,
    ODDS_API_MARKETS,
)
from etl.utils import (
    setup_logger,
    ensure_dir,
    save_json,
    get_timestamp_str,
    retry_on_failure,
)
from etl.cache import load_cache, store_cache

logger = setup_logger(__name__, LOG_LEVEL)

class NbaDataFetcher:
    """Fetches NBA regular season data from balldontlie.io API."""
    
    def __init__(self):
        self.base_url = NBA_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FootballHeritage/1.0 (pipeline data collection)"
        })
        ensure_dir(NBA_DATA_DIR)
    
    @retry_on_failure(max_attempts=3, backoff_factor=1.5)
    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make a request to the NBA API with caching support.
        
        Args:
            endpoint: API endpoint (e.g., 'games', 'teams')
            params: Query parameters
            use_cache: Whether to use cached response if available
            
        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        cache_key = {"endpoint": endpoint, "params": params or {}}
        
        # Try to get from cache
        if use_cache:
            cached = load_cache("nba_api", cache_key, NBA_CACHE_TTL)
            if cached is not None:
                logger.debug(f"Cache hit for {endpoint} with params {params}")
                return cached
        
        # Make the request
        logger.debug(f"Fetching {url} with params {params}")
        response = self.session.get(
            url,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Store in cache
        if use_cache:
            store_cache("nba_api", cache_key, data)
        
        return data
    
    def fetch_games(
        self,
        seasons: Optional[List[int]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team_ids: Optional[List[int]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch NBA games with optional filtering.
        
        Args:
            seasons: List of seasons to fetch (e.g., [2022, 2023])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            team_ids: List of team IDs to filter by
            use_cache: Whether to use cached data if available
            
        Returns:
            List of game dictionaries
        """
        all_games = []
        params = {}
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if team_ids:
            params["team_ids[]"] = team_ids
        
        # If no seasons provided, use current season
        seasons = seasons or [NBA_SEASONS[0]]
        
        for season in seasons:
            page = 0
            per_page = 100
            total_pages = 1  # Will be updated after first request
            
            while page < total_pages:
                page_params = params.copy()
                page_params.update({
                    "seasons[]": [season],
                    "per_page": per_page,
                    "page": page + 1  # API is 1-indexed
                })
                
                try:
                    response = self._request(
                        "games",
                        params=page_params,
                        use_cache=use_cache
                    )
                    
                    games = response.get("data", [])
                    all_games.extend(games)
                    
                    # Update pagination info
                    total_pages = response.get("meta", {}).get("total_pages", 1)
                    page += 1
                    
                    # Respect rate limits
                    time.sleep(0.5)  # Be nice to the API
                    
                except Exception as e:
                    logger.error(f"Error fetching games for season {season}, page {page}: {e}")
                    raise
        
        return all_games
    
    def fetch_teams(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch all NBA teams."""
        try:
            response = self._request("teams", use_cache=use_cache)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            raise
    
    def fetch_odds(
        self,
        sport: str = "basketball_nba",
        regions: List[str] = None,
        markets: List[str] = None,
        date_format: str = "iso",
        odds_format: str = "decimal",
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch NBA odds from The Odds API.
        
        Args:
            sport: The sport to fetch odds for (default: basketball_nba)
            regions: List of bookmaker regions (default: us,eu)
            markets: List of markets to fetch (default: h2h,spreads,totals)
            date_format: Date format (iso, unix, or iso8601)
            odds_format: Odds format (decimal, american, or hongkong)
            use_cache: Whether to use cached data if available
            
        Returns:
            List of odds data
        """
        if not THE_ODDS_API_KEY:
            raise ValueError("THE_ODDS_API_KEY not configured")
            
        regions = regions or ODDS_API_REGIONS
        markets = markets or ODDS_API_MARKETS
        
        cache_key = {
            "sport": sport,
            "regions": regions,
            "markets": markets,
            "date_format": date_format,
            "odds_format": odds_format
        }
        
        # Try to get from cache
        if use_cache:
            cached = load_cache("odds_api", cache_key, NBA_CACHE_TTL)
            if cached is not None:
                logger.debug("Using cached odds data")
                return cached
        
        # Make the request
        url = f"{THE_ODDS_API_BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": ",".join(regions),
            "markets": ",".join(markets),
            "dateFormat": date_format,
            "oddsFormat": odds_format,
        }
        
        try:
            logger.debug(f"Fetching odds from {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            odds_data = response.json()
            
            # Store in cache
            if use_cache:
                store_cache("odds_api", cache_key, odds_data)
                
            return odds_data
            
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            raise
    
    def save_to_file(
        self,
        data: Union[Dict, List],
        data_type: str,
        season: Optional[int] = None
    ) -> Path:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save (must be JSON-serializable)
            data_type: Type of data (e.g., 'games', 'teams', 'odds')
            season: Optional season for filename
            
        Returns:
            Path to the saved file
        """
        timestamp = get_timestamp_str()
        filename = f"{data_type}"
        
        if season:
            filename += f"_{season}"
            
        filename += f"_{timestamp}.json"
        
        filepath = NBA_DATA_DIR / filename
        save_json(data, filepath)
        logger.info(f"Saved {data_type} to {filepath}")
        
        return filepath

def main():
    """Main entry point for the NBA data fetcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch NBA data")
    parser.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        help="Seasons to fetch (e.g., 2022 2023)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--fetch-teams",
        action="store_true",
        help="Fetch team data"
    )
    parser.add_argument(
        "--fetch-odds",
        action="store_true",
        help="Fetch betting odds"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=NBA_DATA_DIR,
        help="Output directory for saved files"
    )
    
    args = parser.parse_args()
    
    try:
        fetcher = NbaDataFetcher()
        
        # Fetch teams if requested
        if args.fetch_teams:
            teams = fetcher.fetch_teams(use_cache=not args.no_cache)
            fetcher.save_to_file(teams, "teams")
        
        # Fetch games
        if args.seasons or args.start_date or args.end_date:
            games = fetcher.fetch_games(
                seasons=args.seasons,
                start_date=args.start_date,
                end_date=args.end_date,
                use_cache=not args.no_cache
            )
            season_str = "_".join(map(str, args.seasons)) if args.seasons else "custom"
            fetcher.save_to_file(games, "games", season_str)
        
        # Fetch odds if requested
        if args.fetch_odds:
            odds = fetcher.fetch_odds(use_cache=not args.no_cache)
            fetcher.save_to_file(odds, "odds")
        
        logger.info("NBA data fetch completed successfully")
        
    except Exception as e:
        logger.error(f"Error in NBA data fetch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()