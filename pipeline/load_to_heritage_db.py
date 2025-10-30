"""
Load data from the current database to football_heritage database.
This script copies matches, odds, and predictions to a new database.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from config import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, LOG_LEVEL
)
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

# Source database (current)
SOURCE_DB = "football_betting"
SOURCE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{SOURCE_DB}"

# Target database (new)
TARGET_DB = "football_heritage"
TARGET_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB}"


def create_target_database():
    """Create the football_heritage database if it doesn't exist."""
    try:
        # Connect to postgres database to create new database
        postgres_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
        engine = create_engine(postgres_uri, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(
                "SELECT 1 FROM pg_database WHERE datname = :dbname"
            ), {"dbname": TARGET_DB}).fetchone()
            
            if not result:
                logger.info(f"Creating database '{TARGET_DB}'...")
                conn.execute(text(f'CREATE DATABASE "{TARGET_DB}"'))
                logger.info(f"✓ Database '{TARGET_DB}' created successfully")
            else:
                logger.info(f"Database '{TARGET_DB}' already exists")
        
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Error creating database: {str(e)}")
        return False


def create_target_schema():
    """Create tables in the target database."""
    try:
        engine = create_engine(TARGET_URI)
        
        logger.info("Creating schema in target database...")
        
        with engine.connect() as conn:
            # Create matches table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id INTEGER PRIMARY KEY,
                    competition VARCHAR(255),
                    season VARCHAR(50),
                    date TIMESTAMP,
                    home_team VARCHAR(255) NOT NULL,
                    away_team VARCHAR(255) NOT NULL,
                    home_score INTEGER,
                    away_score INTEGER,
                    result VARCHAR(50),
                    status VARCHAR(50),
                    data_source VARCHAR(100),
                    venue VARCHAR(255),
                    referee VARCHAR(255),
                    home_team_wins_last_n INTEGER DEFAULT 0,
                    home_team_draws_last_n INTEGER DEFAULT 0,
                    home_team_losses_last_n INTEGER DEFAULT 0,
                    away_team_wins_last_n INTEGER DEFAULT 0,
                    away_team_draws_last_n INTEGER DEFAULT 0,
                    away_team_losses_last_n INTEGER DEFAULT 0,
                    home_team_avg_gd_last_n FLOAT DEFAULT 0,
                    away_team_avg_gd_last_n FLOAT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create odds table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS odds (
                    odds_id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(match_id),
                    bookmaker VARCHAR(255),
                    home_win FLOAT,
                    draw FLOAT,
                    away_win FLOAT,
                    last_updated TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create predictions table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(match_id),
                    model_version VARCHAR(50),
                    winner VARCHAR(50),
                    home_prob FLOAT,
                    draw_prob FLOAT,
                    away_prob FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_odds_match ON odds(match_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id)"))
            
            conn.commit()
        
        logger.info("✓ Schema created successfully")
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Error creating schema: {str(e)}")
        return False


def copy_table_data(table_name, source_engine, target_engine, batch_size=1000):
    """Copy data from source table to target table."""
    try:
        logger.info(f"Copying data from '{table_name}' table...")
        
        # Read data from source
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, source_engine)
        
        if len(df) == 0:
            logger.warning(f"No data found in '{table_name}' table")
            return 0
        
        logger.info(f"Found {len(df)} records in '{table_name}'")
        
        # Write data to target in batches
        total_inserted = 0
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql(
                table_name,
                target_engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            total_inserted += len(batch)
            logger.info(f"  Inserted {total_inserted}/{len(df)} records...")
        
        logger.info(f"✓ Successfully copied {total_inserted} records from '{table_name}'")
        return total_inserted
    
    except SQLAlchemyError as e:
        logger.error(f"Error copying '{table_name}': {str(e)}")
        return 0


def verify_data_integrity(source_engine, target_engine):
    """Verify that data was copied correctly."""
    try:
        logger.info("\nVerifying data integrity...")
        
        tables = ['matches', 'odds', 'predictions']
        all_match = True
        
        for table in tables:
            # Count records in source
            source_count = pd.read_sql(
                f"SELECT COUNT(*) as count FROM {table}",
                source_engine
            ).iloc[0]['count']
            
            # Count records in target
            target_count = pd.read_sql(
                f"SELECT COUNT(*) as count FROM {table}",
                target_engine
            ).iloc[0]['count']
            
            match = "✓" if source_count == target_count else "✗"
            logger.info(f"{match} {table}: Source={source_count}, Target={target_count}")
            
            if source_count != target_count:
                all_match = False
        
        if all_match:
            logger.info("\n✓ All data verified successfully!")
        else:
            logger.warning("\n⚠ Data counts don't match. Please review.")
        
        return all_match
    
    except SQLAlchemyError as e:
        logger.error(f"Error verifying data: {str(e)}")
        return False


def main():
    """Main function to orchestrate the data migration."""
    logger.info("="*80)
    logger.info("FOOTBALL HERITAGE DATABASE MIGRATION")
    logger.info("="*80)
    logger.info(f"Source: {SOURCE_DB}")
    logger.info(f"Target: {TARGET_DB}")
    logger.info("="*80)
    
    # Step 1: Create target database
    logger.info("\nStep 1: Creating target database...")
    if not create_target_database():
        logger.error("Failed to create database. Exiting.")
        sys.exit(1)
    
    # Step 2: Create schema
    logger.info("\nStep 2: Creating schema...")
    if not create_target_schema():
        logger.error("Failed to create schema. Exiting.")
        sys.exit(1)
    
    # Step 3: Copy data
    logger.info("\nStep 3: Copying data...")
    
    try:
        source_engine = create_engine(SOURCE_URI)
        target_engine = create_engine(TARGET_URI)
        
        # Copy tables in order (respecting foreign keys)
        tables = ['matches', 'odds', 'predictions']
        total_records = 0
        
        for table in tables:
            count = copy_table_data(table, source_engine, target_engine)
            total_records += count
        
        logger.info(f"\n✓ Total records copied: {total_records}")
        
        # Step 4: Verify data integrity
        logger.info("\nStep 4: Verifying data integrity...")
        verify_data_integrity(source_engine, target_engine)
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*80)
        
        with target_engine.connect() as conn:
            matches_count = conn.execute(text("SELECT COUNT(*) FROM matches")).fetchone()[0]
            odds_count = conn.execute(text("SELECT COUNT(*) FROM odds")).fetchone()[0]
            predictions_count = conn.execute(text("SELECT COUNT(*) FROM predictions")).fetchone()[0]
            
            logger.info(f"Matches:     {matches_count:,}")
            logger.info(f"Odds:        {odds_count:,}")
            logger.info(f"Predictions: {predictions_count:,}")
        
        logger.info("="*80)
        logger.info("✓ Migration completed successfully!")
        logger.info("="*80)
        
        # Connection string for the new database
        logger.info(f"\nNew database connection string:")
        logger.info(f"postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{TARGET_DB}")
        
    except SQLAlchemyError as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
