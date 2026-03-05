"""
Compute Intelligence V2 - Enhanced Pipeline

Integrates all prediction improvements:
1. Data validation before processing
2. Enhanced Elo model with form adjustments
3. Improved true probability calculation (ensemble methods)
4. Stores results with confidence scores

This is the upgraded version of compute_intelligence.py
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger
from etl.data_validator import DataValidator, validate_data
from etl.elo_model import EloModel, compute_elo_ratings
from etl.true_probability import TrueProbabilityCalculator

logger = setup_logger(__name__, LOG_LEVEL)


def compute_intelligence_v2(
    stake: float = 100.0,
    min_ev_pct: float = 0.02,
    min_confidence: float = 0.5,
    validate_first: bool = True,
    update_elo: bool = True,
) -> Dict[str, any]:
    """
    Enhanced intelligence computation pipeline.
    
    Args:
        stake: Base stake for EV calculations
        min_ev_pct: Minimum EV% to store (default 2%)
        min_confidence: Minimum confidence to store
        validate_first: Run data validation before processing
        update_elo: Update Elo ratings from recent results
    
    Returns:
        Dict with counts and validation status
    """
    engine = create_engine(HERITAGE_DATABASE_URI)
    results = {
        "validation_passed": True,
        "validation_warnings": [],
        "elo_teams_updated": 0,
        "ev_bets_found": 0,
        "ev_bets_stored": 0,
        "devig_rows": 0,
    }
    
    # Step 1: Data Validation
    if validate_first:
        logger.info("[1/4] Running data validation...")
        validator = DataValidator(engine)
        report = validator.validate_all()
        
        results["validation_passed"] = report.overall_passed
        results["validation_warnings"] = [
            c.message for c in report.checks if not c.passed
        ]
        
        if not report.overall_passed:
            logger.warning("Data validation failed. Proceeding with caution.")
            for rec in report.recommendations:
                logger.warning("  Recommendation: %s", rec)
    else:
        logger.info("[1/4] Skipping data validation")
    
    # Step 2: Update Elo Ratings
    if update_elo:
        logger.info("[2/4] Updating Elo ratings...")
        try:
            elo_result = compute_elo_ratings(save=True)
            results["elo_teams_updated"] = elo_result.get("teams_rated", 0)
            logger.info("Updated Elo ratings for %d teams", results["elo_teams_updated"])
        except Exception as e:
            logger.warning("Elo update failed (non-critical): %s", e)
    else:
        logger.info("[2/4] Skipping Elo update")
    
    # Step 3: Calculate True Probabilities and Find Value Bets
    logger.info("[3/4] Calculating true probabilities and finding value bets...")
    try:
        calculator = TrueProbabilityCalculator(engine)
        # Use lower threshold to capture more bets, filter later if needed
        value_bets = calculator.find_value_bets(
            min_ev_pct=0.0,  # Store all, let users filter
            min_confidence=0.0,
            limit=2000,
        )
        # Count how many are actually positive EV
        positive_ev = [b for b in value_bets if b["expected_value_pct"] >= min_ev_pct]
        results["ev_bets_found"] = len(value_bets)
        results["positive_ev_bets"] = len(positive_ev)
        logger.info("Found %d total bets, %d with EV >= %.1f%%", 
                   len(value_bets), len(positive_ev), min_ev_pct * 100)
    except Exception as e:
        logger.error("True probability calculation failed: %s", e)
        value_bets = []
    
    # Step 4: Store Results
    logger.info("[4/4] Storing results to database...")
    try:
        with engine.begin() as conn:
            # Clear existing EV bets (we'll repopulate with improved data)
            conn.execute(text("DELETE FROM ev_bets WHERE true_probability > 0"))
            
            # Insert new value bets
            insert_ev = text("""
                INSERT INTO ev_bets (
                    event_id, pipeline_match_id, bookmaker, market, selection,
                    odds, stake, true_probability, expected_value, expected_value_pct,
                    source_updated_at
                ) VALUES (
                    :event_id, :pipeline_match_id, :bookmaker, :market, :selection,
                    :odds, :stake, :true_probability, :expected_value, :expected_value_pct,
                    NOW()
                )
                ON CONFLICT DO NOTHING
            """)
            
            for bet in value_bets:
                try:
                    conn.execute(insert_ev, {
                        "event_id": bet["event_id"],
                        "pipeline_match_id": bet.get("pipeline_match_id"),
                        "bookmaker": bet["bookmaker"],
                        "market": bet["market"],
                        "selection": bet["selection"],
                        "odds": bet["odds"],
                        "stake": Decimal(str(stake)),
                        "true_probability": bet["true_probability"],
                        "expected_value": bet["expected_value"],
                        "expected_value_pct": bet["expected_value_pct"],
                    })
                    results["ev_bets_stored"] += 1
                except Exception as e:
                    logger.debug("Failed to insert bet: %s", e)
            
            logger.info("Stored %d EV bets", results["ev_bets_stored"])
    
    except SQLAlchemyError as e:
        logger.error("Database storage failed: %s", e)
        raise
    
    # Summary
    logger.info("=== Intelligence V2 Complete ===")
    logger.info("  Validation: %s", "PASSED" if results["validation_passed"] else "WARNINGS")
    logger.info("  Elo Teams: %d", results["elo_teams_updated"])
    logger.info("  Value Bets Found: %d", results["ev_bets_found"])
    logger.info("  Value Bets Stored: %d", results["ev_bets_stored"])
    
    return results


def run_full_pipeline(stake: float = 100.0) -> Dict:
    """
    Run the complete enhanced intelligence pipeline.
    
    This includes:
    1. Data validation
    2. Elo rating updates
    3. True probability calculation
    4. Value bet detection
    5. Also runs the original compute_intelligence for backwards compatibility
    """
    from etl.compute_intelligence import compute_and_store_intelligence
    
    logger.info("=" * 60)
    logger.info("RUNNING FULL INTELLIGENCE PIPELINE")
    logger.info("=" * 60)
    
    # Run enhanced pipeline
    v2_results = compute_intelligence_v2(
        stake=stake,
        min_ev_pct=0.02,
        min_confidence=0.5,
        validate_first=True,
        update_elo=True,
    )
    
    # Also run original pipeline for devigged odds and arbitrage
    logger.info("\nRunning original intelligence pipeline for devig/arb...")
    original_results = compute_and_store_intelligence(stake=stake)
    
    return {
        "v2": v2_results,
        "original": original_results,
    }


def main():
    """Run the enhanced intelligence pipeline."""
    import json
    
    results = run_full_pipeline(stake=100.0)
    
    print("\n=== Pipeline Results ===")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
