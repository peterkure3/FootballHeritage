"""
Fetch raw data from football-data.org and The Odds API.
Save JSON responses to data/raw/ directories.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import (
    FOOTBALL_DATA_ORG_API_KEY,
    FOOTBALL_DATA_ORG_BASE_URL,
    FOOTBALL_DATA_ORG_DIR,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    THE_ODDS_API_DIR,
    TRACKED_COMPETITIONS,
    ODDS_API_SPORT,
    ODDS_API_REGIONS,
    ODDS_API_MARKETS,
    ODDS_API_ODDS_FORMAT,
    API_TIMEOUT,
    LOG_LEVEL,
)
from etl.utils import (
    setup_logger,
    retry_on_failure,
    get_requests_session,
    save_json,
    get_timestamp_str,
    ensure_dir,
)

logger = setup_logger(__name__, LOG_LEVEL)


class FootballDataOrgFetcher:
    """Fetcher for football-data.org API."""
    
    def __init__(self, api_key: str, base_url: str):
        """
        Initialize fetcher.
        
        Args:
            api_key: API key for football-data.org
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {
            "X-Auth-Token": api_key,
            "Content-Type": "application/json"
        }
    
    def fetch_competitions(self) -> Dict:
        """
        Fetch available competitions.
        
        Returns:
            Competitions data as dictionary
        """
        url = f"{self.base_url}/competitions"
        logger.info(f"Fetching competitions from {url}")
        
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data.get('competitions', []))} competitions")
            return data
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                logger.error(f"Bad request - check API key validity: {e.response.text}")
            elif e.response.status_code == 403:
                logger.error(f"Forbidden - API key may be invalid or expired: {e.response.text}")
            elif e.response.status_code == 429:
                logger.error(f"Rate limit exceeded: {e.response.text}")
            raise
    
    def fetch_matches(
        self,
        competition_code: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict:
        """
        Fetch matches for a competition.
        
        Args:
            competition_code: Competition code (e.g., 'PL' for Premier League)
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
        
        Returns:
            Matches data as dictionary
        """
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {}
        
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        
        logger.info(f"Fetching matches for {competition_code} from {url}")
        
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data.get('matches', []))} matches for {competition_code}")
            return data
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                logger.error(f"Bad request for {competition_code}: {e.response.text}")
            elif e.response.status_code == 403:
                logger.error(f"Forbidden - check API tier for {competition_code}: {e.response.text}")
            elif e.response.status_code == 404:
                logger.error(f"Competition {competition_code} not found")
            raise
    
    def fetch_match_details(self, match_id: int) -> Dict:
        """
        Fetch detailed information for a specific match.
        
        Args:
            match_id: Match ID
        
        Returns:
            Match details as dictionary
        """
        url = f"{self.base_url}/matches/{match_id}"
        logger.info(f"Fetching match details for {match_id}")
        
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch match {match_id}: {e.response.text}")
            raise


class TheOddsApiFetcher:
    """Fetcher for The Odds API."""
    
    def __init__(self, api_key: str, base_url: str):
        """
        Initialize fetcher.
        
        Args:
            api_key: API key for The Odds API
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
    
    def fetch_odds(
        self,
        sport: str,
        regions: str = "uk",
        markets: str = "h2h",
        odds_format: str = "decimal"
    ) -> List[Dict]:
        """
        Fetch odds for a sport.
        
        Args:
            sport: Sport key (e.g., 'soccer_epl')
            regions: Comma-separated regions (e.g., 'uk,us,eu')
            markets: Comma-separated markets (e.g., 'h2h')
            odds_format: Odds format ('decimal', 'american')
        
        Returns:
            List of odds data
        """
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }
        
        logger.info(f"Fetching odds for {sport} from {url}")
        
        try:
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched odds for {len(data)} events")
            logger.info(f"Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")
            return data
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch odds: {e.response.text if e.response else str(e)}")
            raise
    
    def fetch_scores(self, sport: str, days_from: int = 3) -> List[Dict]:
        """
        Fetch scores for a sport.
        
        Args:
            sport: Sport key (e.g., 'soccer_epl')
            days_from: Number of days from now to fetch scores
        
        Returns:
            List of scores data
        """
        url = f"{self.base_url}/sports/{sport}/scores"
        params = {
            "apiKey": self.api_key,
            "daysFrom": days_from,
        }
        
        logger.info(f"Fetching scores for {sport} from {url}")
        
        try:
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched scores for {len(data)} events")
            logger.info(f"Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")
            return data
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch scores: {e.response.text if e.response else str(e)}")
            raise


def fetch_football_data_org() -> None:
    """Fetch and save data from football-data.org."""
    logger.info("Starting football-data.org data fetch")
    
    fetcher = FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL)
    timestamp = get_timestamp_str("%Y%m%d_%H%M%S")
    
    ensure_dir(FOOTBALL_DATA_ORG_DIR)
    
    # Fetch competitions
    try:
        competitions = fetcher.fetch_competitions()
        save_json(
            competitions,
            FOOTBALL_DATA_ORG_DIR / f"competitions_{timestamp}.json"
        )
    except Exception as e:
        logger.error(f"Failed to fetch competitions: {str(e)}")
    
    # Fetch matches for tracked competitions
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    for comp_code in TRACKED_COMPETITIONS:
        try:
            matches = fetcher.fetch_matches(comp_code, date_from, date_to)
            save_json(
                matches,
                FOOTBALL_DATA_ORG_DIR / f"matches_{comp_code}_{timestamp}.json"
            )
        except Exception as e:
            logger.error(f"Failed to fetch matches for {comp_code}: {str(e)}")
    
    logger.info("Completed football-data.org data fetch")


def fetch_the_odds_api() -> None:
    """Fetch and save data from The Odds API."""
    logger.info("Starting The Odds API data fetch")
    
    fetcher = TheOddsApiFetcher(THE_ODDS_API_KEY, THE_ODDS_API_BASE_URL)
    timestamp = get_timestamp_str("%Y%m%d_%H%M%S")
    
    ensure_dir(THE_ODDS_API_DIR)
    
    # Fetch odds
    try:
        odds = fetcher.fetch_odds(
            ODDS_API_SPORT,
            ODDS_API_REGIONS,
            ODDS_API_MARKETS,
            ODDS_API_ODDS_FORMAT
        )
        save_json(
            {"events": odds, "fetched_at": timestamp},
            THE_ODDS_API_DIR / f"odds_{timestamp}.json"
        )
    except Exception as e:
        logger.error(f"Failed to fetch odds: {str(e)}")
    
    # Fetch scores
    try:
        scores = fetcher.fetch_scores(ODDS_API_SPORT, days_from=3)
        save_json(
            {"events": scores, "fetched_at": timestamp},
            THE_ODDS_API_DIR / f"scores_{timestamp}.json"
        )
    except Exception as e:
        logger.error(f"Failed to fetch scores: {str(e)}")
    
    logger.info("Completed The Odds API data fetch")


def main() -> None:
    """Main entry point for data fetching."""
    logger.info("Starting raw data fetch")
    
    try:
        fetch_football_data_org()
        fetch_the_odds_api()
        logger.info("Raw data fetch completed successfully")
    except Exception as e:
        logger.error(f"Raw data fetch failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
