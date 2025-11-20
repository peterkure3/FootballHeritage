"""
Fetch NCAA basketball data from NCAA API.
Supports men's and women's Division I basketball.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    NCAA_API_BASE_URL,
    NCAA_API_DIR,
    NCAA_SPORTS,
    NCAA_RATE_LIMIT,
    API_TIMEOUT,
    LOG_LEVEL,
    NCAA_CACHE_TTL,
)
from etl.utils import setup_logger, ensure_dir, save_json, retry_on_failure
from etl.cache import load_cache, store_cache

logger = setup_logger(__name__, LOG_LEVEL)


class NCAADataFetcher:
    """Fetcher for NCAA basketball data."""
    
    def __init__(self):
        self.base_url = NCAA_API_BASE_URL
        self.rate_limit = NCAA_RATE_LIMIT
        self.last_request_time = 0
        self.session = requests.Session()
        
    def _rate_limit_wait(self):
        """Enforce rate limiting (5 requests per second)."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self.last_request_time = time.time()
    
    @retry_on_failure(max_attempts=3)
    def _make_request(self, endpoint: str) -> Dict:
        """
        Make a rate-limited request to NCAA API.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            JSON response as dictionary
        """
        self._rate_limit_wait()
        
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Fetching: {url}")
        
        response = self.session.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        return response.json()
    
    def fetch_scoreboard(
        self,
        sport: str,
        division: str,
        date: Optional[str] = None
    ) -> Dict:
        """
        Fetch scoreboard for a specific date.
        
        Args:
            sport: Sport key (e.g., 'basketball-men', 'basketball-women')
            division: Division (e.g., 'd1', 'd2', 'd3')
            date: Date in YYYY/MM/DD format (None for today)
            
        Returns:
            Scoreboard data
        """
        if date:
            endpoint = f"/scoreboard/{sport}/{division}/{date}/all-conf"
        else:
            endpoint = f"/scoreboard/{sport}/{division}"
        cache_key = {
            "endpoint": "scoreboard",
            "sport": sport,
            "division": division,
            "date": date or "today",
        }
        cached = load_cache("ncaa_api", cache_key, NCAA_CACHE_TTL)
        if cached is not None:
            logger.info("Cache hit: NCAA scoreboard %s %s %s", sport, division, date or "today")
            return cached
        
        try:
            data = self._make_request(endpoint)
            logger.info(f"Fetched {len(data.get('games', []))} games for {sport} on {date or 'today'}")
            store_cache("ncaa_api", cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch scoreboard: {str(e)}")
            return {"games": []}
    
    def fetch_game_details(self, game_id: str) -> Dict:
        """
        Fetch detailed information for a specific game.
        
        Args:
            game_id: NCAA game ID
            
        Returns:
            Game details
        """
        endpoint = f"/game/{game_id}"
        cache_key = {"endpoint": "game", "game_id": game_id}
        cached = load_cache("ncaa_api", cache_key, NCAA_CACHE_TTL)
        if cached is not None:
            logger.info("Cache hit: NCAA game %s", game_id)
            return cached
        
        try:
            data = self._make_request(endpoint)
            logger.info(f"Fetched details for game {game_id}")
            store_cache("ncaa_api", cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch game {game_id}: {str(e)}")
            return {}
    
    def fetch_team_info(self, team_slug: str) -> Dict:
        """
        Fetch team information.
        
        Args:
            team_slug: Team slug (e.g., 'duke', 'north-carolina')
            
        Returns:
            Team information
        """
        endpoint = f"/team/{team_slug}"
        cache_key = {"endpoint": "team", "team_slug": team_slug}
        cached = load_cache("ncaa_api", cache_key, NCAA_CACHE_TTL)
        if cached is not None:
            logger.info("Cache hit: NCAA team %s", team_slug)
            return cached
        
        try:
            data = self._make_request(endpoint)
            logger.info(f"Fetched info for team {team_slug}")
            store_cache("ncaa_api", cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch team {team_slug}: {str(e)}")
            return {}
    
    def fetch_date_range(
        self,
        sport: str,
        division: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Fetch scoreboards for a date range.
        
        Args:
            sport: Sport key
            division: Division
            start_date: Start date
            end_date: End date
            
        Returns:
            List of scoreboard data
        """
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y/%m/%d")
            scoreboard = self.fetch_scoreboard(sport, division, date_str)
            
            if scoreboard.get("games"):
                all_data.append({
                    "date": date_str,
                    "scoreboard": scoreboard
                })
            
            current_date += timedelta(days=1)
        
        logger.info(f"Fetched {len(all_data)} days of data")
        return all_data
    
    def fetch_current_season(
        self,
        sport: str,
        days_back: int = 30
    ) -> List[Dict]:
        """
        Fetch recent games for current season.
        
        Args:
            sport: Sport key (e.g., 'basketball-men')
            days_back: Number of days to look back
            
        Returns:
            List of scoreboard data
        """
        sport_config = NCAA_SPORTS.get(sport)
        if not sport_config:
            logger.error(f"Unknown sport: {sport}")
            return []
        
        division = sport_config["division"]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Fetching {sport} from {start_date.date()} to {end_date.date()}")
        
        return self.fetch_date_range(sport, division, start_date, end_date)
    
    def save_data(self, sport: str, data: List[Dict]):
        """
        Save fetched data to disk.
        
        Args:
            sport: Sport key
            data: Data to save
        """
        sport_dir = NCAA_API_DIR / sport
        ensure_dir(sport_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = sport_dir / f"scoreboard_{timestamp}.json"
        
        save_json(data, filename)
        logger.info(f"Saved data to {filename}")


def fetch_all_ncaa_basketball(days_back: int = 30):
    """
    Fetch data for both men's and women's basketball.
    
    Args:
        days_back: Number of days to look back
    """
    fetcher = NCAADataFetcher()
    
    for sport_key in NCAA_SPORTS.keys():
        logger.info(f"=" * 60)
        logger.info(f"Fetching {NCAA_SPORTS[sport_key]['name']}")
        logger.info(f"=" * 60)
        
        data = fetcher.fetch_current_season(sport_key, days_back)
        
        if data:
            fetcher.save_data(sport_key, data)
            logger.info(f"✓ Successfully fetched {len(data)} days of {sport_key} data")
        else:
            logger.warning(f"No data fetched for {sport_key}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch NCAA basketball data")
    parser.add_argument(
        "--sport",
        choices=list(NCAA_SPORTS.keys()) + ["all"],
        default="all",
        help="Sport to fetch (default: all)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.sport == "all":
            fetch_all_ncaa_basketball(args.days)
        else:
            fetcher = NCAADataFetcher()
            data = fetcher.fetch_current_season(args.sport, args.days)
            if data:
                fetcher.save_data(args.sport, data)
                logger.info(f"✓ Successfully fetched {args.sport} data")
        
        logger.info("NCAA data fetch completed successfully")
    except Exception as e:
        logger.error(f"NCAA data fetch failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
