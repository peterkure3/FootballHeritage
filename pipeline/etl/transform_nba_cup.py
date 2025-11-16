"""
Transform NBA Cup data into standardized format for database storage.
Processes games from balldontlie.io and odds from The Odds API.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


class NbaCupTransformer:
    """
    Transform NBA Cup data into standardized format.
    
    Input: Raw JSON from balldontlie.io + The Odds API
    Output: Pandas DataFrames ready for database insertion
    """
    
    def __init__(self):
        """Initialize transformer."""
        self.league = "nba_cup"
        self.sport = "basketball"
    
    def transform_games(self, games_data: Dict) -> pd.DataFrame:
        """
        Transform NBA Cup games into events DataFrame.
        
        Args:
            games_data: Raw games data from balldontlie.io
        
        Returns:
            DataFrame with columns matching events table schema
        """
        games = games_data.get("data", [])
        
        if not games:
            logger.warning("No NBA Cup games to transform")
            return pd.DataFrame()
        
        transformed_games = []
        
        for game in games:
            try:
                # Extract team information
                home_team = game.get("home_team", {})
                away_team = game.get("visitor_team", {})
                
                # Parse game date
                game_date = game.get("date")
                if game_date:
                    event_date = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                else:
                    logger.warning(f"Game {game.get('id')} missing date, skipping")
                    continue
                
                # Determine game status
                status = game.get("status", "").lower()
                if status == "final":
                    event_status = "completed"
                elif status in ["in progress", "halftime"]:
                    event_status = "live"
                else:
                    event_status = "upcoming"
                
                # Build event record
                event = {
                    "external_id": f"nba_cup_{game.get('id')}",
                    "sport": self.sport,
                    "league": self.league,
                    "home_team": home_team.get("full_name", home_team.get("name", "Unknown")),
                    "away_team": away_team.get("full_name", away_team.get("name", "Unknown")),
                    "home_team_abbr": home_team.get("abbreviation", ""),
                    "away_team_abbr": away_team.get("abbreviation", ""),
                    "event_date": event_date,
                    "status": event_status,
                    "home_score": game.get("home_team_score"),
                    "away_score": game.get("visitor_team_score"),
                    "season": game.get("season"),
                    "season_type": "Cup",
                    "venue": None,  # balldontlie.io doesn't provide venue
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                transformed_games.append(event)
                
            except Exception as e:
                logger.error(f"Error transforming game {game.get('id')}: {e}")
                continue
        
        df = pd.DataFrame(transformed_games)
        logger.info(f"✓ Transformed {len(df)} NBA Cup games")
        
        return df
    
    def transform_odds(self, odds_data: List[Dict], games_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform NBA Cup odds into standardized format.
        
        Args:
            odds_data: Raw odds data from The Odds API
            games_df: Transformed games DataFrame (for matching)
        
        Returns:
            DataFrame with columns matching odds table schema
        """
        if not odds_data:
            logger.warning("No NBA Cup odds to transform")
            return pd.DataFrame()
        
        transformed_odds = []
        
        for event in odds_data:
            try:
                # Extract event info
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")
                commence_time = event.get("commence_time", "")
                
                # Parse commence time
                if commence_time:
                    event_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                else:
                    continue
                
                # Create external_id for matching with games
                external_id = f"nba_cup_{event.get('id', '')}"
                
                # Process each bookmaker
                bookmakers = event.get("bookmakers", [])
                
                for bookmaker in bookmakers:
                    bookmaker_name = bookmaker.get("key", "unknown")
                    markets = bookmaker.get("markets", [])
                    
                    # Initialize odds dict
                    odds_record = {
                        "external_id": external_id,
                        "sport": self.sport,
                        "league": self.league,
                        "home_team": home_team,
                        "away_team": away_team,
                        "event_date": event_date,
                        "bookmaker": bookmaker_name,
                        "moneyline_home": None,
                        "moneyline_away": None,
                        "spread_home": None,
                        "spread_away": None,
                        "spread_odds_home": None,
                        "spread_odds_away": None,
                        "total": None,
                        "over_odds": None,
                        "under_odds": None,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Extract odds from each market
                    for market in markets:
                        market_key = market.get("key", "")
                        outcomes = market.get("outcomes", [])
                        
                        if market_key == "h2h":  # Moneyline
                            for outcome in outcomes:
                                if outcome.get("name") == home_team:
                                    odds_record["moneyline_home"] = outcome.get("price")
                                elif outcome.get("name") == away_team:
                                    odds_record["moneyline_away"] = outcome.get("price")
                        
                        elif market_key == "spreads":  # Point spread
                            for outcome in outcomes:
                                if outcome.get("name") == home_team:
                                    odds_record["spread_home"] = outcome.get("point")
                                    odds_record["spread_odds_home"] = outcome.get("price")
                                elif outcome.get("name") == away_team:
                                    odds_record["spread_away"] = outcome.get("point")
                                    odds_record["spread_odds_away"] = outcome.get("price")
                        
                        elif market_key == "totals":  # Over/Under
                            for outcome in outcomes:
                                if outcome.get("name") == "Over":
                                    odds_record["total"] = outcome.get("point")
                                    odds_record["over_odds"] = outcome.get("price")
                                elif outcome.get("name") == "Under":
                                    odds_record["under_odds"] = outcome.get("price")
                    
                    transformed_odds.append(odds_record)
            
            except Exception as e:
                logger.error(f"Error transforming odds for event {event.get('id')}: {e}")
                continue
        
        df = pd.DataFrame(transformed_odds)
        logger.info(f"✓ Transformed {len(df)} NBA Cup odds records")
        
        return df
    
    def transform_all(self, raw_data: Dict) -> Dict[str, pd.DataFrame]:
        """
        Transform all NBA Cup data (games + odds).
        
        Args:
            raw_data: Combined raw data from fetch_nba_cup_data.py
        
        Returns:
            Dictionary with 'events' and 'odds' DataFrames
        """
        logger.info("Starting NBA Cup data transformation")
        
        # Transform games
        games_df = self.transform_games(raw_data.get("games", {}))
        
        # Transform odds
        odds_df = self.transform_odds(raw_data.get("odds", []), games_df)
        
        logger.info("✓ NBA Cup transformation completed")
        
        return {
            "events": games_df,
            "odds": odds_df
        }


def main():
    """
    Test transformation with sample data.
    
    Usage:
        python transform_nba_cup.py
    """
    from pathlib import Path
    import json
    
    # Find latest NBA Cup data file
    nba_cup_dir = Path(__file__).parent.parent / "data" / "raw" / "the_odds_api" / "nba_cup"
    
    if not nba_cup_dir.exists():
        logger.error(f"NBA Cup data directory not found: {nba_cup_dir}")
        logger.info("Run fetch_nba_cup_data.py first to fetch data")
        return
    
    # Get latest file
    json_files = list(nba_cup_dir.glob("nba_cup_*.json"))
    if not json_files:
        logger.error("No NBA Cup data files found")
        logger.info("Run fetch_nba_cup_data.py first to fetch data")
        return
    
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading data from: {latest_file}")
    
    # Load data
    with open(latest_file, 'r') as f:
        raw_data = json.load(f)
    
    # Transform data
    transformer = NbaCupTransformer()
    transformed = transformer.transform_all(raw_data)
    
    # Print summary
    print("\n" + "="*50)
    print("NBA CUP TRANSFORMATION SUMMARY")
    print("="*50)
    print(f"Events transformed: {len(transformed['events'])}")
    print(f"Odds records transformed: {len(transformed['odds'])}")
    print("\nSample Event:")
    if not transformed['events'].empty:
        print(transformed['events'].head(1).to_dict('records')[0])
    print("\nSample Odds:")
    if not transformed['odds'].empty:
        print(transformed['odds'].head(1).to_dict('records')[0])
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
