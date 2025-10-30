"""
Transform NCAA basketball data into features for ML models.
Handles men's and women's basketball with no-draw outcomes.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    NCAA_API_DIR,
    PROCESSED_DATA_DIR,
    SPORT_CONFIGS,
    LOG_LEVEL,
)
from etl.utils import setup_logger, ensure_dir

logger = setup_logger(__name__, LOG_LEVEL)


class NCAATransformer:
    """Transform NCAA basketball data into ML features."""
    
    def __init__(self, sport: str):
        """
        Initialize transformer.
        
        Args:
            sport: Sport key (e.g., 'basketball-men', 'basketball-women')
        """
        self.sport = sport
        self.sport_config = SPORT_CONFIGS["basketball"]
        self.form_window = self.sport_config["form_window"]
        
    def load_raw_data(self) -> pd.DataFrame:
        """
        Load raw NCAA data from JSON files.
        
        Returns:
            DataFrame with raw game data
        """
        sport_dir = NCAA_API_DIR / self.sport
        
        if not sport_dir.exists():
            logger.warning(f"No data directory found for {self.sport}")
            return pd.DataFrame()
        
        json_files = list(sport_dir.glob("scoreboard_*.json"))
        
        if not json_files:
            logger.warning(f"No data files found for {self.sport}")
            return pd.DataFrame()
        
        all_games = []
        
        for json_file in json_files:
            import json
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            for day_data in data:
                date = day_data.get("date")
                scoreboard = day_data.get("scoreboard", {})
                games = scoreboard.get("games", [])
                
                for game in games:
                    game_data = self._parse_game(game, date)
                    if game_data:
                        all_games.append(game_data)
        
        if not all_games:
            logger.warning(f"No games parsed for {self.sport}")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_games)
        logger.info(f"Loaded {len(df)} games for {self.sport}")
        
        return df
    
    def _parse_game(self, game: Dict, date: str) -> Dict:
        """
        Parse a single game from NCAA API format.
        
        Args:
            game: Game data from API
            date: Game date string
            
        Returns:
            Parsed game dictionary
        """
        try:
            # Extract basic info
            game_id = game.get("game", {}).get("gameID")
            game_state = game.get("game", {}).get("gameState", "")
            
            # Teams
            home_team = game.get("game", {}).get("home", {})
            away_team = game.get("game", {}).get("away", {})
            
            home_name = home_team.get("names", {}).get("short", "")
            away_name = away_team.get("names", {}).get("short", "")
            
            # Scores (if game is final)
            home_score = home_team.get("score")
            away_score = away_team.get("score")
            
            # Determine result (for completed games)
            result = None
            if home_score is not None and away_score is not None:
                if home_score > away_score:
                    result = "home_win"
                else:
                    result = "away_win"
            
            # Parse date
            game_date = datetime.strptime(date, "%Y/%m/%d") if date else None
            
            return {
                "game_id": game_id,
                "date": game_date,
                "home_team": home_name,
                "away_team": away_name,
                "home_score": home_score,
                "away_score": away_score,
                "result": result,
                "game_state": game_state,
                "sport": self.sport,
            }
        except Exception as e:
            logger.error(f"Error parsing game: {str(e)}")
            return None
    
    def calculate_team_form(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate team form features (last N games).
        
        Args:
            df: DataFrame with game data
            
        Returns:
            DataFrame with form features
        """
        # Sort by date
        df = df.sort_values("date").copy()
        
        # Initialize form columns
        df["home_team_wins_last_n"] = 0
        df["home_team_losses_last_n"] = 0
        df["away_team_wins_last_n"] = 0
        df["away_team_losses_last_n"] = 0
        df["home_team_avg_score_last_n"] = 0.0
        df["away_team_avg_score_last_n"] = 0.0
        df["home_team_avg_score_diff_last_n"] = 0.0
        df["away_team_avg_score_diff_last_n"] = 0.0
        
        # Only calculate for games with results
        completed_games = df[df["result"].notna()].copy()
        
        if len(completed_games) == 0:
            return df
        
        # Calculate form for each team
        teams = pd.concat([df["home_team"], df["away_team"]]).unique()
        
        for team in teams:
            # Get team's games (home and away)
            team_home = completed_games[completed_games["home_team"] == team].copy()
            team_away = completed_games[completed_games["away_team"] == team].copy()
            
            # Calculate rolling stats for home games
            for idx in team_home.index:
                prev_games = self._get_previous_games(completed_games, team, df.loc[idx, "date"], self.form_window)
                if len(prev_games) > 0:
                    df.loc[idx, "home_team_wins_last_n"] = prev_games["wins"]
                    df.loc[idx, "home_team_losses_last_n"] = prev_games["losses"]
                    df.loc[idx, "home_team_avg_score_last_n"] = prev_games["avg_score"]
                    df.loc[idx, "home_team_avg_score_diff_last_n"] = prev_games["avg_diff"]
            
            # Calculate rolling stats for away games
            for idx in team_away.index:
                prev_games = self._get_previous_games(completed_games, team, df.loc[idx, "date"], self.form_window)
                if len(prev_games) > 0:
                    df.loc[idx, "away_team_wins_last_n"] = prev_games["wins"]
                    df.loc[idx, "away_team_losses_last_n"] = prev_games["losses"]
                    df.loc[idx, "away_team_avg_score_last_n"] = prev_games["avg_score"]
                    df.loc[idx, "away_team_avg_score_diff_last_n"] = prev_games["avg_diff"]
        
        return df
    
    def _get_previous_games(
        self,
        df: pd.DataFrame,
        team: str,
        current_date: datetime,
        n: int
    ) -> Dict:
        """
        Get statistics from team's previous N games.
        
        Args:
            df: DataFrame with completed games
            team: Team name
            current_date: Current game date
            n: Number of previous games to consider
            
        Returns:
            Dictionary with team statistics
        """
        # Get team's previous games (both home and away)
        team_games = df[
            ((df["home_team"] == team) | (df["away_team"] == team)) &
            (df["date"] < current_date)
        ].tail(n)
        
        if len(team_games) == 0:
            return {"wins": 0, "losses": 0, "avg_score": 0.0, "avg_diff": 0.0}
        
        wins = 0
        scores = []
        diffs = []
        
        for _, game in team_games.iterrows():
            is_home = game["home_team"] == team
            
            if is_home:
                team_score = game["home_score"]
                opp_score = game["away_score"]
                won = game["result"] == "home_win"
            else:
                team_score = game["away_score"]
                opp_score = game["home_score"]
                won = game["result"] == "away_win"
            
            if won:
                wins += 1
            
            scores.append(team_score)
            diffs.append(team_score - opp_score)
        
        return {
            "wins": wins,
            "losses": len(team_games) - wins,
            "avg_score": np.mean(scores),
            "avg_diff": np.mean(diffs),
        }
    
    def transform(self) -> pd.DataFrame:
        """
        Full transformation pipeline.
        
        Returns:
            Transformed DataFrame with features
        """
        logger.info(f"Starting transformation for {self.sport}")
        
        # Load raw data
        df = self.load_raw_data()
        
        if df.empty:
            logger.warning("No data to transform")
            return df
        
        # Calculate team form
        df = self.calculate_team_form(df)
        
        # Add sport identifier
        df["sport_type"] = "basketball"
        
        logger.info(f"Transformation complete: {len(df)} games processed")
        
        return df
    
    def save_processed_data(self, df: pd.DataFrame):
        """
        Save processed data to parquet.
        
        Args:
            df: Processed DataFrame
        """
        ensure_dir(PROCESSED_DATA_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = PROCESSED_DATA_DIR / f"matches_ncaa_{self.sport}_{timestamp}.parquet"
        
        df.to_parquet(filename, index=False)
        logger.info(f"Saved processed data to {filename}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform NCAA basketball data")
    parser.add_argument(
        "--sport",
        choices=["basketball-men", "basketball-women", "all"],
        default="all",
        help="Sport to transform (default: all)"
    )
    
    args = parser.parse_args()
    
    try:
        sports = ["basketball-men", "basketball-women"] if args.sport == "all" else [args.sport]
        
        for sport in sports:
            logger.info(f"=" * 60)
            logger.info(f"Transforming {sport}")
            logger.info(f"=" * 60)
            
            transformer = NCAATransformer(sport)
            df = transformer.transform()
            
            if not df.empty:
                transformer.save_processed_data(df)
                logger.info(f"✓ Successfully transformed {sport}")
            else:
                logger.warning(f"No data to save for {sport}")
        
        logger.info("NCAA data transformation completed successfully")
    except Exception as e:
        logger.error(f"NCAA data transformation failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
