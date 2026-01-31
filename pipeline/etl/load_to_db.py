"""
Load processed data into PostgreSQL database.
Implements upsert logic for idempotency.
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Set

import pandas as pd
from colorama import init, Fore, Style
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Initialize colorama
init()

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    DATABASE_URI,
    PROCESSED_DATA_DIR,
    LOG_LEVEL,
    NBA_DATA_DIR
)

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
PIPELINE_LOG_PATH = LOGS_DIR / "pipeline_loader.log"

# Custom formatter for colored logs
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
            record.msg = f"{self.COLORS[levelname]}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

def setup_colored_logger():
    """Set up a logger with colored output"""
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with color formatter
    console = logging.StreamHandler()
    formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', 
                               datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler for structured logging
    file_handler = logging.FileHandler(PIPELINE_LOG_PATH, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_colored_logger()


def ensure_table_columns(engine, table_name: str, columns_definition: Dict[str, str]) -> None:
    """Ensure required columns exist on a table, adding them if missing."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table(table_name):
            return
        existing_columns: Set[str] = {col['name'] for col in inspector.get_columns(table_name)}
    except Exception as exc:
        logger.warning(f"Could not inspect table {table_name}: {exc}")
        return

    missing_columns = {
        column_name: ddl
        for column_name, ddl in columns_definition.items()
        if column_name not in existing_columns
    }

    if not missing_columns:
        return

    with engine.begin() as conn:
        for column_name, ddl in missing_columns.items():
            conn.execute(text(
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {ddl}"
            ))
            logger.info(f"Added missing column '{column_name}' to {table_name}")


def ensure_nba_table_schema(engine) -> None:
    """Patch legacy nba_games tables missing new columns."""
    nba_columns = {
        'sport_key': "VARCHAR(50)",
        'sport': "VARCHAR(50) NOT NULL DEFAULT 'BASKETBALL'",
        'sport_title': "VARCHAR(100)",
        'commence_time': "TIMESTAMP",
        'home_team': "VARCHAR(100)",
        'away_team': "VARCHAR(100)",
        'home_score': "INTEGER",
        'away_score': "INTEGER",
        'completed': "BOOLEAN",
        'last_update': "TIMESTAMP",
        'source_file': "VARCHAR(255)",
        'created_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        'updated_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
    ensure_table_columns(engine, 'nba_games', nba_columns)


def ensure_schema_exists(engine) -> None:
    """
    Ensure all required tables exist in the database.
    Creates tables if they don't exist.
    """
    schema_sql = """
    -- Matches table (supports both football and basketball)
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY,
        sport_type TEXT DEFAULT 'football',
        competition TEXT,
        season DATE,
        date TIMESTAMP,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        home_score INTEGER,
        away_score INTEGER,
        result TEXT,
        home_shots INTEGER,
        away_shots INTEGER,
        home_possession FLOAT,
        away_possession FLOAT,
        home_corners INTEGER,
        away_corners INTEGER,
        home_yellow_cards INTEGER,
        away_yellow_cards INTEGER,
        home_red_cards INTEGER,
        away_red_cards INTEGER,
        home_xg FLOAT,
        away_xg FLOAT,
        venue TEXT,
        referee TEXT,
        attendance INTEGER,
        status TEXT,
        data_source TEXT,
        home_team_wins_last_n INTEGER DEFAULT 0,
        home_team_draws_last_n INTEGER DEFAULT 0,
        home_team_losses_last_n INTEGER DEFAULT 0,
        away_team_wins_last_n INTEGER DEFAULT 0,
        away_team_draws_last_n INTEGER DEFAULT 0,
        away_team_losses_last_n INTEGER DEFAULT 0,
        home_team_avg_gd_last_n FLOAT DEFAULT 0.0,
        away_team_avg_gd_last_n FLOAT DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Odds table
    CREATE TABLE IF NOT EXISTS odds (
        id SERIAL PRIMARY KEY,
        match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
        bookmaker TEXT NOT NULL,
        home_win FLOAT,
        draw FLOAT,
        away_win FLOAT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Predictions table
    CREATE TABLE IF NOT EXISTS predictions (
        id SERIAL PRIMARY KEY,
        match_id INTEGER REFERENCES matches(match_id) ON DELETE CASCADE,
        model_version TEXT NOT NULL,
        winner TEXT NOT NULL,
        home_prob FLOAT NOT NULL,
        draw_prob FLOAT NOT NULL,
        away_prob FLOAT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- NBA games table
    CREATE TABLE IF NOT EXISTS nba_games (
        game_id VARCHAR(100) PRIMARY KEY,
        sport_key VARCHAR(50),
        sport VARCHAR(50) NOT NULL DEFAULT 'BASKETBALL',
        sport_title VARCHAR(100),
        commence_time TIMESTAMP,
        home_team VARCHAR(100),
        away_team VARCHAR(100),
        home_score INTEGER,
        away_score INTEGER,
        completed BOOLEAN,
        last_update TIMESTAMP,
        source_file VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes if they don't exist
    CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
    CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
    CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team);
    CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team);
    CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds(match_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
    """
    
    try:
        with engine.begin() as conn:
            # Execute each statement separately
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
        logger.info("✅ Database schema verified/created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {e}")
        raise


def get_db_engine():
    """
    Create SQLAlchemy database engine and ensure schema exists.
    
    Returns:
        SQLAlchemy engine
    """
    engine = create_engine(DATABASE_URI)
    ensure_schema_exists(engine)
    return engine


def prepare_dataframe(df: pd.DataFrame, id_column: str, date_columns: list = None) -> pd.DataFrame:
    """
    Prepare DataFrame for database operations by handling duplicates and data types.
    
    Args:
        df: Input DataFrame
        id_column: Name of the ID column to check for duplicates
        date_columns: List of columns to convert to datetime
        
    Returns:
        Processed DataFrame with duplicates removed and proper data types
    """
    if df.empty:
        return df
        
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Remove duplicates based on ID column
    initial_count = len(df)
    df = df.drop_duplicates(subset=[id_column], keep='last')
    
    if len(df) < initial_count:
        logger.warning(f"Removed {initial_count - len(df)} duplicate {id_column}s")
    
    # Convert date columns
    if date_columns:
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df

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
    
    # Filter to only existing columns and handle duplicates
    available_columns = [col for col in columns if col in df.columns]
    df_to_load = prepare_dataframe(
        df[available_columns], 
        id_column="match_id",
        date_columns=["date", "season"]
    )

    # Drop rows with null match_id to satisfy NOT NULL constraint in the database
    if "match_id" in df_to_load.columns:
        before_count = len(df_to_load)
        df_to_load = df_to_load[df_to_load["match_id"].notna()]
        dropped_null_ids = before_count - len(df_to_load)
        if dropped_null_ids > 0:
            logger.warning(f"Dropped {dropped_null_ids} rows with null match_id before upsert")
    
    if df_to_load.empty:
        logger.warning("No valid matches data to load after processing")
        return
    
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
            
            # Upsert from temp table in smaller batches to avoid the cardinality violation
            batch_size = 1000
            total_rows = len(df_to_load)
            
            for i in range(0, total_rows, batch_size):
                batch = df_to_load.iloc[i:i+batch_size]
                
                # Create a temp table for this batch
                batch.to_sql("matches_temp_batch", conn, if_exists="replace", index=False)
                
                # Execute upsert for this batch
                upsert_query = text(f"""
                    INSERT INTO matches ({col_list})
                    SELECT {col_list} FROM matches_temp_batch
                    ON CONFLICT (match_id) DO UPDATE SET
                    {update_cols}
                """)
                conn.execute(upsert_query)
                
                # Clean up
                conn.execute(text("DROP TABLE IF EXISTS matches_temp_batch"))
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(total_rows + batch_size - 1)//batch_size}")
            
            # Clean up the main temp table
            conn.execute(text("DROP TABLE IF EXISTS matches_temp"))
        
        logger.info(f"Successfully upserted {len(df_to_load)} matches into database")
    
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


def upsert_nba_games(df: pd.DataFrame, engine) -> None:
    """
    Upsert NBA games data into database.
    
    Args:
        df: DataFrame with NBA games data
        engine: SQLAlchemy engine
    """
    # Define required columns with their default values
    required_columns = {
        'game_id': None,  # Required, no default
        'sport_key': 'basketball_nba',  # Keep original for API compatibility
        'sport': 'BASKETBALL',  # Standardized sport type for internal use
        'sport_title': 'NBA Basketball',
        'commence_time': None,  # Required, no default
        'home_team': '',
        'away_team': '',
        'home_score': None,
        'away_score': None,
        'completed': False,
        'last_update': None,
        'source_file': ''
    }
    
    # Handle empty DataFrame
    if df.empty:
        logger.warning("No NBA games data to load")
        return
    
    # Make a copy of the input DataFrame
    df_to_load = df.copy()
    
    # Ensure all required columns exist with default values
    for col, default in required_columns.items():
        if col not in df_to_load.columns and col != 'game_id' and col != 'commence_time':
            df_to_load[col] = default
    
    # Convert score columns to numeric, coercing errors to NaN
    for score_col in ['home_score', 'away_score']:
        if score_col in df_to_load.columns:
            df_to_load[score_col] = pd.to_numeric(df_to_load[score_col], errors='coerce')
    
    # Prepare the data - handle duplicates and convert data types
    df_to_load = prepare_dataframe(
        df_to_load,
        id_column='game_id',
        date_columns=['commence_time', 'last_update']
    )
    
    # Filter to only include required columns that exist in the DataFrame
    available_columns = [col for col in required_columns.keys() if col in df_to_load.columns]
    
    # Ensure required columns are present
    if 'game_id' not in available_columns or 'commence_time' not in available_columns:
        logger.error("Missing required columns in NBA games data")
        return
    
    df_to_load = df_to_load[available_columns]
    
    if df_to_load.empty:
        logger.warning("No valid NBA games data to load after processing")
        return

    try:
        ensure_nba_table_schema(engine)
        with engine.begin() as conn:
            # Create the nba_games table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS nba_games (
                    game_id VARCHAR(100) PRIMARY KEY,
                    sport_key VARCHAR(50),
                    sport VARCHAR(50) NOT NULL DEFAULT 'BASKETBALL',
                    sport_title VARCHAR(100),
                    commence_time TIMESTAMP,
                    home_team VARCHAR(100),
                    away_team VARCHAR(100),
                    home_score INTEGER,
                    away_score INTEGER,
                    completed BOOLEAN,
                    last_update TIMESTAMP,
                    source_file VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create a temporary table for the current batch
            temp_table_name = "nba_games_temp"
            df_to_load.to_sql(
                temp_table_name,
                conn,
                if_exists="replace",
                index=False
            )
            
            # Build the upsert query
            col_list = ", ".join(available_columns)
            update_cols = ", ".join([
                f"{col} = EXCLUDED.{col}"
                for col in available_columns
                if col != "game_id"
            ])
            
            # Add updated_at to the update columns
            update_cols += ", updated_at = CURRENT_TIMESTAMP"
            
            # Execute the upsert in batches to avoid locking issues
            batch_size = 1000
            total_rows = len(df_to_load)
            
            for i in range(0, total_rows, batch_size):
                batch = df_to_load.iloc[i:i+batch_size]
                
                # Create a temp table for this batch
                batch.to_sql("nba_games_temp_batch", conn, if_exists="replace", index=False)
                
                # Execute upsert for this batch
                upsert_query = text(f"""
                    INSERT INTO nba_games ({col_list})
                    SELECT {col_list} FROM nba_games_temp_batch
                    ON CONFLICT (game_id) DO UPDATE SET
                    {update_cols}
                """)
                conn.execute(upsert_query)
                
                # Clean up the batch temp table
                conn.execute(text("DROP TABLE IF EXISTS nba_games_temp_batch"))
                
                logger.info(f"Processed NBA games batch {i//batch_size + 1}/{(total_rows + batch_size - 1)//batch_size}")
            
            # Clean up the main temp table
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))
        
        logger.info(f"Successfully upserted {len(df_to_load)} NBA games into database")
    
    except SQLAlchemyError as e:
        logger.error(f"❌ {Fore.RED}Failed to upsert NBA games: {str(e)}{Style.RESET_ALL}", exc_info=True)
        raise

def load_latest_processed_data() -> None:
    """Load the most recent processed data files into database."""
    logger.info(f"🚀 {Fore.CYAN}Starting database load{Style.RESET_ALL}")
    logger.info(f"📂 {Fore.CYAN}Processing directory: {PROCESSED_DATA_DIR}{Style.RESET_ALL}")
    
    try:
        engine = get_db_engine()
        
        # Find latest processed files
        matches_files = sorted(PROCESSED_DATA_DIR.glob("matches_*.parquet"), key=os.path.getmtime)
        odds_files = sorted(PROCESSED_DATA_DIR.glob("odds_*.parquet"), key=os.path.getmtime)
        nba_odds_files = sorted(PROCESSED_DATA_DIR.glob("nba_odds_*.parquet"), key=os.path.getmtime)
        nba_scores_files = sorted(PROCESSED_DATA_DIR.glob("nba_scores_*.parquet"), key=os.path.getmtime)
        
        # Load football matches if available
        if matches_files:
            latest_matches_file = matches_files[-1]
            logger.info(f"📥 {Fore.BLUE}Loading matches from {latest_matches_file}{Style.RESET_ALL}")
            try:
                matches_df = pd.read_parquet(latest_matches_file)
                logger.info(f"✅ {Fore.GREEN}Read {Fore.CYAN}{len(matches_df)} matches{Style.RESET_ALL} from file")
                upsert_matches(matches_df, engine)
            except Exception as e:
                logger.error(f"❌ {Fore.RED}Error processing matches file {latest_matches_file}: {str(e)}{Style.RESET_ALL}", exc_info=True)
        else:
            logger.warning(f"⚠️  {Fore.YELLOW}No matches files found{Style.RESET_ALL}")
        
        # Load football odds if available
        if odds_files:
            latest_odds_file = odds_files[-1]
            logger.info(f"🎲 {Fore.BLUE}Loading odds from {latest_odds_file}{Style.RESET_ALL}")
            try:
                odds_df = pd.read_parquet(latest_odds_file)
                logger.info(f"✅ {Fore.GREEN}Read {Fore.CYAN}{len(odds_df)} odds records{Style.RESET_ALL} from file")
                upsert_odds(odds_df, engine)
            except Exception as e:
                logger.error(f"❌ {Fore.RED}Error processing odds file {latest_odds_file}: {str(e)}{Style.RESET_ALL}", exc_info=True)
        else:
            logger.warning(f"⚠️  {Fore.YELLOW}No odds files found{Style.RESET_ALL}")
        
        # Load NBA odds if available
        if nba_odds_files:
            latest_nba_odds_file = nba_odds_files[-1]
            logger.info(f"🏀 {Fore.BLUE}Loading NBA odds from {latest_nba_odds_file}{Style.RESET_ALL}")
            try:
                nba_odds_df = pd.read_parquet(latest_nba_odds_file)
                logger.info(f"✅ {Fore.GREEN}Read {Fore.CYAN}{len(nba_odds_df)} NBA odds records{Style.RESET_ALL} from file")
                # We'll handle NBA odds in a future update
                logger.info(f"ℹ️  {Fore.CYAN}NBA odds loading not yet implemented{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"❌ {Fore.RED}Error processing NBA odds file {latest_nba_odds_file}: {str(e)}{Style.RESET_ALL}", exc_info=True)
        else:
            logger.warning(f"⚠️  {Fore.YELLOW}No NBA odds files found{Style.RESET_ALL}")
        
        # Load NBA scores if available
        if nba_scores_files:
            latest_nba_scores_file = nba_scores_files[-1]
            logger.info(f"🏀 {Fore.BLUE}Loading NBA scores from {latest_nba_scores_file}{Style.RESET_ALL}")
            try:
                nba_scores_df = pd.read_parquet(latest_nba_scores_file)
                logger.info(f"✅ {Fore.GREEN}Read {Fore.CYAN}{len(nba_scores_df)} NBA scores{Style.RESET_ALL} from file")
                
                # Transform the scores data to match our expected format
                nba_scores_df = nba_scores_df.rename(columns={
                    'id': 'game_id',
                    'scores': 'game_scores',  # Store raw scores as JSON
                })
                
                # Try to extract home and away scores if available
                if 'home_score' not in nba_scores_df.columns and 'game_scores' in nba_scores_df.columns:
                    try:
                        # Try to parse the scores JSON if it exists
                        scores_data = nba_scores_df['game_scores'].apply(
                            lambda x: json.loads(x) if isinstance(x, str) else x
                        )
                        
                        # Extract home and away scores if available in the scores data
                        if scores_data.apply(lambda x: isinstance(x, list) and len(x) > 0).any():
                            nba_scores_df['home_score'] = scores_data.apply(
                                lambda x: x[0].get('score') if isinstance(x, list) and len(x) > 0 else None
                            )
                            nba_scores_df['away_score'] = scores_data.apply(
                                lambda x: x[1].get('score') if isinstance(x, list) and len(x) > 1 else None
                            )
                    except Exception as e:
                        logger.warning(f"⚠️  {Fore.YELLOW}Could not parse scores data: {str(e)}{Style.RESET_ALL}")
                
                upsert_nba_games(nba_scores_df, engine)
                
            except Exception as e:
                logger.error(f"❌ {Fore.RED}Error processing NBA scores file {latest_nba_scores_file}: {str(e)}{Style.RESET_ALL}", exc_info=True)
        else:
            logger.warning(f"⚠️  {Fore.YELLOW}No NBA scores files found{Style.RESET_ALL}")
        
        logger.info(f"✨ {Fore.GREEN}Database load completed successfully!{Style.RESET_ALL}")
        
    except Exception as e:
        logger.error(f"💥 {Fore.RED}Fatal error in load_latest_processed_data: {str(e)}{Style.RESET_ALL}", exc_info=True)
        raise


def main() -> None:
    """Main entry point."""
    try:
        load_latest_processed_data()
    except Exception as e:
        logger.error(f"❌ {Fore.RED}Database load failed: {str(e)}{Style.RESET_ALL}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
