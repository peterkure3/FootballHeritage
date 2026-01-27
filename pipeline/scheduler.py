"""
Automated scheduler for football betting pipeline.
Runs daily data fetches and weekly model retraining.

Usage:
    python scheduler.py

This will run continuously and execute tasks on schedule.
"""

import sys
import time
import schedule
import logging
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from etl.fetch_raw_data import main as fetch_data
from etl.ingest_oddsapi_offers import main as ingest_oddsapi_offers
from etl.match_oddsapi_events import main as match_oddsapi_events
from etl.compute_intelligence import main as compute_betting_intelligence
from etl.transform import main as transform_data
from etl.load_to_db import main as load_data
from models.train_model import main as train_model
from models.predict import main as predict_matches

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def daily_fetch_job():
    """Daily job: Fetch data and generate predictions."""
    logger.info("=" * 60)
    logger.info("DAILY FETCH JOB STARTED")
    logger.info("=" * 60)
    
    try:
        # Fetch new data
        logger.info("[1/4] Fetching raw data...")
        fetch_data()

        logger.info("[2/5] Ingesting OddsAPI offers...")
        ingest_oddsapi_offers()

        logger.info("[3/6] Matching OddsAPI events...")
        match_oddsapi_events()

        logger.info("[4/7] Computing betting intelligence...")
        compute_betting_intelligence()
        
        # Transform data
        logger.info("[5/7] Transforming data...")
        transform_data()
        
        # Load to database
        logger.info("[6/7] Loading to database...")
        load_data()
        
        # Generate predictions
        logger.info("[7/7] Generating predictions...")
        predict_matches()
        
        logger.info("✓ Daily fetch completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Daily fetch failed: {str(e)}", exc_info=True)


def weekly_retrain_job():
    """Weekly job: Full pipeline with model retraining."""
    logger.info("=" * 60)
    logger.info("WEEKLY RETRAIN JOB STARTED")
    logger.info("=" * 60)
    
    try:
        # Fetch new data
        logger.info("[1/5] Fetching raw data...")
        fetch_data()

        logger.info("[2/6] Ingesting OddsAPI offers...")
        ingest_oddsapi_offers()

        logger.info("[3/7] Matching OddsAPI events...")
        match_oddsapi_events()

        logger.info("[4/8] Computing betting intelligence...")
        compute_betting_intelligence()
        
        # Transform data
        logger.info("[5/8] Transforming data...")
        transform_data()
        
        # Load to database
        logger.info("[6/8] Loading to database...")
        load_data()
        
        # Train model
        logger.info("[7/8] Training model...")
        train_model()
        
        # Generate predictions
        logger.info("[8/8] Generating predictions...")
        predict_matches()
        
        logger.info("✓ Weekly retrain completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Weekly retrain failed: {str(e)}", exc_info=True)


def main():
    """Main scheduler loop."""
    logger.info("=" * 60)
    logger.info("FOOTBALL BETTING PIPELINE SCHEDULER")
    logger.info("=" * 60)
    logger.info("Schedule:")
    logger.info("  - Daily fetch: Every day at 08:00")
    logger.info("  - Weekly retrain: Every Sunday at 02:00")
    logger.info("=" * 60)
    
    # Schedule daily fetch at 8 AM
    schedule.every().day.at("08:00").do(daily_fetch_job)
    
    # Schedule weekly retrain on Sunday at 2 AM
    schedule.every().sunday.at("02:00").do(weekly_retrain_job)
    
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    
    # Run immediately on startup (optional)
    # daily_fetch_job()
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
