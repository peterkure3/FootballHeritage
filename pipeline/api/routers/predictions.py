"""Prediction history, accuracy, model versions, Elo/backtest endpoints.

NOTE: static /predictions/* routes are registered before /predictions/{match_id};
in the old single-file layout seven of them were shadowed by the dynamic route."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import LOG_LEVEL
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


class PredictionHistoryResponse(BaseModel):
    predictions: List[PredictionResult]
    total_count: int
    correct_count: int
    accuracy_pct: float
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
    overall_accuracy: float
    total_predictions: int
    correct_predictions: int
    by_league: List[AccuracyByLeague]
    by_confidence: List[AccuracyByConfidence]
    recent_form: List[dict]  # Last 10 predictions

@router.get("/predictions/history-data", response_model=PredictionHistoryResponse)
def get_prediction_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=5, le=100, description="Items per page"),
    league: Optional[str] = Query(None, description="Filter by league"),
    result_filter: Optional[str] = Query(None, description="all, correct, incorrect"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter by last N days"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get paginated prediction history with actual outcomes.
    Shows which predictions were correct/incorrect.
    Supports custom date range via start_date and end_date parameters.
    """
    try:
        db = get_db_connection()
        
        # Build filters
        filters = ["m.result IS NOT NULL"]  # Only finished matches
        params = {}
        
        # Custom date range takes precedence over days
        if start_date and end_date:
            filters.append("m.date >= :start_date AND m.date <= :end_date")
            params["start_date"] = start_date
            params["end_date"] = end_date
        elif start_date:
            filters.append("m.date >= :start_date")
            params["start_date"] = start_date
        elif end_date:
            filters.append("m.date <= :end_date")
            params["end_date"] = end_date
        elif days:
            filters.append(f"(m.date IS NULL OR m.date >= NOW() - INTERVAL '{days} days')")
        
        if league:
            filters.append("m.competition ILIKE :league")
            params["league"] = f"%{league}%"
        
        filter_clause = " AND ".join(filters)
        
        # Get total count first
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE {filter_clause}
        """)
        
        with db.connect() as conn:
            total_count = conn.execute(count_query, params).scalar() or 0
        
        # Get paginated results
        offset = (page - 1) * page_size
        
        query = text(f"""
            SELECT 
                m.match_id, m.home_team, m.away_team, m.competition, m.date,
                m.result, m.home_score, m.away_score,
                p.winner AS predicted_winner, p.home_prob, p.draw_prob, p.away_prob,
                p.model_version,
                CASE WHEN m.result = p.winner THEN true ELSE false END AS is_correct
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE {filter_clause}
            ORDER BY m.date DESC NULLS LAST, m.match_id DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params["limit"] = page_size
        params["offset"] = offset
        
        with db.connect() as conn:
            results = conn.execute(query, params).fetchall()
        
        predictions = []
        correct_count = 0
        
        for row in results:
            try:
                # Safely convert probabilities
                home_prob = float(row[9]) if row[9] is not None else 0.33
                draw_prob = float(row[10]) if row[10] is not None else 0.33
                away_prob = float(row[11]) if row[11] is not None else 0.33
                
                # Determine confidence based on max probability
                max_prob = max(home_prob, draw_prob, away_prob)
                if max_prob >= 0.6:
                    confidence = "High"
                elif max_prob >= 0.45:
                    confidence = "Medium"
                else:
                    confidence = "Low"
                
                is_correct = bool(row[13]) if row[13] is not None else False
                if is_correct:
                    correct_count += 1
                
                # Apply result filter
                if result_filter == "correct" and not is_correct:
                    continue
                elif result_filter == "incorrect" and is_correct:
                    continue
                
                predictions.append(PredictionResult(
                    match_id=int(row[0]),
                    home_team=str(row[1]) if row[1] else "Unknown",
                    away_team=str(row[2]) if row[2] else "Unknown",
                    competition=str(row[3]) if row[3] else None,
                    match_date=row[4],
                    actual_result=str(row[5]) if row[5] else None,
                    home_score=int(row[6]) if row[6] is not None else None,
                    away_score=int(row[7]) if row[7] is not None else None,
                    predicted_winner=str(row[8]) if row[8] else "unknown",
                    home_prob=round(home_prob, 4),
                    draw_prob=round(draw_prob, 4),
                    away_prob=round(away_prob, 4),
                    model_version=str(row[12]) if row[12] else None,
                    is_correct=is_correct,
                    confidence=confidence,
                ))
            except Exception as row_error:
                logger.warning(f"Skipping row due to error: {row_error}")
        
        accuracy_pct = (correct_count / len(results) * 100) if results else 0
        
        return PredictionHistoryResponse(
            predictions=predictions,
            total_count=total_count,
            correct_count=correct_count,
            accuracy_pct=round(accuracy_pct, 2),
            page=page,
            page_size=page_size,
        )
    
    except Exception as e:
        logger.error(f"Prediction history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
):
    """
    Get overall prediction accuracy metrics.
    Breaks down accuracy by league and confidence level.
    """
    try:
        db = get_db_connection()
        
        # Overall accuracy
        overall_query = text("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN m.result = p.winner THEN 1 ELSE 0 END) AS correct
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE m.result IS NOT NULL
              AND (m.date IS NULL OR m.date >= NOW() - INTERVAL '%s days')
        """ % days)
        
        with db.connect() as conn:
            overall = conn.execute(overall_query).fetchone()
        
        total = int(overall[0]) if overall and overall[0] else 0
        correct = int(overall[1]) if overall and overall[1] else 0
        overall_accuracy = (correct / total * 100) if total > 0 else 0
        
        # Accuracy by league
        league_query = text("""
            SELECT 
                m.competition,
                COUNT(*) AS total,
                SUM(CASE WHEN m.result = p.winner THEN 1 ELSE 0 END) AS correct
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE m.result IS NOT NULL
              AND (m.date IS NULL OR m.date >= NOW() - INTERVAL '%s days')
              AND m.competition IS NOT NULL
            GROUP BY m.competition
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """ % days)
        
        with db.connect() as conn:
            league_results = conn.execute(league_query).fetchall()
        
        by_league = []
        for row in league_results:
            league_total = int(row[1]) if row[1] else 0
            league_correct = int(row[2]) if row[2] else 0
            by_league.append(AccuracyByLeague(
                league=str(row[0]) if row[0] else "Unknown",
                total=league_total,
                correct=league_correct,
                accuracy_pct=round((league_correct / league_total * 100) if league_total > 0 else 0, 2),
            ))
        
        # Accuracy by confidence tier
        confidence_query = text("""
            SELECT 
                CASE 
                    WHEN GREATEST(p.home_prob, p.draw_prob, p.away_prob) >= 0.6 THEN 'High'
                    WHEN GREATEST(p.home_prob, p.draw_prob, p.away_prob) >= 0.45 THEN 'Medium'
                    ELSE 'Low'
                END AS confidence,
                COUNT(*) AS total,
                SUM(CASE WHEN m.result = p.winner THEN 1 ELSE 0 END) AS correct
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE m.result IS NOT NULL
              AND (m.date IS NULL OR m.date >= NOW() - INTERVAL '%s days')
            GROUP BY confidence
            ORDER BY confidence
        """ % days)
        
        with db.connect() as conn:
            confidence_results = conn.execute(confidence_query).fetchall()
        
        by_confidence = []
        for row in confidence_results:
            conf_total = int(row[1]) if row[1] else 0
            conf_correct = int(row[2]) if row[2] else 0
            by_confidence.append(AccuracyByConfidence(
                confidence=str(row[0]) if row[0] else "Unknown",
                total=conf_total,
                correct=conf_correct,
                accuracy_pct=round((conf_correct / conf_total * 100) if conf_total > 0 else 0, 2),
            ))
        
        # Recent form (last 10 predictions)
        recent_query = text("""
            SELECT 
                m.match_id, m.home_team, m.away_team, m.date,
                p.winner AS predicted, m.result AS actual,
                CASE WHEN m.result = p.winner THEN true ELSE false END AS correct
            FROM matches m
            JOIN predictions p ON m.match_id = p.match_id
            WHERE m.result IS NOT NULL
            ORDER BY m.date DESC
            LIMIT 10
        """)
        
        with db.connect() as conn:
            recent_results = conn.execute(recent_query).fetchall()
        
        recent_form = []
        for row in recent_results:
            recent_form.append({
                "match_id": row[0],
                "teams": f"{row[1]} vs {row[2]}",
                "date": row[3].isoformat() if row[3] else None,
                "predicted": row[4],
                "actual": row[5],
                "correct": row[6],
            })
        
        return PredictionAccuracyResponse(
            overall_accuracy=round(overall_accuracy, 2),
            total_predictions=total,
            correct_predictions=correct,
            by_league=by_league,
            by_confidence=by_confidence,
            recent_form=recent_form,
        )
    
    except Exception as e:
        logger.error(f"Prediction accuracy error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class ModelVersionInfo(BaseModel):
    version: str
    prediction_count: int
    correct_count: int
    accuracy_pct: float
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
                SUM(CASE WHEN m.result = p.winner THEN 1 ELSE 0 END) AS correct_count,
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
        
        for i, row in enumerate(results):
            version = str(row[0]) if row[0] else "unknown"
            prediction_count = int(row[1]) if row[1] else 0
            correct_count = int(row[2]) if row[2] else 0
            first_used = row[3]
            last_used = row[4]
            
            accuracy_pct = (correct_count / prediction_count * 100) if prediction_count > 0 else 0
            is_current = (i == 0)  # Most recent version is current
            
            if is_current:
                current_version = version
            
            versions.append(ModelVersionInfo(
                version=version,
                prediction_count=prediction_count,
                correct_count=correct_count,
                accuracy_pct=round(accuracy_pct, 2),
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


