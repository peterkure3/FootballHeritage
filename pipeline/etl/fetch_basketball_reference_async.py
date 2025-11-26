import os
import time
import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from io import StringIO
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Warning: tqdm not installed. Install with: pip install tqdm")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('basketball_reference_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.basketball-reference.com"
SEASONS = list(range(2020, 2025))  # Last 5 seasons including current
MAX_CONCURRENT_REQUESTS = 8  # Number of concurrent HTTP requests

class AsyncBasketballReferenceScraper:
    """Async scraper for Basketball Reference website using aiohttp + Selenium fallback."""
    
    def __init__(self):
        self.base_dir = Path("data/raw/historical/nba")
        self.games_dir = self.base_dir / "games"
        
        # Create directories if they don't exist
        self.games_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for async HTTP requests
        self.session = None
        
        # WebDriver fallback for difficult pages
        self.driver = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'fallback_to_selenium': 0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Create aiohttp session with realistic headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()
    
    def _init_webdriver(self):
        """Initialize WebDriver as fallback."""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    async def _get_page_async(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch a page using async HTTP requests."""
        for attempt in range(max_retries):
            try:
                # Random delay (1-3 seconds for async)
                await asyncio.sleep(1 + random.random() * 2)
                
                self.stats['total_requests'] += 1
                
                async with self.session.get(url) as response:
                    if response.status == 403:
                        logger.warning(f"403 for {url}, will try Selenium fallback")
                        return None
                    
                    if response.status == 200:
                        content = await response.text()
                        
                        # Quick check if we got a valid page
                        if "basketball-reference" in content.lower() and "access denied" not in content.lower():
                            self.stats['successful_requests'] += 1
                            return content
                        else:
                            logger.warning(f"Invalid content for {url}")
                            return None
                    
                    logger.warning(f"HTTP {response.status} for {url}")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                    return None
                await asyncio.sleep((attempt + 1) * 2)
        
        return None
    
    def _get_page_selenium(self, url: str) -> Optional[str]:
        """Fallback method using Selenium WebDriver."""
        self._init_webdriver()
        
        try:
            logger.info(f"Using Selenium fallback for {url}")
            self.stats['fallback_to_selenium'] += 1
            
            self.driver.get(url)
            
            # Wait for the content to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for access denied
            if "Access Denied" in self.driver.title:
                logger.error(f"Access denied even with Selenium for {url}")
                return None
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"Selenium fallback failed for {url}: {e}")
            return None
    
    async def _get_month_links(self, season: int) -> List[str]:
        """Get all month links for a given season."""
        season_url = f"leagues/NBA_{season+1}_games.html"
        url = urljoin(BASE_URL, season_url)
        
        # Try async first
        html = await self._get_page_async(url)
        
        # Fallback to Selenium if needed
        if not html:
            html = self._get_page_selenium(url)
        
        if not html:
            logger.error(f"Failed to fetch schedule for {season}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all month tables
        month_links = []
        months_div = soup.find('div', {'class': 'filter'})
        if months_div:
            month_links = [a['href'] for a in months_div.find_all('a') 
                         if a.get('href') and 'games-' in a['href']]
        
        return month_links
    
    async def _process_month(self, args: tuple) -> List[Dict[str, Any]]:
        """Process a single month schedule asynchronously."""
        month_url, season, month_name = args
        
        # Try async first
        html = await self._get_page_async(month_url)
        
        # Fallback to Selenium if needed
        if not html:
            html = self._get_page_selenium(month_url)
        
        if not html:
            logger.warning(f"Failed to fetch {month_name}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the schedule table
        table = soup.find('table', {'id': 'schedule'})
        if not table:
            logger.warning(f"No schedule table found at {month_url}")
            return []
        
        # Convert table to DataFrame
        df = pd.read_html(StringIO(str(table)))[0]
        
        # Clean up the DataFrame
        if 'Date' not in df.columns:
            logger.warning(f"Unexpected table format at {month_url}")
            return []
        
        df = df[df['Date'].notna()]  # Remove rows with no date
        
        # Convert to list of dicts
        games = []
        for _, row in df.iterrows():
            try:
                game = {
                    'season': f"{season}-{str(season+1)[2:]}",
                    'date': row.get('Date', ''),
                    'start_time': row.get('Start (ET)', ''),
                    'visitor': row.get('Visitor/Neutral', ''),
                    'visitor_pts': self._safe_int(row.get('PTS', '')),
                    'home': row.get('Home/Neutral', ''),
                    'home_pts': self._safe_int(row.get('PTS.1', '')),
                    'overtime': 'OT' in str(row.get('Notes', '')),
                    'attendance': row.get('Attend.', ''),
                    'notes': row.get('Notes', '')
                }
                games.append(game)
            except Exception as e:
                logger.warning(f"Error processing game row: {e}")
        
        logger.info(f"Processed {month_name}: {len(games)} games")
        return games
    
    async def get_season_schedule(self, season: int) -> List[Dict[str, Any]]:
        """Get the full NBA schedule for a given season using async processing."""
        logger.info(f"Fetching schedule for {season}-{str(season+1)[2:]} season...")
        
        # Get all month links
        month_links = await self._get_month_links(season)
        if not month_links:
            logger.error(f"No month links found for season {season}")
            return []
        
        # Prepare arguments for async processing
        month_args = []
        for month_link in month_links:
            month_url = urljoin(BASE_URL, month_link)
            month_name = month_link.split('-')[-1].replace('.html', '')
            month_args.append((month_url, season, month_name))
        
        all_games = []
        
        # Process months concurrently
        if HAS_TQDM:
            with tqdm(total=len(month_args), desc=f"Season {season}-{season+1}") as pbar:
                tasks = [self._process_month(args) for args in month_args]
                
                for coro in asyncio.as_completed(tasks):
                    try:
                        games = await coro
                        all_games.extend(games)
                        pbar.set_description(f"Season {season}-{season+1} ({len(all_games)} games)")
                    except Exception as e:
                        logger.error(f"Error in async processing: {e}")
                    finally:
                        pbar.update(1)
        else:
            # Fallback without progress bar
            tasks = [self._process_month(args) for args in month_args]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing month {i}: {result}")
                else:
                    all_games.extend(result)
        
        # Log season summary
        logger.info(f"Season {season}-{season+1} completed: {len(all_games)} games")
        logger.info(f"Stats: {self.stats['successful_requests']}/{self.stats['total_requests']} requests successful, {self.stats['fallback_to_selenium']} Selenium fallbacks")
        
        return all_games
    
    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert a value to an integer."""
        try:
            if pd.isna(value) or value == '':
                return None
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def save_games_to_json(self, games: List[Dict[str, Any]], season: int) -> str:
        """Save games data to a JSON file."""
        if not games:
            logger.warning(f"No games to save for season {season}")
            return ""
            
        # Create a filename with the season
        filename = self.games_dir / f"nba_games_{season}_{season+1}.json"
        
        try:
            # Save to JSON
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(games, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(games)} games to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error saving games to {filename}: {e}")
            return ""

async def main():
    """Main function to fetch historical NBA data with async processing."""
    total_start_time = time.time()
    
    async with AsyncBasketballReferenceScraper() as scraper:
        try:
            # Show overall progress if tqdm is available
            if HAS_TQDM:
                season_progress = tqdm(SEASONS, desc="Overall Progress")
            else:
                season_progress = SEASONS
                logger.info(f"Starting to fetch {len(SEASONS)} seasons...")
            
            for season in season_progress:
                season_start_time = time.time()
                
                # Get the schedule for the season
                games = await scraper.get_season_schedule(season)
                
                # Save the games data
                if games:
                    output_file = scraper.save_games_to_json(games, season)
                    if output_file:
                        season_time = time.time() - season_start_time
                        logger.info(f"✅ Successfully processed {len(games)} games for {season}-{season+1} in {season_time:.1f}s")
                        
                        # Show a sample of the data
                        if games:
                            sample_game = games[0]
                            logger.info(f"Sample: {sample_game['visitor']} vs {sample_game['home']} on {sample_game['date']}")
                else:
                    logger.warning(f"❌ No games found for {season}-{season+1}")
                
                # Update tqdm description
                if HAS_TQDM:
                    season_progress.set_description(f"Overall Progress (Season {season}-{season+1})")
            
            total_time = time.time() - total_start_time
            logger.info(f"🎉 All seasons completed in {total_time:.1f}s!")
            
        except Exception as e:
            logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    # Check if aiohttp is installed
    try:
        import aiohttp
    except ImportError:
        print("Installing required aiohttp package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
    
    asyncio.run(main())
