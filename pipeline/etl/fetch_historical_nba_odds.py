"""
Fetch historical NBA odds data from The Odds API.
"""
import os
import json
import time
from datetime import datetime, timedelta
import requests
from pathlib import Path
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('historical_odds_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class HistoricalOddsFetcher:
    """Fetches historical NBA odds data from The Odds API."""
    
    def __init__(self):
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,  # Set to DEBUG for more detailed logging
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('historical_odds_fetch.log'),
                logging.StreamHandler()
            ]
        )
        
        self.api_key = os.getenv('THE_ODDS_API_KEY')
        if not self.api_key:
            raise ValueError("THE_ODDS_API_KEY environment variable not set")
            
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        self.sport = "basketball_nba"
        self.regions = "us"  # us, uk, eu, au
        self.markets = "h2h,spreads,totals"
        self.odds_format = "decimal"
        self.date_format = "%Y-%m-%dT%H:%M:%SZ"
        
        # Create output directories
        self.raw_dir = Path("data/raw/historical/nba/odds")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Log API key status (masked)
        logger.info(f"Using API key: {self.api_key[:4]}...{self.api_key[-4:]}")
    
    def get_season_dates(self, season_year):
        """Get start and end dates for an NBA season."""
        # NBA regular season typically starts in October and ends in April
        season_start = datetime(season_year, 10, 1)  # October 1st
        season_end = datetime(season_year + 1, 4, 15)  # Mid-April (end of regular season)
        
        # If we're in the current season, adjust end date to today
        current_year = datetime.now().year
        if season_year == current_year:
            season_end = datetime.now()
            
        logger.info(f"NBA {season_year}-{season_year+1} season: {season_start.date()} to {season_end.date()}")
        return season_start, season_end
    
    def fetch_odds_for_date(self, date):
        """Fetch odds for a specific date."""
        # Skip future dates
        if date > datetime.now():
            logger.debug(f"Skipping future date: {date.date()}")
            return []
            
        url = f"{self.base_url}/{self.sport}/odds"
        
        # Format dates in ISO 8601 format with timezone
        from_date = date.replace(hour=12, minute=0, second=0).isoformat() + 'Z'  # Use noon to catch games in all timezones
        to_date = (date + timedelta(days=1)).replace(hour=12, minute=0, second=0).isoformat() + 'Z'
        
        params = {
            'apiKey': self.api_key,
            'regions': self.regions,
            'markets': self.markets,
            'oddsFormat': self.odds_format,
            'dateFormat': 'iso',
            'commenceTimeFrom': from_date,
            'commenceTimeTo': to_date
        }
        
        try:
            logger.info(f"Fetching odds for {date.date()}...")
            logger.debug(f"API Request: {url}?{'&'.join([f'{k}={v}' for k, v in params.items() if k != 'apiKey'])}")
            
            response = requests.get(url, params=params)
            
            # Log response status and headers for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.fetch_odds_for_date(date)  # Retry
                
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"API Response: {json.dumps(data, indent=2)[:1000]}...")  # Log first 1000 chars of response
            
            if not data:
                logger.info(f"No odds data for {date.date()}")
                return []
                
            logger.info(f"Fetched {len(data)} games for {date.date()}")
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                logger.debug(f"No odds available for {date.date()} (422 Unprocessable Entity)")
                return []
            logger.error(f"HTTP error fetching odds for {date.date()}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching odds for {date.date()}: {e}")
            return []
    
    def save_raw_data(self, data, date_str):
        """Save raw API response to a JSON file."""
        if not data:  # Don't save empty data
            return
            
        filename = self.raw_dir / f"nba_odds_{date_str}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data)} games to {filename}")
    
    def fetch_season_odds(self, season_year):
        """Fetch odds for an entire NBA season."""
        logger.info(f"Fetching odds for {season_year}-{season_year+1} NBA season...")
        
        start_date, end_date = self.get_season_dates(season_year)
        current_date = start_date
        
        # Adjust end_date to not exceed current date
        end_date = min(end_date, datetime.now())
        
        while current_date <= end_date:
            # Skip weekends if no games are typically scheduled (optional optimization)
            if current_date.weekday() in [5, 6]:  # Saturday or Sunday
                logger.debug(f"Skipping weekend date: {current_date.date()}")
                current_date += timedelta(days=1)
                continue
                
            date_str = current_date.strftime("%Y%m%d")
            output_file = self.raw_dir / f"nba_odds_{date_str}.json"
            
            if output_file.exists():
                logger.debug(f"Skipping {current_date.date()} - already processed")
                current_date += timedelta(days=1)
                continue
                
            logger.info(f"Processing {current_date.date()}...")
                
            # Fetch data for this date
            data = self.fetch_odds_for_date(current_date)
            
            # Save if we got data
            if data:
                self.save_raw_data(data, date_str)
            
            # Be nice to the API - add a small delay between requests
            time.sleep(1.5)
            current_date += timedelta(days=1)
    
    def fetch_last_n_seasons(self, n=5):
        """Fetch odds for the last N NBA seasons."""
        current_year = datetime.now().year
        for year in range(current_year - n, current_year):
            self.fetch_season_odds(year)

def main():
    """Main function to fetch historical NBA odds."""
    try:
        fetcher = HistoricalOddsFetcher()
        # Fetch the 2023-2024 season which should have complete data
        season_year = 2023
        logger.info(f"Starting to fetch odds for the {season_year}-{season_year+1} NBA season...")
        
        # Get the season dates
        start_date, end_date = fetcher.get_season_dates(season_year)
        logger.info(f"Fetching data from {start_date.date()} to {end_date.date()}")
        
        # Fetch data for the season
        fetcher.fetch_season_odds(season_year)
        
        # List all saved files
        output_dir = Path("data/raw/historical/nba/odds")
        if output_dir.exists():
            saved_files = list(output_dir.glob("*.json"))
            if saved_files:
                logger.info(f"Successfully saved {len(saved_files)} data files to {output_dir}")
                logger.info("Sample of saved files:")
                for f in sorted(saved_files)[:3]:  # Show first 3 files as sample
                    logger.info(f"- {f.name}")
                
                # Show a sample of the first file's content
                if saved_files:
                    with open(saved_files[0], 'r') as f:
                        sample_data = json.load(f)
                        logger.info("Sample data from first file:")
                        logger.info(json.dumps(sample_data[:2], indent=2))  # Show first 2 entries
            else:
                logger.warning("No data files were saved. Check API response and logs.")
    except Exception as e:
        logger.error(f"Error in historical odds fetch: {e}", exc_info=True)

if __name__ == "__main__":
    main()
