"""
Load processed data into PostgreSQL database.
Implements upsert logic for idempotency.
"""

import sys
from pathlib import Path
from typing import List

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from config import DATABASE_URI, PROCESSED_DATA_DIR, LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


def get_db_engine():
    """
    Create SQLAlchemy database engine.
    
    Returns:
        SQLAlchemy engine
    """
    return create_engine(DATABASE_URI)


def upsert_matches(df: pd.DataFrame, engine) -> None:
    """
    Upsert matches data into database.
    
    Args:
        df: DataFrame with matches data
        engine: SQLAlchemy engine
    """
    if df.empty:
        logger.warning("No matches data to load")
        return
    
    # Select columns that exist in the matches table
    columns = [
        "match_id", "competition", "season", "date", "home_team", "away_team",
        "home_score", "away_score", "result", "status", "data_source",
        "venue", "referee"
    ]
    
    # Filter to only existing columns
    available_columns = [col for col in columns if col in df.columns]
    df_to_load = df[available_columns].copy()
    
    # Convert date columns
    if "date" in df_to_load.columns:
        df_to_load["date"] = pd.to_datetime(df_to_load["date"])
    if "season" in df_to_load.columns:
        df_to_load["season"] = pd.to_datetime(df_to_load["season"], errors="coerce")
    
    try:
        with engine.begin() as conn:
            # Create temporary table
            df_to_load.to_sql(
                "matches_temp",
                conn,
                if_exists="replace",
                index=False,
                method="multi"
            )
            
            # Build column list for upsert
            col_list = ", ".join(available_columns)
            update_cols = ", ".join([
                f"{col} = EXCLUDED.{col}"
                for col in available_columns
                if col != "match_id"
            ])
            
            # Upsert from temp table
            upsert_query = text(f"""
                INSERT INTO matches ({col_list})
                SELECT {col_list} FROM matches_temp
                ON CONFLICT (match_id) DO UPDATE SET
                {update_cols}
            """)
            
            conn.execute(upsert_query)
            conn.execute(text("DROP TABLE matches_temp"))
        
        logger.info(f"Upserted {len(df_to_load)} matches into database")
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to upsert matches: {str(e)}", exc_info=True)
        raise


def upsert_odds(df: pd.DataFrame, engine) -> None:
    """
    Upsert odds data into database.
    
    Args:
        df: DataFrame with odds data
        engine: SQLAlchemy engine
    """
    if df.empty:
        logger.warning("No odds data to load")
        return
    
    # Prepare data
    df_to_load = df.copy()
    
    # Map match by home_team and away_team to get match_id
    # This is a simplified approach - in production, you'd need better matching logic
    try:
        with engine.begin() as conn:
            # Get match IDs
            matches = pd.read_sql("SELECT match_id, home_team, away_team FROM matches", conn)
            
            # Merge to get match_id
            df_to_load = df_to_load.merge(
                matches[["match_id", "home_team", "away_team"]],
                on=["home_team", "away_team"],
                how="inner"
            )
            
            if df_to_load.empty:
                logger.warning("No matching matches found for odds data")
                return
            
            # Select columns for odds table
            odds_columns = ["match_id", "bookmaker", "home_win", "draw", "away_win", "updated_at"]
            df_to_load = df_to_load[[col for col in odds_columns if col in df_to_load.columns]]
            
            # Convert timestamp
            if "updated_at" in df_to_load.columns:
                df_to_load["updated_at"] = pd.to_datetime(df_to_load["updated_at"], errors="coerce")
            
            # Insert odds (no conflict resolution needed as id is SERIAL)
            df_to_load.to_sql(
                "odds",
                conn,
                if_exists="append",
                index=False,
                method="multi"
            )
        
        logger.info(f"Inserted {len(df_to_load)} odds records into database")
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to upsert odds: {str(e)}", exc_info=True)
        raise


def load_latest_processed_data() -> None:
    """Load the most recent processed data files into database."""
    logger.info("Starting database load")
    
    engine = get_db_engine()
    
    # Find latest processed files
    matches_files = sorted(PROCESSED_DATA_DIR.glob("matches_*.parquet"))
    odds_files = sorted(PROCESSED_DATA_DIR.glob("odds_*.parquet"))
    
    if not matches_files:
        logger.warning("No processed matches files found")
        return
    
    # Load latest matches
    latest_matches_file = matches_files[-1]
    logger.info(f"Loading matches from {latest_matches_file}")
    matches_df = pd.read_parquet(latest_matches_file)
    upsert_matches(matches_df, engine)
    
    # Load latest odds if available
    if odds_files:
        latest_odds_file = odds_files[-1]
        logger.info(f"Loading odds from {latest_odds_file}")
        odds_df = pd.read_parquet(latest_odds_file)
        upsert_odds(odds_df, engine)
    
    logger.info("Database load completed")


def main() -> None:
    """Main entry point."""
    try:
        load_latest_processed_data()
    except Exception as e:
        logger.error(f"Database load failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
