"""
Transform raw NBA data into processed datasets.
Handles data cleaning, feature engineering, and output to parquet files.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import json
import logging

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from dateutil.parser import parse as parse_date
from config import (
    NBA_DATA_DIR,
    PROCESSED_DATA_DIR,
    LOG_LEVEL,
    NBA_SEASONS,
)
from etl.utils import (
    setup_logger,
    ensure_dir,
    get_timestamp_str,
)

logger = setup_logger(__name__, LOG_LEVEL)

class NbaDataTransformer:
    """Transforms raw NBA data into processed datasets."""
    
    def __init__(self, data_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """
        Initialize the transformer with input/output directories.
        
        Args:
            data_dir: Directory containing raw JSON files (default: NBA_DATA_DIR)
            output_dir: Directory to save processed files (default: PROCESSED_DATA_DIR/nba)
        """
        self.data_dir = data_dir or NBA_DATA_DIR
        self.output_dir = (output_dir or PROCESSED_DATA_DIR) / "nba"
        ensure_dir(self.output_dir)
        
        # Team name mapping for consistency
        self.team_abbreviation_map = {
            'ATL': 'Atlanta Hawks',
            'BOS': 'Boston Celtics',
            'BKN': 'Brooklyn Nets',
            'CHA': 'Charlotte Hornets',
            'CHI': 'Chicago Bulls',
            'CLE': 'Cleveland Cavaliers',
            'DAL': 'Dallas Mavericks',
            'DEN': 'Denver Nuggets',
            'DET': 'Detroit Pistons',
            'GSW': 'Golden State Warriors',
            'HOU': 'Houston Rockets',
            'IND': 'Indiana Pacers',
            'LAC': 'LA Clippers',
            'LAL': 'Los Angeles Lakers',
            'MEM': 'Memphis Grizzlies',
            'MIA': 'Miami Heat',
            'MIL': 'Milwaukee Bucks',
            'MIN': 'Minnesota Timberwolves',
            'NOP': 'New Orleans Pelicans',
            'NYK': 'New York Knicks',
            'OKC': 'Oklahoma City Thunder',
            'ORL': 'Orlando Magic',
            'PHI': 'Philadelphia 76ers',
            'PHX': 'Phoenix Suns',
            'POR': 'Portland Trail Blazers',
            'SAC': 'Sacramento Kings',
            'SAS': 'San Antonio Spurs',
            'TOR': 'Toronto Raptors',
            'UTA': 'Utah Jazz',
            'WAS': 'Washington Wizards'
        }
        
        # Team ID to abbreviation mapping
        self.team_id_to_abbr = {
            1: 'ATL', 2: 'BOS', 4: 'BKN', 5: 'CHA', 6: 'CHI',
            7: 'CLE', 8: 'DAL', 9: 'DEN', 10: 'DET', 11: 'GSW',
            14: 'HOU', 15: 'IND', 16: 'LAC', 17: 'LAL', 19: 'MEM',
            20: 'MIA', 21: 'MIL', 22: 'MIN', 23: 'NOP', 24: 'NYK',
            25: 'OKC', 26: 'ORL', 27: 'PHI', 28: 'PHX', 29: 'POR',
            30: 'SAC', 31: 'SAS', 38: 'TOR', 40: 'UTA', 41: 'WAS'
        }
    
    def load_games_data(self, input_files: Optional[List[Path]] = None) -> pd.DataFrame:
        """
        Load and combine games data from JSON files.
        
        Args:
            input_files: List of JSON files to load. If None, will scan data_dir for game files.
            
        Returns:
            DataFrame containing games data
        """
        if input_files is None:
            input_files = list(self.data_dir.glob("games_*.json"))
            if not input_files:
                raise FileNotFoundError(f"No game files found in {self.data_dir}")
        
        all_games = []
        for file in input_files:
            logger.info(f"Loading games from {file}")
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'data' in data:
                    data = data['data']
                all_games.extend(data)
        
        if not all_games:
            logger.warning("No games data found in the provided files")
            return pd.DataFrame()
        
        df = pd.json_normalize(all_games)
        
        # Convert date columns
        date_columns = ['date', 'game_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        # Add season column if not present
        if 'season' not in df.columns and 'season' in df.columns:
            df['season'] = df['season'].astype(int)
        else:
            # Extract season from date (NBA season starts in October)
            df['season'] = df['date'].apply(
                lambda x: x.year if x.month >= 10 else x.year - 1
            )
        
        # Add team abbreviations
        df['home_team_abbr'] = df['home_team.id'].map(self.team_id_to_abbr)
        df['visitor_team_abbr'] = df['visitor_team.id'].map(self.team_id_to_abbr)
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def load_teams_data(self) -> pd.DataFrame:
        """Load and process teams data."""
        team_files = list(self.data_dir.glob("teams_*.json"))
        if not team_files:
            logger.warning("No team files found")
            return pd.DataFrame()
        
        all_teams = []
        for file in team_files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'data' in data:
                    all_teams.extend(data['data'])
                else:
                    all_teams.extend(data)
        
        if not all_teams:
            return pd.DataFrame()
        
        return pd.json_normalize(all_teams)
    
    def load_odds_data(self) -> pd.DataFrame:
        """Load and process odds data from The Odds API."""
        odds_files = list(self.data_dir.glob("odds_*.json"))
        if not odds_files:
            logger.warning("No odds files found")
            return pd.DataFrame()
        
        all_odds = []
        for file in odds_files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_odds.extend(data)
        
        if not all_odds:
            return pd.DataFrame()
        
        # Normalize odds data
        df = pd.json_normalize(
            all_odds,
            meta=['id', 'sport_key', 'sport_title', 'commence_time', 'home_team', 'away_team'],
            record_path='bookmakers',
            meta_prefix='event_'
        )
        
        # Extract markets
        df = df.explode('markets')
        df = pd.concat([
            df.drop(['markets'], axis=1),
            pd.json_normalize(df['markets'])
        ], axis=1)
        
        # Clean up column names
        df.columns = [col.replace('.', '_') for col in df.columns]
        
        return df
    
    def calculate_team_form(self, games_df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Calculate team form over a rolling window of games.
        
        Args:
            games_df: DataFrame containing game results
            window: Number of games to consider for form calculation
            
        Returns:
            DataFrame with additional form columns
        """
        # Create a copy to avoid modifying the original
        df = games_df.copy()
        
        # Ensure we have the required columns
        required_cols = ['home_team_id', 'visitor_team_id', 'home_team_score', 'visitor_team_score', 'date']
        if not all(col in df.columns for col in required_cols):
            logger.warning("Missing required columns for form calculation")
            return df
        
        # Create a long format of the games
        home_games = df[['date', 'home_team_id', 'home_team_score', 'visitor_team_score']].copy()
        home_games['team_id'] = home_games['home_team_id']
        home_games['opponent_id'] = home_games['visitor_team_score']
        home_games['points'] = home_games.apply(
            lambda x: 2 if x['home_team_score'] > x['visitor_team_score'] else 1,
            axis=1
        )
        home_games['is_home'] = True
        
        away_games = df[['date', 'visitor_team_id', 'home_team_score', 'visitor_team_score']].copy()
        away_games['team_id'] = away_games['visitor_team_id']
        away_games['opponent_id'] = away_games['home_team_score']
        away_games['points'] = away_games.apply(
            lambda x: 2 if x['visitor_team_score'] > x['home_team_score'] else 1,
            axis=1
        )
        away_games['is_home'] = False
        
        # Combine and sort
        all_games = pd.concat([home_games, away_games])
        all_games = all_games.sort_values(['team_id', 'date'])
        
        # Calculate rolling form
        all_games['form'] = all_games.groupby('team_id')['points'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
        
        # Pivot back to wide format
        home_form = all_games[all_games['is_home']].set_index(['date', 'team_id'])['form']
        away_form = all_games[~all_games['is_home']].set_index(['date', 'team_id'])['form']
        
        # Merge back to original dataframe
        df = df.merge(
            home_form.rename('home_team_form'),
            left_on=['date', 'home_team_id'],
            right_index=True,
            how='left'
        )
        
        df = df.merge(
            away_form.rename('visitor_team_form'),
            left_on=['date', 'visitor_team_id'],
            right_index=True,
            how='left'
        )
        
        return df
    
    def process_games(self, games_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and clean games data.
        
        Args:
            games_df: Raw games DataFrame
            
        Returns:
            Processed DataFrame with additional features
        """
        if games_df.empty:
            return games_df
        
        df = games_df.copy()
        
        # Ensure required columns exist
        required_cols = ['home_team_score', 'visitor_team_score', 'date']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns. Need: {required_cols}")
        
        # Calculate game result (1=home win, 0=away win)
        df['result'] = (df['home_team_score'] > df['visitor_team_score']).astype(int)
        
        # Calculate point spread
        df['point_spread'] = df['home_team_score'] - df['visitor_team_score']
        
        # Add team form
        df = self.calculate_team_form(df)
        
        # Add rest days since last game
        df = self.add_rest_days(df)
        
        return df
    
    def add_rest_days(self, games_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add columns for days of rest for each team before the game.
        
        Args:
            games_df: DataFrame containing game data
            
        Returns:
            DataFrame with rest days columns added
        """
        if games_df.empty:
            return games_df
            
        df = games_df.sort_values('date').copy()
        
        # Create a long format of the games
        home_games = df[['date', 'home_team_id']].copy()
        home_games['team_id'] = home_games['home_team_id']
        home_games['is_home'] = True
        
        away_games = df[['date', 'visitor_team_id']].copy()
        away_games['team_id'] = away_games['visitor_team_id']
        away_games['is_home'] = False
        
        all_games = pd.concat([home_games, away_games])
        all_games = all_games.sort_values(['team_id', 'date'])
        
        # Calculate days since last game
        all_games['prev_game_date'] = all_games.groupby('team_id')['date'].shift(1)
        all_games['rest_days'] = (all_games['date'] - all_games['prev_game_date']).dt.days - 1
        all_games['rest_days'] = all_games['rest_days'].fillna(7)  # First game of season
        
        # Pivot back to wide format
        home_rest = all_games[all_games['is_home']].set_index(['date', 'team_id'])['rest_days']
        away_rest = all_games[~all_games['is_home']].set_index(['date', 'team_id'])['rest_days']
        
        # Merge back to original dataframe
        df = df.merge(
            home_rest.rename('home_team_rest_days'),
            left_on=['date', 'home_team_id'],
            right_index=True,
            how='left'
        )
        
        df = df.merge(
            away_rest.rename('visitor_team_rest_days'),
            left_on=['date', 'visitor_team_id'],
            right_index=True,
            how='left'
        )
        
        return df
    
    def save_processed_data(self, df: pd.DataFrame, name: str) -> Path:
        """
        Save processed data to parquet file.
        
        Args:
            df: DataFrame to save
            name: Base name for the output file
            
        Returns:
            Path to the saved file
        """
        timestamp = get_timestamp_str()
        filename = f"{name}_{timestamp}.parquet"
        filepath = self.output_dir / filename
        
        ensure_dir(self.output_dir)
        df.to_parquet(filepath, index=False)
        logger.info(f"Saved processed data to {filepath}")
        
        return filepath

def main():
    """Main entry point for the NBA data transformer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform NBA data")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing raw JSON files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save processed files"
    )
    parser.add_argument(
        "--games",
        nargs="+",
        type=Path,
        help="Specific game files to process"
    )
    parser.add_argument(
        "--teams",
        action="store_true",
        help="Process teams data"
    )
    parser.add_argument(
        "--odds",
        action="store_true",
        help="Process odds data"
    )
    
    args = parser.parse_args()
    
    try:
        transformer = NbaDataTransformer(
            data_dir=args.input_dir,
            output_dir=args.output_dir
        )
        
        # Process games
        if args.games:
            games_df = transformer.load_games_data(args.games)
        else:
            games_df = transformer.load_games_data()
        
        if not games_df.empty:
            processed_games = transformer.process_games(games_df)
            transformer.save_processed_data(processed_games, "nba_games")
        
        # Process teams
        if args.teams:
            teams_df = transformer.load_teams_data()
            if not teams_df.empty:
                transformer.save_processed_data(teams_df, "nba_teams")
        
        # Process odds
        if args.odds:
            odds_df = transformer.load_odds_data()
            if not odds_df.empty:
                transformer.save_processed_data(odds_df, "nba_odds")
        
        logger.info("NBA data transformation completed successfully")
        
    except Exception as e:
        logger.error(f"Error in NBA data transformation: {e}")
        raise

if __name__ == "__main__":
    main()