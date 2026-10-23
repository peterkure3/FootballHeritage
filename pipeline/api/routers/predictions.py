"""Prediction history, accuracy, model versions, Elo/backtest endpoints.

NOTE: static /predictions/* routes are registered before /predictions/{match_id};
in the old single-file layout seven of them were shadowed by the dynamic route."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from datetime import datetime, date as Date
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.prediction_dashboard import history, accuracy
from config import LOG_LEVEL, MODEL_VERSION
from etl.utils import setup_logger
from api.db import get_db_connection, heritage_engine

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


# Response models
class PredictionResponse(BaseModel):
    match_id: int
    winner: str
    home_prob: float
    draw_prob: float
    away_prob: float
    model_version: str
    created_at: datetime


class MatchResponse(BaseModel):
    match_id: int
    competition: Optional[str]
    date: Optional[datetime]
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str
    home_win_odds: Optional[float]
    draw_odds: Optional[float]
    away_win_odds: Optional[float]


class HealthResponse(BaseModel):
    status: str
    last_pipeline_run: Optional[str]
    database_connected: bool


# Prediction History & Accuracy Models (defined early for route ordering)
class PredictionResult(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str] = None
    match_date: Optional[datetime] = None
    predicted_winner: str
    home_prob: float
    draw_prob: float
    away_prob: float
    actual_result: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    is_correct: Optional[bool] = None
    confidence: str
    model_version: Optional[str] = None
    prediction_created_at: Optional[datetime] = None


class PredictionHistoryResponse(BaseModel):
    predictions: List[PredictionResult]
    total_count: int
    correct_count: int
    accuracy_pct: Optional[float]
    excluded: dict = {}
    evaluation_basis: str = 'latest_valid_pre_kickoff_per_fixture'
    page: int
    page_size: int


class AccuracyByLeague(BaseModel):
    league: str
    total: int
    correct: int
    accuracy_pct: float


class AccuracyByConfidence(BaseModel):
    confidence: str
    total: int
    correct: int
    accuracy_pct: float


class PredictionAccuracyResponse(BaseModel):
    overall_accuracy: Optional[float]
    total_predictions: int
    correct_predictions: int
    by_league: List[AccuracyByLeague]
    by_confidence: List[AccuracyByConfidence]
    recent_form: List[dict]
    log_loss: Optional[float] = None
    brier_score: Optional[float] = None
    excluded: dict = {}
    evaluation_basis: str = 'latest_valid_pre_kickoff_per_fixture'
    evidence_note: str = ''
    sample_start: Optional[str] = None
    sample_end: Optional[str] = None
    bookmaker_baseline: Optional[dict] = None
    calibration: Optional[dict] = None

@router.get("/predictions/history-data", response_model=PredictionHistoryResponse)
def get_prediction_history(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=5, le=100),
    league: Optional[str] = None,
    result_filter: Optional[str] = Query(None, pattern="^(all|correct|incorrect)$"),
    days: Optional[int] = Query(None, ge=1, le=365),
    start_date: Optional[Date] = None, end_date: Optional[Date] = None,
    model_version: Optional[str] = None,
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="Start date must precede end date")
    try:
        return history(page, page_size, league, result_filter, days, start_date, end_date, model_version)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Prediction history database is unavailable")


@router.post("/predictions/update-results")
def update_prediction_results(days: int = Query(7, ge=1, le=30, description="Days to look back")):
    """
    Trigger an update of match results from external API.
    This fetches final scores for completed matches and updates the database.
    """
    try:
        from etl.update_results import update_all_results, get_pending_results_count
        
        updated = update_all_results(days)
        pending = get_pending_results_count()
        
        return {
            "success": True,
            "updated_count": updated,
            "pending_count": pending,
            "message": f"Updated {updated} matches. {pending} matches still pending results."
        }
    except Exception as e:
        logger.error(f"Failed to update results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/accuracy-data", response_model=PredictionAccuracyResponse)
def get_prediction_accuracy(
    days: Optional[int] = Query(None, ge=1, le=365), league: Optional[str] = None,
    start_date: Optional[Date] = None, end_date: Optional[Date] = None,
    model_version: Optional[str] = None,
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="Start date must precede end date")
    try:
        return accuracy(league, days, start_date, end_date, model_version)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Prediction evaluation database is unavailable")


class ModelVersionInfo(BaseModel):
    version: str
    prediction_count: int
    correct_count: int
    accuracy_pct: Optional[float]
    settled_count: int = 0
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_current: bool = False


class ModelVersionsResponse(BaseModel):
    versions: List[ModelVersionInfo]
    current_version: Optional[str] = None


@router.get("/predictions/versions", response_model=ModelVersionsResponse)
def get_prediction_versions():
    """
    Get all model versions used for predictions with their accuracy stats.
    Useful for tracking model performance over time.
    """
    try:
        db = get_db_connection()
        
        query = text("""
            SELECT 
                p.model_version,
                COUNT(*) AS prediction_count,
                COUNT(*) FILTER (WHERE m.result = p.winner AND m.date < (NOW() AT TIME ZONE 'UTC')
                    AND p.created_at < m.date AND p.id = (
                        SELECT p2.id FROM predictions p2 WHERE p2.match_id=p.match_id
                            AND p2.model_version=p.model_version AND p2.created_at < m.date
                            AND p2.winner IN ('home_win','draw','away_win')
                            AND p2.home_prob BETWEEN 0 AND 1 AND p2.draw_prob BETWEEN 0 AND 1
                            AND p2.away_prob BETWEEN 0 AND 1
                            AND ABS(p2.home_prob+p2.draw_prob+p2.away_prob-1)<0.01
                        ORDER BY p2.created_at DESC, p2.id DESC LIMIT 1)) AS correct_count,
                COUNT(*) FILTER (WHERE m.result IN ('home_win','draw','away_win') AND m.date < (NOW() AT TIME ZONE 'UTC')
                    AND p.created_at < m.date AND p.id = (
                        SELECT p2.id FROM predictions p2 WHERE p2.match_id=p.match_id
                            AND p2.model_version=p.model_version AND p2.created_at < m.date
                            AND p2.winner IN ('home_win','draw','away_win')
                            AND p2.home_prob BETWEEN 0 AND 1 AND p2.draw_prob BETWEEN 0 AND 1
                            AND p2.away_prob BETWEEN 0 AND 1
                            AND ABS(p2.home_prob+p2.draw_prob+p2.away_prob-1)<0.01
                        ORDER BY p2.created_at DESC, p2.id DESC LIMIT 1)) AS settled_count,
                MIN(p.created_at) AS first_used,
                MAX(p.created_at) AS last_used
            FROM predictions p
            LEFT JOIN matches m ON p.match_id = m.match_id
            WHERE p.model_version IS NOT NULL
            GROUP BY p.model_version
            ORDER BY MAX(p.created_at) DESC
        """)
        
        with db.connect() as conn:
            results = conn.execute(query).fetchall()
        
        if not results:
            return ModelVersionsResponse(versions=[], current_version=None)
        
        versions = []
        current_version = None
        
        for row in results:
            version = str(row[0]) if row[0] else "unknown"
            prediction_count = int(row[1]) if row[1] else 0
            correct_count = int(row[2]) if row[2] else 0
            settled_count = int(row[3]) if row[3] else 0
            first_used = row[4]
            last_used = row[5]

            # Accuracy over settled matches only — unsettled predictions are not "wrong yet"
            accuracy_pct = (correct_count / settled_count * 100) if settled_count > 0 else None
            is_current = version == MODEL_VERSION
            
            if is_current:
                current_version = version
            
            versions.append(ModelVersionInfo(
                version=version,
                prediction_count=prediction_count,
                correct_count=correct_count,
                accuracy_pct=round(accuracy_pct, 2) if accuracy_pct is not None else None,
                settled_count=settled_count,
                first_used=first_used,
                last_used=last_used,
                is_current=is_current,
            ))
        
        return ModelVersionsResponse(
            versions=versions,
            current_version=current_version,
        )
    
    except Exception as e:
        logger.error(f"Prediction versions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PREDICTION IMPROVEMENT ENDPOINTS
# ============================================================================

class DataValidationResponse(BaseModel):
    timestamp: str
    overall_passed: bool
    checks: List[Dict]
    recommendations: List[str]


class EloRatingResponse(BaseModel):
    team: str
    elo: float
    form: float
    games_played: int
    recent_form: str


class BacktestResultResponse(BaseModel):
    model_name: str
    total_predictions: int
    brier_score: float
    log_loss: float
    accuracy: float
    by_league: Dict


class MatchPredictionResponse(BaseModel):
    home_team: str
    away_team: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    home_elo: float
    away_elo: float
    confidence: float
    league: Optional[str]
    event_date: Optional[str]


@router.get("/predictions/validate-data")
def validate_prediction_data():
    """
    Run data validation checks before predictions.
    Returns validation status and recommendations.
    """
    from etl.data_validator import DataValidator
    
    try:
        validator = DataValidator(heritage_engine)
        report = validator.validate_all()
        
        return {
            "timestamp": report.timestamp.isoformat(),
            "overall_passed": report.overall_passed,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "message": c.message,
                    "severity": c.severity,
                }
                for c in report.checks
            ],
            "recommendations": report.recommendations,
        }
    except Exception as e:
        logger.error(f"Data validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/elo-ratings", response_model=List[EloRatingResponse])
def get_elo_ratings(
    league: Optional[str] = Query(None, description="Filter by league"),
    limit: int = Query(50, ge=1, le=500),
):
    """
    Get current Elo ratings for all teams.
    """
    from etl.elo_model import EloModel
    
    try:
        model = EloModel(heritage_engine)
        model.load_ratings_from_db()
        
        if not model.ratings:
            model.load_historical_results(league=league)
        
        ratings = model.get_all_ratings()
        return ratings[:limit]
    except Exception as e:
        logger.error(f"Elo ratings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/update-elo")
def update_elo_ratings(
    league: Optional[str] = Query(None, description="Filter by league"),
):
    """
    Recalculate Elo ratings from historical data.
    """
    from etl.elo_model import compute_elo_ratings
    
    try:
        result = compute_elo_ratings(league=league, save=True)
        return {
            "status": "success",
            "teams_rated": result.get("teams_rated", 0),
            "top_10": result.get("top_10", []),
        }
    except Exception as e:
        logger.error(f"Elo update error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/upcoming", response_model=List[MatchPredictionResponse])
def get_upcoming_predictions(
    league: Optional[str] = Query(None, description="Filter by league"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get predictions for upcoming matches using enhanced Elo model.
    """
    from etl.elo_model import predict_upcoming_matches
    
    try:
        predictions = predict_upcoming_matches(league=league)
        return predictions[:limit]
    except Exception as e:
        logger.error(f"Predictions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/backtest")
def get_backtest_results(
    days_back: int = Query(90, ge=7, le=365),
    league: Optional[str] = Query(None, description="Filter by league"),
):
    """
    Run backtesting on the Elo model and return accuracy metrics.
    """
    from etl.backtesting import run_backtest
    
    try:
        result = run_backtest(model="elo", days_back=days_back, league=league, save=False)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/value-bets")
def get_enhanced_value_bets(
    min_ev_pct: float = Query(0.02, ge=0, le=1.0, description="Minimum EV percentage"),
    min_confidence: float = Query(0.5, ge=0, le=1.0, description="Minimum confidence"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get value bets using improved true probability calculation.
    Uses ensemble of sharp book devigging, consensus odds, and Elo model.
    """
    from etl.true_probability import TrueProbabilityCalculator
    
    try:
        calculator = TrueProbabilityCalculator(heritage_engine)
        value_bets = calculator.find_value_bets(
            min_ev_pct=min_ev_pct,
            min_confidence=min_confidence,
            limit=limit,
        )
        
        return {
            "count": len(value_bets),
            "bets": value_bets,
        }
    except Exception as e:
        logger.error(f"Value bets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/run-pipeline")
def run_enhanced_pipeline():
    """
    Run the full enhanced intelligence pipeline.
    Includes data validation, Elo updates, and improved EV calculation.
    """
    from etl.compute_intelligence_v2 import run_full_pipeline
    
    try:
        results = run_full_pipeline(stake=100.0)
        return {
            "status": "success",
            "results": results,
        }
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/{match_id}", response_model=PredictionResponse)
def get_prediction(match_id: int):
    """
    Get prediction for a specific match.
    
    Args:
        match_id: Match ID
    
    Returns:
        Prediction with probabilities
    """
    try:
        engine = get_db_connection()
        
        query = text("""
            SELECT 
                match_id,
                model_version,
                winner,
                home_prob,
                draw_prob,
                away_prob,
                created_at
            FROM predictions
            WHERE match_id = :match_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"match_id": match_id}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction found for match {match_id}"
            )
        
        return PredictionResponse(
            match_id=result[0],
            model_version=result[1],
            winner=result[2],
            home_prob=result[3],
            draw_prob=result[4],
            away_prob=result[5],
            created_at=result[6],
        )
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


