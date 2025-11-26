"""
Transform NBA odds and scores data from The Odds API into a format suitable for the database.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from config import (
    NBA_DATA_DIR,
    PROCESSED_DATA_DIR,
    LOG_LEVEL
)
from etl.utils import (
    setup_logger,
    load_json,
    ensure_dir,
    get_timestamp_str
)

logger = setup_logger(__name__, LOG_LEVEL)

def normalize_nba_odds(odds_files: List[Path]) -> pd.DataFrame:
    """
    Normalize NBA odds data from The Odds API.
    
    Args:
        odds_files: List of JSON file paths with odds data
        
    Returns:
        Normalized DataFrame with odds data
    """
    all_odds = []
    
    for file_path in odds_files:
        try:
            data = load_json(file_path)
            
            for game in data:
                game_id = game.get('id')
                commence_time = game.get('commence_time')
                home_team = game.get('home_team')
                away_team = game.get('away_team')
                
                # Process bookmakers
                for bookmaker in game.get('bookmakers', []):
                    bookie_name = bookmaker.get('key')
                    
                    # Process markets (h2h, spreads, totals)
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key')
                        
                        for outcome in market.get('outcomes', []):
                            odds_data = {
                                'game_id': game_id,
                                'commence_time': commence_time,
                                'home_team': home_team,
                                'away_team': away_team,
                                'bookmaker': bookie_name,
                                'market': market_key,
                                'outcome': outcome.get('name'),
                                'price': outcome.get('price'),
                                'point': outcome.get('point'),
                                'last_update': game.get('last_update'),
                                'sport': 'BASKETBALL',  # Standardized sport type
                                'source_file': file_path.name
                            }
                            all_odds.append(odds_data)
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue
    
    if not all_odds:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_odds)
    
    # Convert timestamp strings to datetime
    if 'commence_time' in df.columns:
        df['commence_time'] = pd.to_datetime(df['commence_time'])
    if 'last_update' in df.columns:
        df['last_update'] = pd.to_datetime(df['last_update'])
    
    return df

def normalize_nba_scores(scores_files: List[Path]) -> pd.DataFrame:
    """
    Normalize NBA scores data from The Odds API.
    
    Args:
        scores_files: List of JSON file paths with scores data
        
    Returns:
        Normalized DataFrame with scores data
    """
    all_scores = []
    
    for file_path in scores_files:
        try:
            data = load_json(file_path)
            
            for game in data:
                score_data = {
                    'game_id': game.get('id'),
                    'sport_key': 'BASKETBALL',  # Standardized sport type
                    'sport_title': game.get('sport_title'),
                    'commence_time': game.get('commence_time'),
                    'completed': game.get('completed'),
                    'home_team': game.get('home_team'),
                    'away_team': game.get('away_team'),
                    'scores': json.dumps(game.get('scores', [])),
                    'last_update': game.get('last_update'),
                    'source_file': file_path.name
                }
                all_scores.append(score_data)
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue
    
    if not all_scores:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_scores)
    
    # Convert timestamp strings to datetime
    if 'commence_time' in df.columns:
        df['commence_time'] = pd.to_datetime(df['commence_time'])
    if 'last_update' in df.columns:
        df['last_update'] = pd.to_datetime(df['last_update'])
    
    return df

def transform_nba_data():
    """Main function to transform NBA data."""
    logger.info("Starting NBA data transformation")
    
    ensure_dir(PROCESSED_DATA_DIR)
    
    # Find all NBA odds and scores files
    nba_odds_files = list(NBA_DATA_DIR.glob("nba_odds_*.json"))
    nba_scores_files = list(NBA_DATA_DIR.glob("nba_scores_*.json"))
    
    # Process odds data
    odds_df = pd.DataFrame()
    if nba_odds_files:
        logger.info(f"Processing {len(nba_odds_files)} NBA odds files")
        odds_df = normalize_nba_odds(nba_odds_files)
        
        if not odds_df.empty:
            # Save processed odds data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = PROCESSED_DATA_DIR / f"nba_odds_processed_{timestamp}.parquet"
            odds_df.to_parquet(output_file, index=False)
            logger.info(f"Saved processed NBA odds to {output_file}")
    
    # Process scores data
    scores_df = pd.DataFrame()
    if nba_scores_files:
        logger.info(f"Processing {len(nba_scores_files)} NBA scores files")
        scores_df = normalize_nba_scores(nba_scores_files)
        
        if not scores_df.empty:
            # Save processed scores data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = PROCESSED_DATA_DIR / f"nba_scores_processed_{timestamp}.parquet"
            scores_df.to_parquet(output_file, index=False)
            logger.info(f"Saved processed NBA scores to {output_file}")
    
    logger.info("NBA data transformation completed")
    return {
        'nba_odds': odds_df,
        'nba_scores': scores_df
    }

def main():
    """Main entry point for the NBA data transformer."""
    transform_nba_data()

if __name__ == "__main__":
    main()
