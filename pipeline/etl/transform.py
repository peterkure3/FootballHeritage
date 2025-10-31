"""
Transform raw JSON/CSV data into processed Parquet files.
Normalize data, engineer features, and prepare for database loading.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    FOOTBALL_DATA_ORG_DIR,
    THE_ODDS_API_DIR,
    HISTORICAL_CSV_DIR,
    PROCESSED_DATA_DIR,
    TEAM_FORM_WINDOW,
    LOG_LEVEL,
)
from etl.utils import (
    setup_logger,
    load_json,
    ensure_dir,
    get_timestamp_str,
)

logger = setup_logger(__name__, LOG_LEVEL)


def normalize_football_data_org_matches(json_files: List[Path]) -> pd.DataFrame:
    """
    Normalize football-data.org match JSON files to DataFrame.
    
    Args:
        json_files: List of JSON file paths
    
    Returns:
        Normalized DataFrame
    """
    all_matches = []
    
    for json_file in json_files:
        try:
            data = load_json(json_file)
            matches = data.get("matches", [])
            
            for match in matches:
                normalized = {
                    "match_id": match.get("id"),
                    "competition": match.get("competition", {}).get("name"),
                    "season": match.get("season", {}).get("startDate"),
                    "date": match.get("utcDate"),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "home_score": match.get("score", {}).get("fullTime", {}).get("home"),
                    "away_score": match.get("score", {}).get("fullTime", {}).get("away"),
                    "status": match.get("status"),
                    "venue": match.get("venue"),
                    "referee": match.get("referees", [{}])[0].get("name") if match.get("referees") else None,
                    "data_source": "football_data_org",
                }
                
                # Calculate result
                if normalized["home_score"] is not None and normalized["away_score"] is not None:
                    if normalized["home_score"] > normalized["away_score"]:
                        normalized["result"] = "home_win"
                    elif normalized["home_score"] < normalized["away_score"]:
                        normalized["result"] = "away_win"
                    else:
                        normalized["result"] = "draw"
                else:
                    normalized["result"] = None
                
                all_matches.append(normalized)
        
        except Exception as e:
            logger.error(f"Error processing {json_file}: {str(e)}")
    
    df = pd.DataFrame(all_matches)
    logger.info(f"Normalized {len(df)} matches from football-data.org")
    return df


def normalize_the_odds_api_odds(json_files: List[Path]) -> pd.DataFrame:
    """
    Normalize The Odds API odds JSON files to DataFrame.
    
    Args:
        json_files: List of JSON file paths
    
    Returns:
        Normalized DataFrame
    """
    all_odds = []
    
    for json_file in json_files:
        try:
            data = load_json(json_file)
            events = data.get("events", [])
            fetched_at = data.get("fetched_at")
            
            for event in events:
                event_id = event.get("id")
                home_team = event.get("home_team")
                away_team = event.get("away_team")
                commence_time = event.get("commence_time")
                
                for bookmaker in event.get("bookmakers", []):
                    bookmaker_name = bookmaker.get("key")
                    
                    for market in bookmaker.get("markets", []):
                        if market.get("key") == "h2h":
                            outcomes = market.get("outcomes", [])
                            
                            odds_dict = {
                                "match_id": event_id,
                                "home_team": home_team,
                                "away_team": away_team,
                                "commence_time": commence_time,
                                "bookmaker": bookmaker_name,
                                "updated_at": fetched_at,
                            }
                            
                            for outcome in outcomes:
                                name = outcome.get("name")
                                price = outcome.get("price")
                                
                                if name == home_team:
                                    odds_dict["home_win"] = price
                                elif name == away_team:
                                    odds_dict["away_win"] = price
                                elif name == "Draw":
                                    odds_dict["draw"] = price
                            
                            all_odds.append(odds_dict)
        
        except Exception as e:
            logger.error(f"Error processing {json_file}: {str(e)}")
    
    df = pd.DataFrame(all_odds)
    logger.info(f"Normalized {len(df)} odds records from The Odds API")
    return df


def load_historical_csvs() -> pd.DataFrame:
    """
    Load historical CSV files.
    
    Returns:
        Combined DataFrame from all CSVs
    """
    csv_files = list(HISTORICAL_CSV_DIR.glob("*.csv"))
    
    if not csv_files:
        logger.warning("No historical CSV files found")
        return pd.DataFrame()
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df["data_source"] = "historical_csv"
            dfs.append(df)
        except Exception as e:
            logger.error(f"Error loading {csv_file}: {str(e)}")
    
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"Loaded {len(combined)} records from {len(dfs)} CSV files")
        return combined
    
    return pd.DataFrame()


def calculate_team_form(df: pd.DataFrame, window: int = TEAM_FORM_WINDOW) -> pd.DataFrame:
    """
    Calculate team form (wins, draws, losses) over last N matches.
    
    Args:
        df: DataFrame with match data
        window: Number of recent matches to consider
    
    Returns:
        DataFrame with form features added
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors='coerce', utc=True).dt.tz_localize(None)
    df = df.sort_values("date")
    
    # Initialize form columns
    df["home_team_wins_last_n"] = 0
    df["home_team_draws_last_n"] = 0
    df["home_team_losses_last_n"] = 0
    df["away_team_wins_last_n"] = 0
    df["away_team_draws_last_n"] = 0
    df["away_team_losses_last_n"] = 0
    
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    
    for team in teams:
        # Get all matches for this team
        team_matches = df[
            (df["home_team"] == team) | (df["away_team"] == team)
        ].copy()
        
        if len(team_matches) < window:
            continue
        
        for idx in team_matches.index:
            # Get previous N matches
            prev_matches = team_matches[team_matches["date"] < df.loc[idx, "date"]].tail(window)
            
            if len(prev_matches) == 0:
                continue
            
            wins = 0
            draws = 0
            losses = 0
            
            for _, match in prev_matches.iterrows():
                if match["result"] is None:
                    continue
                
                if match["home_team"] == team:
                    if match["result"] == "home_win":
                        wins += 1
                    elif match["result"] == "draw":
                        draws += 1
                    else:
                        losses += 1
                else:  # away team
                    if match["result"] == "away_win":
                        wins += 1
                    elif match["result"] == "draw":
                        draws += 1
                    else:
                        losses += 1
            
            # Update form for this match
            if df.loc[idx, "home_team"] == team:
                df.loc[idx, "home_team_wins_last_n"] = wins
                df.loc[idx, "home_team_draws_last_n"] = draws
                df.loc[idx, "home_team_losses_last_n"] = losses
            else:
                df.loc[idx, "away_team_wins_last_n"] = wins
                df.loc[idx, "away_team_draws_last_n"] = draws
                df.loc[idx, "away_team_losses_last_n"] = losses
    
    logger.info(f"Calculated team form for {len(teams)} teams")
    return df


def calculate_goal_difference(df: pd.DataFrame, window: int = TEAM_FORM_WINDOW) -> pd.DataFrame:
    """
    Calculate average goal difference over last N matches.
    
    Args:
        df: DataFrame with match data
        window: Number of recent matches to consider
    
    Returns:
        DataFrame with goal difference features added
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors='coerce', utc=True).dt.tz_localize(None)
    df = df.sort_values("date")
    
    df["home_team_avg_gd_last_n"] = 0.0
    df["away_team_avg_gd_last_n"] = 0.0
    
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    
    for team in teams:
        team_matches = df[
            (df["home_team"] == team) | (df["away_team"] == team)
        ].copy()
        
        if len(team_matches) < window:
            continue
        
        for idx in team_matches.index:
            prev_matches = team_matches[team_matches["date"] < df.loc[idx, "date"]].tail(window)
            
            if len(prev_matches) == 0:
                continue
            
            goal_diffs = []
            
            for _, match in prev_matches.iterrows():
                if pd.isna(match["home_score"]) or pd.isna(match["away_score"]):
                    continue
                
                if match["home_team"] == team:
                    gd = match["home_score"] - match["away_score"]
                else:
                    gd = match["away_score"] - match["home_score"]
                
                goal_diffs.append(gd)
            
            if goal_diffs:
                avg_gd = np.mean(goal_diffs)
                
                if df.loc[idx, "home_team"] == team:
                    df.loc[idx, "home_team_avg_gd_last_n"] = avg_gd
                else:
                    df.loc[idx, "away_team_avg_gd_last_n"] = avg_gd
    
    logger.info(f"Calculated goal difference for {len(teams)} teams")
    return df


def merge_odds_with_matches(matches_df: pd.DataFrame, odds_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge odds data with matches data.
    
    Args:
        matches_df: DataFrame with match data
        odds_df: DataFrame with odds data
    
    Returns:
        Merged DataFrame
    """
    if odds_df.empty:
        logger.warning("No odds data to merge")
        return matches_df
    
    # Group odds by match and calculate average
    avg_odds = odds_df.groupby(["home_team", "away_team"]).agg({
        "home_win": "mean",
        "draw": "mean",
        "away_win": "mean",
    }).reset_index()
    
    # Merge with matches
    merged = matches_df.merge(
        avg_odds,
        on=["home_team", "away_team"],
        how="left"
    )
    
    # Calculate odds spread
    merged["odds_spread"] = merged["home_win"] - merged["away_win"]
    
    logger.info(f"Merged odds data with {len(merged)} matches")
    return merged


def transform_data() -> None:
    """Main transformation pipeline."""
    logger.info("Starting data transformation")
    
    ensure_dir(PROCESSED_DATA_DIR)
    
    # Load raw data
    football_data_files = list(FOOTBALL_DATA_ORG_DIR.glob("matches_*.json"))
    odds_files = list(THE_ODDS_API_DIR.glob("odds_*.json"))
    
    # Normalize data
    matches_df = normalize_football_data_org_matches(football_data_files)
    odds_df = normalize_the_odds_api_odds(odds_files)
    historical_df = load_historical_csvs()
    
    # Combine matches
    if not historical_df.empty:
        matches_df = pd.concat([matches_df, historical_df], ignore_index=True)
    
    if matches_df.empty:
        logger.warning("No match data to transform")
        return
    
    # Remove rows without match_id (required for database)
    matches_df = matches_df[matches_df["match_id"].notna()].copy()
    
    # Remove duplicates
    matches_df = matches_df.drop_duplicates(subset=["match_id"], keep="last")
    
    # Engineer features
    matches_df = calculate_team_form(matches_df)
    matches_df = calculate_goal_difference(matches_df)
    matches_df = merge_odds_with_matches(matches_df, odds_df)
    
    # Save processed data
    timestamp = get_timestamp_str("%Y-%m-%d")
    matches_output = PROCESSED_DATA_DIR / f"matches_{timestamp}.parquet"
    matches_df.to_parquet(matches_output, index=False)
    logger.info(f"Saved {len(matches_df)} processed matches to {matches_output}")
    
    if not odds_df.empty:
        odds_output = PROCESSED_DATA_DIR / f"odds_{timestamp}.parquet"
        odds_df.to_parquet(odds_output, index=False)
        logger.info(f"Saved {len(odds_df)} odds records to {odds_output}")
    
    logger.info("Data transformation completed")


def main() -> None:
    """Main entry point."""
    try:
        transform_data()
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
