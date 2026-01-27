"""
Convenience script to run the entire pipeline manually.
Executes: fetch → transform → load → train → predict
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from etl.utils import setup_logger
from config import LOG_LEVEL

logger = setup_logger(__name__, LOG_LEVEL)


def clean_processed_data():
    """Clean processed data before loading to database."""
    import pandas as pd
    from config import PROCESSED_DATA_DIR
    
    logger.info("Cleaning processed data...")
    
    # Find latest matches file
    matches_files = sorted(PROCESSED_DATA_DIR.glob("matches_*.parquet"))
    if not matches_files:
        logger.warning("No processed matches files found")
        return
    
    matches_file = matches_files[-1]
    logger.info(f"Cleaning {matches_file.name}")
    
    # Load and clean
    df = pd.read_parquet(matches_file)
    initial_count = len(df)
    
    # Remove rows with missing critical data
    df = df.dropna(subset=['match_id', 'home_team', 'away_team', 'home_score', 'away_score'])
    
    # Ensure match_id is integer
    df['match_id'] = df['match_id'].astype(int)
    
    # Save cleaned data
    df.to_parquet(matches_file, index=False)
    
    removed = initial_count - len(df)
    if removed > 0:
        logger.info(f"Removed {removed} rows with missing data")
    logger.info(f"Cleaned data: {len(df)} matches ready for database")


def run_full_pipeline():
    """Execute the complete pipeline."""
    logger.info("=" * 60)
    logger.info("Starting full pipeline execution")
    logger.info("=" * 60)
    
    steps = [
        ("Fetch raw data", "etl.fetch_raw_data", "main"),
        ("Ingest OddsAPI offers", "etl.ingest_oddsapi_offers", "main"),
        ("Match OddsAPI events", "etl.match_oddsapi_events", "main"),
        ("Compute betting intelligence", "etl.compute_intelligence", "main"),
        ("Transform data", "etl.transform", "main"),
        ("Clean processed data", None, clean_processed_data),  # Custom cleaning step
        ("Load to database", "etl.load_to_db", "main"),
        ("Train model", "models.train_model", "main"),
        ("Generate predictions", "models.predict", "main"),
    ]
    
    for step_name, module_name, func in steps:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Step: {step_name}")
        logger.info(f"{'=' * 60}")
        
        try:
            if module_name:
                # Import and call module function
                module = __import__(module_name, fromlist=[func])
                func_to_call = getattr(module, func)
                func_to_call()
            else:
                # Call function directly
                func()
            
            logger.info(f"✓ {step_name} completed successfully")
        except Exception as e:
            logger.error(f"✗ {step_name} failed: {str(e)}", exc_info=True)
            logger.error("Pipeline execution stopped due to error")
            sys.exit(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline execution completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_full_pipeline()
