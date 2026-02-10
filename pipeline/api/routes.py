"""
API routes for football betting predictions.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from config import DATABASE_URI, LOG_LEVEL
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


engine = create_engine(DATABASE_URI)

heritage_engine = create_engine(HERITAGE_DATABASE_URI)


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


class WhatIfPredictionResponse(BaseModel):
    home_team: str
    away_team: str
    winner: str
    home_prob: float
    draw_prob: float
    away_prob: float
    model_version: str
    confidence: str
    recommendation: str


class DevigRequest(BaseModel):
    pipeline_match_id: Optional[str] = None
    event_id: Optional[str] = None
    bookmaker: str
    market: str = "h2h"
    outcome_a: str
    outcome_b: str
    odds_a: float
    odds_b: float
    source_updated_at: Optional[datetime] = None


class DevigResponse(BaseModel):
    fair_prob_a: float
    fair_prob_b: float
    vig: float


class EvRequest(BaseModel):
    pipeline_match_id: Optional[str] = None
    event_id: Optional[str] = None
    bookmaker: Optional[str] = None
    market: str
    selection: str
    odds: float
    stake: float
    true_probability: float
    source_updated_at: Optional[datetime] = None


class EvResponse(BaseModel):
    expected_value: float
    expected_value_pct: float


class EvBatchRequest(BaseModel):
    bets: List[EvRequest]


class ArbitrageOffer(BaseModel):
    bookmaker: str
    selection: str
    decimal_odds: float


class ArbitrageScanRequest(BaseModel):
    pipeline_match_id: Optional[str] = None
    event_id: Optional[str] = None
    market: str = "h2h"
    selection_a: str
    selection_b: str
    total_stake: float
    offers: List[ArbitrageOffer]
    source_updated_at: Optional[datetime] = None


class ArbitrageResponse(BaseModel):
    book_a: str
    book_b: str
    odds_a: float
    odds_b: float
    arb_percentage: float
    stake_a: float
    stake_b: float


class ValueBetResponse(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str]
    match_date: Optional[datetime]
    selection: str
    model_prob: float
    implied_prob: float
    edge: float
    edge_pct: float
    decimal_odds: float
    kelly_stake_pct: float
    recommended_stake: float
    expected_value: float
    confidence: str
    model_version: str


def implied_probability_from_decimal(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1")
    return 1.0 / decimal_odds


def devig_two_way(decimal_odds_a: float, decimal_odds_b: float) -> Dict[str, float]:
    p1 = implied_probability_from_decimal(decimal_odds_a)
    p2 = implied_probability_from_decimal(decimal_odds_b)
    p_total = p1 + p2
    if p_total <= 0:
        raise ValueError("invalid implied probabilities")
    fair_p1 = p1 / p_total
    fair_p2 = p2 / p_total
    vig = p_total - 1.0
    return {"fair_prob_a": fair_p1, "fair_prob_b": fair_p2, "vig": vig}


def win_profit_from_decimal(decimal_odds: float, stake: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1")
    if stake <= 0:
        raise ValueError("stake must be > 0")
    return stake * (decimal_odds - 1.0)


def expected_value(true_probability: float, decimal_odds: float, stake: float) -> Dict[str, float]:
    if true_probability < 0 or true_probability > 1:
        raise ValueError("true_probability must be in [0, 1]")
    win_profit = win_profit_from_decimal(decimal_odds, stake)
    ev = (true_probability * win_profit) - ((1.0 - true_probability) * stake)
    ev_pct = ev / stake
    return {"expected_value": ev, "expected_value_pct": ev_pct}


def arbitrage_two_way(decimal_odds_a: float, decimal_odds_b: float, total_stake: float) -> Optional[Dict[str, float]]:
    if decimal_odds_a <= 1.0 or decimal_odds_b <= 1.0:
        raise ValueError("decimal odds must be > 1")
    if total_stake <= 0:
        raise ValueError("total_stake must be > 0")
    inv_a = 1.0 / decimal_odds_a
    inv_b = 1.0 / decimal_odds_b
    inv_sum = inv_a + inv_b
    if inv_sum >= 1.0:
        return None
    edge = 1.0 - inv_sum
    stake_a = total_stake * (inv_a / inv_sum)
    stake_b = total_stake * (inv_b / inv_sum)
    return {"arb_percentage": edge, "stake_a": stake_a, "stake_b": stake_b}


def get_db_connection():
    """Get database connection."""
    return engine


def get_heritage_db_connection():
    return heritage_engine


@router.post("/intelligence/devig", response_model=DevigResponse)
async def devig_endpoint(payload: DevigRequest):
    try:
        computed = devig_two_way(payload.odds_a, payload.odds_b)

        insert_query = text("""
            INSERT INTO devigged_odds (
                event_id,
                pipeline_match_id,
                bookmaker,
                market,
                outcome_a,
                outcome_b,
                odds_a,
                odds_b,
                fair_prob_a,
                fair_prob_b,
                vig,
                source_updated_at
            ) VALUES (
                :event_id,
                :pipeline_match_id,
                :bookmaker,
                :market,
                :outcome_a,
                :outcome_b,
                :odds_a,
                :odds_b,
                :fair_prob_a,
                :fair_prob_b,
                :vig,
                :source_updated_at
            )
            ON CONFLICT DO NOTHING
        """)

        params = {
            "event_id": payload.event_id,
            "pipeline_match_id": payload.pipeline_match_id,
            "bookmaker": payload.bookmaker,
            "market": payload.market,
            "outcome_a": payload.outcome_a,
            "outcome_b": payload.outcome_b,
            "odds_a": payload.odds_a,
            "odds_b": payload.odds_b,
            "fair_prob_a": computed["fair_prob_a"],
            "fair_prob_b": computed["fair_prob_b"],
            "vig": computed["vig"],
            "source_updated_at": payload.source_updated_at,
        }

        heritage = get_heritage_db_connection()
        with heritage.begin() as conn:
            conn.execute(insert_query, params)

        return DevigResponse(
            fair_prob_a=computed["fair_prob_a"],
            fair_prob_b=computed["fair_prob_b"],
            vig=computed["vig"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error (devig): {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/intelligence/ev", response_model=EvResponse)
async def ev_endpoint(payload: EvRequest):
    try:
        computed = expected_value(payload.true_probability, payload.odds, payload.stake)

        insert_query = text("""
            INSERT INTO ev_bets (
                event_id,
                pipeline_match_id,
                bookmaker,
                market,
                selection,
                odds,
                stake,
                true_probability,
                expected_value,
                expected_value_pct,
                source_updated_at
            ) VALUES (
                :event_id,
                :pipeline_match_id,
                :bookmaker,
                :market,
                :selection,
                :odds,
                :stake,
                :true_probability,
                :expected_value,
                :expected_value_pct,
                :source_updated_at
            )
            ON CONFLICT DO NOTHING
        """)

        params = {
            "event_id": payload.event_id,
            "pipeline_match_id": payload.pipeline_match_id,
            "bookmaker": payload.bookmaker,
            "market": payload.market,
            "selection": payload.selection,
            "odds": payload.odds,
            "stake": payload.stake,
            "true_probability": payload.true_probability,
            "expected_value": computed["expected_value"],
            "expected_value_pct": computed["expected_value_pct"],
            "source_updated_at": payload.source_updated_at,
        }

        heritage = get_heritage_db_connection()
        with heritage.begin() as conn:
            conn.execute(insert_query, params)

        return EvResponse(
            expected_value=computed["expected_value"],
            expected_value_pct=computed["expected_value_pct"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error (ev): {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/intelligence/ev/batch", response_model=List[EvResponse])
async def ev_batch_endpoint(payload: EvBatchRequest):
    results: List[EvResponse] = []
    try:
        heritage = get_heritage_db_connection()

        insert_query = text("""
            INSERT INTO ev_bets (
                event_id,
                pipeline_match_id,
                bookmaker,
                market,
                selection,
                odds,
                stake,
                true_probability,
                expected_value,
                expected_value_pct,
                source_updated_at
            ) VALUES (
                :event_id,
                :pipeline_match_id,
                :bookmaker,
                :market,
                :selection,
                :odds,
                :stake,
                :true_probability,
                :expected_value,
                :expected_value_pct,
                :source_updated_at
            )
            ON CONFLICT DO NOTHING
        """)

        with heritage.begin() as conn:
            for bet in payload.bets:
                computed = expected_value(bet.true_probability, bet.odds, bet.stake)
                conn.execute(
                    insert_query,
                    {
                        "event_id": bet.event_id,
                        "pipeline_match_id": bet.pipeline_match_id,
                        "bookmaker": bet.bookmaker,
                        "market": bet.market,
                        "selection": bet.selection,
                        "odds": bet.odds,
                        "stake": bet.stake,
                        "true_probability": bet.true_probability,
                        "expected_value": computed["expected_value"],
                        "expected_value_pct": computed["expected_value_pct"],
                        "source_updated_at": bet.source_updated_at,
                    },
                )
                results.append(
                    EvResponse(
                        expected_value=computed["expected_value"],
                        expected_value_pct=computed["expected_value_pct"],
                    )
                )

        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error (ev batch): {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/intelligence/arbitrage/scan", response_model=List[ArbitrageResponse])
async def arbitrage_scan(payload: ArbitrageScanRequest):
    try:
        offers_a = [o for o in payload.offers if o.selection == payload.selection_a]
        offers_b = [o for o in payload.offers if o.selection == payload.selection_b]

        if not offers_a or not offers_b:
            return []

        heritage = get_heritage_db_connection()
        insert_query = text("""
            INSERT INTO arbitrage (
                event_id,
                pipeline_match_id,
                market,
                selection_a,
                selection_b,
                book_a,
                book_b,
                odds_a,
                odds_b,
                arb_percentage,
                total_stake,
                stake_a,
                stake_b,
                source_updated_at
            ) VALUES (
                :event_id,
                :pipeline_match_id,
                :market,
                :selection_a,
                :selection_b,
                :book_a,
                :book_b,
                :odds_a,
                :odds_b,
                :arb_percentage,
                :total_stake,
                :stake_a,
                :stake_b,
                :source_updated_at
            )
            ON CONFLICT DO NOTHING
        """)

        results: List[ArbitrageResponse] = []
        with heritage.begin() as conn:
            for oa in offers_a:
                for ob in offers_b:
                    if oa.bookmaker == ob.bookmaker:
                        continue
                    computed = arbitrage_two_way(oa.decimal_odds, ob.decimal_odds, payload.total_stake)
                    if not computed:
                        continue
                    conn.execute(
                        insert_query,
                        {
                            "event_id": payload.event_id,
                            "pipeline_match_id": payload.pipeline_match_id,
                            "market": payload.market,
                            "selection_a": payload.selection_a,
                            "selection_b": payload.selection_b,
                            "book_a": oa.bookmaker,
                            "book_b": ob.bookmaker,
                            "odds_a": oa.decimal_odds,
                            "odds_b": ob.decimal_odds,
                            "arb_percentage": computed["arb_percentage"],
                            "total_stake": payload.total_stake,
                            "stake_a": computed["stake_a"],
                            "stake_b": computed["stake_b"],
                            "source_updated_at": payload.source_updated_at,
                        },
                    )
                    results.append(
                        ArbitrageResponse(
                            book_a=oa.bookmaker,
                            book_b=ob.bookmaker,
                            odds_a=oa.decimal_odds,
                            odds_b=ob.decimal_odds,
                            arb_percentage=computed["arb_percentage"],
                            stake_a=computed["stake_a"],
                            stake_b=computed["stake_b"],
                        )
                    )

        results.sort(key=lambda r: r.arb_percentage, reverse=True)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error (arbitrage): {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/best-value-bets", response_model=List[ValueBetResponse])
async def get_best_value_bets(
    min_edge: float = Query(0.05, description="Minimum edge percentage (0.05 = 5%)"),
    bankroll: float = Query(1000.0, description="Your total bankroll for Kelly sizing"),
    kelly_fraction: float = Query(0.25, description="Fraction of Kelly to use (0.25 = quarter Kelly)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum bets to return"),
    upcoming_only: bool = Query(True, description="Only show upcoming matches"),
):
    """
    Get best value bets by combining ML predictions with current odds.
    
    This endpoint:
    1. Fetches all matches with predictions and odds
    2. Calculates edge (model probability - implied probability)
    3. Computes Kelly criterion stake sizing
    4. Returns bets sorted by expected value
    
    Args:
        min_edge: Minimum edge to include (default 5%)
        bankroll: Your bankroll for stake calculation
        kelly_fraction: Fraction of Kelly to use (0.25 = conservative)
        limit: Max number of bets to return
        upcoming_only: Only include future matches
    
    Returns:
        List of value bets sorted by edge
    """
    try:
        db = get_db_connection()
        
        # Get matches with predictions and odds - only future matches
        date_filter = " AND m.date >= NOW()" if upcoming_only else ""
        status_filter = " AND (m.status IS NULL OR m.status NOT IN ('FINISHED', 'CANCELLED', 'POSTPONED'))" if upcoming_only else ""
        
        query = text(f"""
            SELECT 
                m.match_id,
                m.home_team,
                m.away_team,
                m.competition,
                m.date,
                m.status,
                p.home_prob,
                p.draw_prob,
                p.away_prob,
                p.model_version,
                p.winner,
                COALESCE(AVG(o.home_win), 2.5) as home_odds,
                COALESCE(AVG(o.draw), 3.2) as draw_odds,
                COALESCE(AVG(o.away_win), 2.8) as away_odds
            FROM matches m
            INNER JOIN predictions p ON m.match_id = p.match_id
            LEFT JOIN odds o ON m.match_id = o.match_id
            WHERE m.home_team IS NOT NULL
                AND m.away_team IS NOT NULL
                AND p.home_prob IS NOT NULL
                {date_filter}
                {status_filter}
            GROUP BY m.match_id, m.home_team, m.away_team, m.competition, m.date, m.status,
                     p.home_prob, p.draw_prob, p.away_prob, p.model_version, p.winner
            ORDER BY m.date ASC NULLS LAST
        """)
        
        with db.connect() as conn:
            results = conn.execute(query).fetchall()
        
        value_bets = []
        
        for row in results:
            match_id = row[0]
            home_team = row[1]
            away_team = row[2]
            competition = row[3]
            match_date = row[4]
            status = row[5]
            home_prob = float(row[6])
            draw_prob = float(row[7])
            away_prob = float(row[8])
            model_version = row[9]
            winner = row[10]
            home_odds = float(row[11])
            draw_odds = float(row[12])
            away_odds = float(row[13])
            
            # Calculate implied probabilities (with vig)
            home_implied = 1 / home_odds if home_odds > 1 else 0.4
            draw_implied = 1 / draw_odds if draw_odds > 1 else 0.25
            away_implied = 1 / away_odds if away_odds > 1 else 0.35
            
            # Check each outcome for value
            outcomes = [
                ("Home Win", home_team, home_prob, home_implied, home_odds),
                ("Draw", "Draw", draw_prob, draw_implied, draw_odds),
                ("Away Win", away_team, away_prob, away_implied, away_odds),
            ]
            
            for outcome_name, selection, model_prob, implied_prob, decimal_odds in outcomes:
                edge = model_prob - implied_prob
                
                if edge >= min_edge and decimal_odds > 1.0:
                    # Kelly criterion: f* = (bp - q) / b
                    # where b = decimal_odds - 1, p = model_prob, q = 1 - p
                    b = decimal_odds - 1
                    kelly_full = (b * model_prob - (1 - model_prob)) / b if b > 0 else 0
                    kelly_stake_pct = max(0, kelly_full * kelly_fraction)
                    recommended_stake = round(bankroll * kelly_stake_pct, 2)
                    
                    # Expected value
                    win_profit = recommended_stake * (decimal_odds - 1)
                    ev = (model_prob * win_profit) - ((1 - model_prob) * recommended_stake)
                    
                    # Confidence level
                    if edge > 0.15:
                        confidence = "High"
                    elif edge > 0.08:
                        confidence = "Medium"
                    else:
                        confidence = "Low"
                    
                    value_bets.append(ValueBetResponse(
                        match_id=match_id,
                        home_team=home_team,
                        away_team=away_team,
                        competition=competition,
                        match_date=match_date,
                        selection=f"{selection} ({outcome_name})",
                        model_prob=round(model_prob, 4),
                        implied_prob=round(implied_prob, 4),
                        edge=round(edge, 4),
                        edge_pct=round(edge * 100, 2),
                        decimal_odds=round(decimal_odds, 3),
                        kelly_stake_pct=round(kelly_stake_pct * 100, 2),
                        recommended_stake=recommended_stake,
                        expected_value=round(ev, 2),
                        confidence=confidence,
                        model_version=model_version,
                    ))
        
        # Sort by edge descending
        value_bets.sort(key=lambda x: x.edge, reverse=True)
        
        return value_bets[:limit]
    
    except SQLAlchemyError as e:
        logger.error(f"Database error (best-value-bets): {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error generating value bets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PREDICTION HISTORY & ACCURACY ROUTES
# IMPORTANT: These specific routes MUST be defined BEFORE /predictions/{match_id}
# to avoid FastAPI matching "history-data" as a match_id parameter
# ============================================================================

@router.get("/predictions/history-data", response_model=PredictionHistoryResponse)
async def get_prediction_history(
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
async def update_prediction_results(days: int = Query(7, ge=1, le=30, description="Days to look back")):
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
async def get_prediction_accuracy(
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
async def get_prediction_versions():
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


@router.get("/predictions/{match_id}", response_model=PredictionResponse)
async def get_prediction(match_id: int):
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


@router.get("/matches", response_model=List[MatchResponse])
async def get_matches(
    competition: Optional[str] = Query(None, description="Filter by competition name"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get matches with odds.
    
    Args:
        competition: Optional competition filter
        date: Optional date filter (YYYY-MM-DD)
        limit: Maximum number of results
    
    Returns:
        List of matches with odds
    """
    try:
        engine = get_db_connection()
        
        # Build query
        query_str = """
            SELECT 
                m.match_id,
                m.competition,
                m.date,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.status,
                AVG(o.home_win) as home_win_odds,
                AVG(o.draw) as draw_odds,
                AVG(o.away_win) as away_win_odds
            FROM matches m
            LEFT JOIN odds o ON m.match_id = o.match_id
            WHERE 1=1
        """
        
        params = {}
        
        if competition:
            query_str += " AND m.competition ILIKE :competition"
            params["competition"] = f"%{competition}%"
        
        if date:
            query_str += " AND DATE(m.date) = :date"
            params["date"] = date
        
        query_str += """
            GROUP BY m.match_id, m.competition, m.date, m.home_team, 
                     m.away_team, m.home_score, m.away_score, m.status
            ORDER BY m.date DESC NULLS LAST, m.match_id DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        with engine.connect() as conn:
            results = conn.execute(text(query_str), params).fetchall()
        
        matches = []
        for row in results:
            matches.append(MatchResponse(
                match_id=row[0],
                competition=row[1],
                date=row[2],
                home_team=row[3],
                away_team=row[4],
                home_score=row[5],
                away_score=row[6],
                status=row[7],
                home_win_odds=row[8],
                draw_odds=row[9],
                away_win_odds=row[10],
            ))
        
        return matches
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API and pipeline health.
    
    Returns:
        Health status
    """
    database_connected = False
    last_pipeline_run = None
    
    try:
        engine = get_db_connection()
        
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            database_connected = True
            
            # Get last prediction timestamp
            result = conn.execute(
                text("SELECT MAX(created_at) FROM predictions")
            ).fetchone()
            
            if result and result[0]:
                last_pipeline_run = result[0].isoformat()
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
    
    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        last_pipeline_run=last_pipeline_run,
        database_connected=database_connected,
    )


@router.get("/predict-matchup", response_model=WhatIfPredictionResponse)
async def predict_matchup(
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name")
):
    """
    Predict outcome for any two teams (What-If scenario).
    
    Uses enhanced v2 model with:
    - ELO ratings
    - Head-to-head history
    - Weighted form
    - Venue-specific stats
    - Odds-derived features
    - Probability calibration
    - Ensemble model (stacking)
    
    Args:
        home_team: Name of the home team
        away_team: Name of the away team
    
    Returns:
        Prediction with probabilities and recommendation
    
    Example:
        /api/v1/predict-matchup?home_team=Arsenal&away_team=Chelsea
    """
    try:
        import joblib
        import pandas as pd
        import numpy as np
        from pathlib import Path
        
        model_dir = Path(__file__).parent.parent / "models" / "model_store"
        
        # Try v2 model first, fallback to v1
        model_version = "2.0.0"
        model_path = model_dir / f"model_v{model_version}.pkl"
        if not model_path.exists():
            model_version = "1.0.0"
            model_path = model_dir / f"model_v{model_version}.pkl"
        
        features_path = model_dir / f"features_v{model_version}.pkl"
        label_encoder_path = model_dir / f"label_encoder_v{model_version}.pkl"
        
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Model not trained yet. Please run: python -m models.train_model_v2"
            )
        
        model = joblib.load(model_path)
        feature_names = joblib.load(features_path)
        label_encoder = joblib.load(label_encoder_path)
        
        engine = get_db_connection()
        
        # Enhanced team stats with more metrics
        def get_team_stats(team_name, window=10):
            query = text("""
                WITH recent_matches AS (
                    SELECT 
                        home_team, away_team, result, home_score, away_score, date,
                        CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as team_side
                    FROM matches
                    WHERE (home_team ILIKE :team OR away_team ILIKE :team)
                        AND result IS NOT NULL
                        AND home_score IS NOT NULL
                    ORDER BY date DESC
                    LIMIT :window
                )
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN (team_side='home' AND result='home_win') OR (team_side='away' AND result='away_win') THEN 1 END) as wins,
                    COUNT(CASE WHEN result = 'draw' THEN 1 END) as draws,
                    COUNT(CASE WHEN (team_side='home' AND result='away_win') OR (team_side='away' AND result='home_win') THEN 1 END) as losses,
                    AVG(CASE WHEN team_side='home' THEN home_score - away_score ELSE away_score - home_score END) as avg_gd,
                    AVG(CASE WHEN team_side='home' THEN home_score ELSE away_score END) as avg_goals_for,
                    AVG(CASE WHEN team_side='home' THEN away_score ELSE home_score END) as avg_goals_against
                FROM recent_matches
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
            
            if result and result[0] > 0:
                total = result[0]
                return {
                    'wins': result[1] or 0,
                    'draws': result[2] or 0,
                    'losses': result[3] or 0,
                    'avg_gd': float(result[4] or 0.0),
                    'avg_goals_for': float(result[5] or 1.5),
                    'avg_goals_against': float(result[6] or 1.5),
                    'win_rate': (result[1] or 0) / total,
                    'form_points': ((result[1] or 0) * 3 + (result[2] or 0)) / (total * 3),
                }
            return {'wins': 0, 'draws': 0, 'losses': 0, 'avg_gd': 0.0, 
                    'avg_goals_for': 1.5, 'avg_goals_against': 1.5, 'win_rate': 0.33, 'form_points': 0.33}
        
        # Get venue-specific stats
        def get_venue_stats(team_name, is_home, window=20):
            if is_home:
                query = text("""
                    WITH recent AS (
                        SELECT result, home_score FROM matches 
                        WHERE home_team ILIKE :team AND result IS NOT NULL
                        ORDER BY date DESC LIMIT :window
                    )
                    SELECT COUNT(*) as matches,
                           COUNT(CASE WHEN result = 'home_win' THEN 1 END) as wins,
                           AVG(home_score) as avg_goals
                    FROM recent
                """)
            else:
                query = text("""
                    WITH recent AS (
                        SELECT result, away_score FROM matches 
                        WHERE away_team ILIKE :team AND result IS NOT NULL
                        ORDER BY date DESC LIMIT :window
                    )
                    SELECT COUNT(*) as matches,
                           COUNT(CASE WHEN result = 'away_win' THEN 1 END) as wins,
                           AVG(away_score) as avg_goals
                    FROM recent
                """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
            
            if result and result[0] > 0:
                return {'win_rate': (result[1] or 0) / result[0], 'avg_goals': float(result[2] or 1.5)}
            return {'win_rate': 0.5 if is_home else 0.33, 'avg_goals': 1.5}
        
        # Get head-to-head stats
        def get_h2h_stats(home, away, window=10):
            query = text("""
                SELECT home_team, away_team, result, home_score, away_score
                FROM matches
                WHERE ((home_team ILIKE :home AND away_team ILIKE :away) OR
                       (home_team ILIKE :away AND away_team ILIKE :home))
                    AND result IS NOT NULL
                ORDER BY date DESC LIMIT :window
            """)
            
            with engine.connect() as conn:
                results = conn.execute(query, {"home": f"%{home}%", "away": f"%{away}%", "window": window}).fetchall()
            
            if not results:
                return {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'home_goals_avg': 1.5, 'away_goals_avg': 1.5}
            
            home_wins, draws, away_wins = 0, 0, 0
            home_goals, away_goals = [], []
            
            for row in results:
                match_home, match_away, result, h_score, a_score = row
                if home.lower() in match_home.lower():
                    home_goals.append(h_score or 0)
                    away_goals.append(a_score or 0)
                    if result == "home_win": home_wins += 1
                    elif result == "draw": draws += 1
                    else: away_wins += 1
                else:
                    home_goals.append(a_score or 0)
                    away_goals.append(h_score or 0)
                    if result == "away_win": home_wins += 1
                    elif result == "draw": draws += 1
                    else: away_wins += 1
            
            return {
                'home_wins': home_wins, 'draws': draws, 'away_wins': away_wins,
                'home_goals_avg': np.mean(home_goals) if home_goals else 1.5,
                'away_goals_avg': np.mean(away_goals) if away_goals else 1.5,
            }
        
        # Calculate ELO ratings
        def get_elo_ratings():
            query = text("""
                SELECT home_team, away_team, result FROM matches
                WHERE result IS NOT NULL ORDER BY date ASC
            """)
            
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            elo = {}
            K, HOME_ADV, INIT = 32, 100, 1500
            
            for _, row in df.iterrows():
                h, a, r = row["home_team"], row["away_team"], row["result"]
                h_elo = elo.get(h, INIT)
                a_elo = elo.get(a, INIT)
                h_exp = 1 / (1 + 10 ** ((a_elo - h_elo - HOME_ADV) / 400))
                h_act = 1.0 if r == "home_win" else (0.5 if r == "draw" else 0.0)
                elo[h] = h_elo + K * (h_act - h_exp)
                elo[a] = a_elo + K * ((1 - h_act) - (1 - h_exp))
            
            return elo
        
        # Gather all stats
        home_stats = get_team_stats(home_team)
        away_stats = get_team_stats(away_team)
        home_venue = get_venue_stats(home_team, is_home=True)
        away_venue = get_venue_stats(away_team, is_home=False)
        h2h = get_h2h_stats(home_team, away_team)
        elo_ratings = get_elo_ratings()
        
        home_elo = elo_ratings.get(home_team, 1500)
        away_elo = elo_ratings.get(away_team, 1500)
        elo_diff = home_elo - away_elo + 100
        home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - 100) / 400))
        
        # Get odds (try to find specific or use averages)
        odds_query = text("""
            SELECT AVG(home_win), AVG(draw), AVG(away_win) FROM odds WHERE home_win IS NOT NULL
        """)
        with engine.connect() as conn:
            odds_result = conn.execute(odds_query).fetchone()
        
        home_odds = float(odds_result[0]) if odds_result and odds_result[0] else 2.5
        draw_odds = float(odds_result[1]) if odds_result and odds_result[1] else 3.2
        away_odds = float(odds_result[2]) if odds_result and odds_result[2] else 2.8
        
        # Calculate odds-derived features
        implied_home = 1 / home_odds
        implied_draw = 1 / draw_odds
        implied_away = 1 / away_odds
        overround = implied_home + implied_draw + implied_away
        fair_home = implied_home / overround
        fair_draw = implied_draw / overround
        fair_away = implied_away / overround
        
        # Build comprehensive feature vector
        features = {
            # Odds-derived (strongest signals)
            'fair_home_prob': fair_home,
            'fair_draw_prob': fair_draw,
            'fair_away_prob': fair_away,
            'odds_ratio': home_odds / away_odds if away_odds > 0 else 1.0,
            'odds_spread': home_odds - away_odds,
            'log_home_odds': np.log(max(home_odds, 1.01)),
            'log_away_odds': np.log(max(away_odds, 1.01)),
            'log_draw_odds': np.log(max(draw_odds, 1.01)),
            'home_is_favorite': 1 if home_odds < away_odds else 0,
            'favorite_odds': min(home_odds, away_odds),
            'underdog_odds': max(home_odds, away_odds),
            # ELO
            'home_elo': home_elo,
            'away_elo': away_elo,
            'elo_diff': elo_diff,
            'home_expected': home_expected,
            # H2H
            'h2h_home_wins': h2h['home_wins'],
            'h2h_draws': h2h['draws'],
            'h2h_away_wins': h2h['away_wins'],
            'h2h_home_goals_avg': h2h['home_goals_avg'],
            'h2h_away_goals_avg': h2h['away_goals_avg'],
            # Weighted form
            'home_weighted_form': home_stats['form_points'] * 3,
            'away_weighted_form': away_stats['form_points'] * 3,
            'home_weighted_goals_for': home_stats['avg_goals_for'],
            'home_weighted_goals_against': home_stats['avg_goals_against'],
            'away_weighted_goals_for': away_stats['avg_goals_for'],
            'away_weighted_goals_against': away_stats['avg_goals_against'],
            # Venue
            'home_team_home_win_rate': home_venue['win_rate'],
            'home_team_home_goals_avg': home_venue['avg_goals'],
            'away_team_away_win_rate': away_venue['win_rate'],
            'away_team_away_goals_avg': away_venue['avg_goals'],
            # Original form
            'home_team_wins_last_n': home_stats['wins'],
            'home_team_draws_last_n': home_stats['draws'],
            'home_team_losses_last_n': home_stats['losses'],
            'away_team_wins_last_n': away_stats['wins'],
            'away_team_draws_last_n': away_stats['draws'],
            'away_team_losses_last_n': away_stats['losses'],
            'home_team_avg_gd_last_n': home_stats['avg_gd'],
            'away_team_avg_gd_last_n': away_stats['avg_gd'],
            'home_win': home_odds,
            'draw': draw_odds,
            'away_win': away_odds,
        }
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([{k: features.get(k, 0) for k in feature_names}])
        X = X.fillna(0)
        
        # Make prediction
        probabilities = model.predict_proba(X)[0]
        predicted_class = model.predict(X)[0]
        winner = label_encoder.inverse_transform([predicted_class])[0]
        
        prob_dict = dict(zip(label_encoder.classes_, probabilities))
        home_prob = prob_dict.get('home_win', 0.0)
        draw_prob = prob_dict.get('draw', 0.0)
        away_prob = prob_dict.get('away_win', 0.0)
        
        # Confidence based on probability spread
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 0.55:
            confidence = "High"
        elif max_prob > 0.42:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Generate detailed recommendation
        if winner == 'home_win':
            recommendation = f"{home_team} is favored to win at home ({home_prob*100:.1f}%)"
        elif winner == 'away_win':
            recommendation = f"{away_team} is favored to win away ({away_prob*100:.1f}%)"
        else:
            recommendation = f"Match likely to end in a draw ({draw_prob*100:.1f}%)"
        
        # Add ELO context
        if abs(home_elo - away_elo) > 100:
            stronger = home_team if home_elo > away_elo else away_team
            recommendation += f". {stronger} has a significant ELO advantage."
        
        # Add form context
        if home_stats['wins'] >= 4:
            recommendation += f" {home_team} is in excellent form ({home_stats['wins']} wins in last 10)."
        elif home_stats['losses'] >= 4:
            recommendation += f" {home_team} is struggling ({home_stats['losses']} losses in last 10)."
        
        if away_stats['wins'] >= 4:
            recommendation += f" {away_team} is in great form ({away_stats['wins']} wins in last 10)."
        elif away_stats['losses'] >= 4:
            recommendation += f" {away_team} has been losing ({away_stats['losses']} losses in last 10)."
        
        # Add H2H context
        if h2h['home_wins'] + h2h['draws'] + h2h['away_wins'] >= 3:
            if h2h['home_wins'] > h2h['away_wins']:
                recommendation += f" H2H favors {home_team} ({h2h['home_wins']}-{h2h['draws']}-{h2h['away_wins']})."
            elif h2h['away_wins'] > h2h['home_wins']:
                recommendation += f" H2H favors {away_team} ({h2h['away_wins']}-{h2h['draws']}-{h2h['home_wins']})."
        
        return WhatIfPredictionResponse(
            home_team=home_team,
            away_team=away_team,
            winner=winner,
            home_prob=float(home_prob),
            draw_prob=float(draw_prob),
            away_prob=float(away_prob),
            model_version=model_version,
            confidence=confidence,
            recommendation=recommendation
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model files not found. Please train the model first."
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ============================================================================
# SMART ASSISTANT - Intent-based routing without LLM
# ============================================================================

class AssistantRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class BetCard(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str] = None
    match_date: Optional[datetime] = None
    selection: str
    model_prob: float
    implied_prob: float
    edge_pct: float
    decimal_odds: float
    recommended_stake: float
    expected_value: float
    confidence: str


class PredictionCard(BaseModel):
    home_team: str
    away_team: str
    home_prob: float
    draw_prob: float
    away_prob: float
    winner: str
    confidence: str
    recommendation: str


class MatchCard(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str] = None
    match_date: Optional[datetime] = None
    status: Optional[str] = None


class AssistantResponse(BaseModel):
    intent: str
    message: str
    data: Optional[Dict[str, Any]] = None
    bets: Optional[List[BetCard]] = None
    predictions: Optional[List[PredictionCard]] = None
    matches: Optional[List[MatchCard]] = None
    suggestions: List[str] = []


# Intent patterns for smart routing
INTENT_PATTERNS = {
    "best_bets": [
        r"best\s*(value)?\s*bets?",
        r"top\s*picks?",
        r"what\s*(should|to)\s*bet",
        r"recommend(ations?)?",
        r"smart\s*picks?",
        r"good\s*bets?",
        r"where\s*(should|to)\s*bet",
        r"make\s*money",
        r"profitable",
        r"value\s*bets?",
        r"ev\s*bets?",
        r"\+ev",
    ],
    "predict_match": [
        r"predict\s+(.+?)\s*(?:vs?|versus|against)\s*(.+)",
        r"who\s*(?:will|would|gonna)?\s*win\s+(.+?)\s*(?:vs?|versus|against|or)\s*(.+)",
        r"(.+?)\s*(?:vs?|versus)\s*(.+?)\s*(?:prediction|odds|analysis)",
        r"analyze\s+(.+?)\s*(?:vs?|versus|against)\s*(.+)",
        r"(.+?)\s*(?:vs?|versus|against)\s*(.+)",
    ],
    "upcoming_matches": [
        r"(?:today'?s?|tonight'?s?|upcoming|next)\s*(?:games?|matches?|fixtures?)",
        r"what\s*(?:matches|games)\s*(?:are)?\s*(?:on|playing)?\s*(?:today|tonight|this\s*week)?",
        r"(?:show|list|get)\s*(?:me\s*)?(?:the\s*)?(?:games?|matches?|fixtures?)",
        r"matches\s*(?:on\s*)?today",
        r"today'?s?\s*(?:games?|matches?)",
        r"schedule",
        r"fixtures?",
    ],
    "team_analysis": [
        r"(?:how\s*is|analyze|analysis|stats?|statistics?|form)\s*(?:for\s*)?(.+)",
        r"(.+?)\s*(?:form|stats?|statistics?|performance|analysis)",
        r"tell\s*me\s*about\s*(.+)",
    ],
    "help": [
        r"help",
        r"what\s*can\s*you\s*do",
        r"commands?",
        r"how\s*(?:do|does)\s*(?:this|it)\s*work",
    ],
    "greeting": [
        r"^(?:hi|hello|hey|yo|sup|greetings?)(?:\s|$|!|\?)",
        r"^(?:good\s*)?(?:morning|afternoon|evening)",
    ],
}

# Team name aliases for better matching
TEAM_ALIASES = {
    "arsenal": ["arsenal", "gunners", "ars"],
    "chelsea": ["chelsea", "blues", "che"],
    "liverpool": ["liverpool", "reds", "lfc", "liv"],
    "man city": ["manchester city", "man city", "city", "mci", "mcfc"],
    "man united": ["manchester united", "man united", "man utd", "united", "manu", "mufc"],
    "tottenham": ["tottenham", "spurs", "tot", "thfc"],
    "barcelona": ["barcelona", "barca", "fcb"],
    "real madrid": ["real madrid", "real", "madrid", "rma"],
    "bayern": ["bayern munich", "bayern", "fcb munich"],
    "psg": ["paris saint-germain", "psg", "paris"],
    "juventus": ["juventus", "juve"],
    "inter": ["inter milan", "inter", "internazionale"],
    "milan": ["ac milan", "milan"],
    "dortmund": ["borussia dortmund", "dortmund", "bvb"],
    "newcastle": ["newcastle", "newcastle united", "magpies", "nufc"],
    "aston villa": ["aston villa", "villa", "avfc"],
    "west ham": ["west ham", "hammers", "whu"],
    "everton": ["everton", "toffees", "efc"],
    "wolves": ["wolverhampton", "wolves", "wwfc"],
    "brighton": ["brighton", "seagulls", "bha"],
    "crystal palace": ["crystal palace", "palace", "cpfc"],
    "brentford": ["brentford", "bees"],
    "fulham": ["fulham", "cottagers"],
    "bournemouth": ["bournemouth", "cherries", "afcb"],
    "nottingham forest": ["nottingham forest", "forest", "nffc"],
    "leeds": ["leeds", "leeds united", "lufc"],
}


def normalize_team_name(query: str) -> Optional[str]:
    """Try to match a team name from user input."""
    query_lower = query.lower().strip()
    for canonical, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            if alias in query_lower:
                return canonical
    return query_lower


def detect_intent(query: str) -> tuple[str, dict]:
    """Detect user intent from query using pattern matching."""
    query_lower = query.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return intent, {"groups": match.groups() if match.groups() else []}
    
    return "unknown", {}


@router.post("/smart-assistant", response_model=AssistantResponse)
async def smart_assistant(request: AssistantRequest):
    """
    Smart betting assistant with intent-based routing.
    No LLM required - uses pattern matching to understand queries
    and calls appropriate internal APIs.
    """
    query = request.query.strip()
    intent, context = detect_intent(query)
    
    try:
        if intent == "greeting":
            return AssistantResponse(
                intent=intent,
                message="👋 Hey! I'm your AI betting assistant. I can help you find value bets, predict matches, and analyze teams. What would you like to know?",
                suggestions=[
                    "Show me the best value bets",
                    "Predict Arsenal vs Liverpool",
                    "What matches are on today?",
                    "Analyze Manchester City's form",
                ]
            )
        
        elif intent == "help":
            return AssistantResponse(
                intent=intent,
                message="""🤖 **Here's what I can do:**

**Find Value Bets** - I'll show you bets where our ML model finds positive edge
• "Show me the best bets"
• "What are today's value picks?"

**Predict Matches** - Get AI predictions for any matchup
• "Predict Arsenal vs Chelsea"
• "Who will win Liverpool vs Man City?"

**View Upcoming Matches** - See what's coming up
• "What matches are on today?"
• "Show me this week's fixtures"

**Analyze Teams** - Get team stats and form
• "How is Arsenal doing?"
• "Analyze Liverpool's form"

Just ask naturally and I'll help! 🎯""",
                suggestions=[
                    "Best value bets",
                    "Predict Arsenal vs Liverpool",
                    "Today's matches",
                ]
            )
        
        elif intent == "best_bets":
            return await _handle_best_bets()
        
        elif intent == "predict_match":
            return await _handle_predict_match(query, context)
        
        elif intent == "upcoming_matches":
            return await _handle_upcoming_matches()
        
        elif intent == "team_analysis":
            return await _handle_team_analysis(query, context)
        
        else:
            # Unknown intent - try to be helpful
            return AssistantResponse(
                intent="unknown",
                message=f"🤔 I'm not sure what you're asking about. Here are some things I can help with:",
                suggestions=[
                    "Show me the best value bets",
                    "Predict Arsenal vs Liverpool",
                    "What matches are on today?",
                    "How is Manchester City doing?",
                ]
            )
    
    except Exception as e:
        logger.error(f"Smart assistant error: {str(e)}")
        return AssistantResponse(
            intent="error",
            message=f"Sorry, I encountered an error: {str(e)}. Please try again.",
            suggestions=["Show me the best bets", "What matches are on today?"]
        )


async def _handle_best_bets() -> AssistantResponse:
    """Handle best bets intent."""
    db = get_db_connection()
    
    date_filter = " AND m.date >= NOW()"
    status_filter = " AND (m.status IS NULL OR m.status NOT IN ('FINISHED', 'CANCELLED', 'POSTPONED'))"
    
    query = text(f"""
        SELECT 
            m.match_id, m.home_team, m.away_team, m.competition, m.date, m.status,
            p.home_prob, p.draw_prob, p.away_prob, p.model_version,
            COALESCE(AVG(o.home_win), 2.5) as home_odds,
            COALESCE(AVG(o.draw), 3.2) as draw_odds,
            COALESCE(AVG(o.away_win), 2.8) as away_odds
        FROM matches m
        INNER JOIN predictions p ON m.match_id = p.match_id
        LEFT JOIN odds o ON m.match_id = o.match_id
        WHERE m.home_team IS NOT NULL AND m.away_team IS NOT NULL AND p.home_prob IS NOT NULL
            {date_filter} {status_filter}
        GROUP BY m.match_id, m.home_team, m.away_team, m.competition, m.date, m.status,
                 p.home_prob, p.draw_prob, p.away_prob, p.model_version
        ORDER BY m.date ASC NULLS LAST
        LIMIT 50
    """)
    
    with db.connect() as conn:
        results = conn.execute(query).fetchall()
    
    bets = []
    min_edge = 0.05
    bankroll = 1000
    kelly_fraction = 0.25
    
    for row in results:
        home_prob, draw_prob, away_prob = float(row[6]), float(row[7]), float(row[8])
        home_odds, draw_odds, away_odds = float(row[10]), float(row[11]), float(row[12])
        
        home_implied = 1 / home_odds if home_odds > 1 else 0.4
        draw_implied = 1 / draw_odds if draw_odds > 1 else 0.25
        away_implied = 1 / away_odds if away_odds > 1 else 0.35
        
        outcomes = [
            ("Home Win", row[1], home_prob, home_implied, home_odds),
            ("Draw", "Draw", draw_prob, draw_implied, draw_odds),
            ("Away Win", row[2], away_prob, away_implied, away_odds),
        ]
        
        for outcome_name, selection, model_prob, implied_prob, decimal_odds in outcomes:
            edge = model_prob - implied_prob
            if edge >= min_edge and decimal_odds > 1.0:
                b = decimal_odds - 1
                kelly_full = (b * model_prob - (1 - model_prob)) / b if b > 0 else 0
                kelly_stake_pct = max(0, kelly_full * kelly_fraction)
                recommended_stake = round(bankroll * kelly_stake_pct, 2)
                win_profit = recommended_stake * (decimal_odds - 1)
                ev = (model_prob * win_profit) - ((1 - model_prob) * recommended_stake)
                
                confidence = "High" if edge > 0.15 else "Medium" if edge > 0.08 else "Low"
                
                bets.append(BetCard(
                    match_id=row[0],
                    home_team=row[1],
                    away_team=row[2],
                    competition=row[3],
                    match_date=row[4],
                    selection=f"{selection} ({outcome_name})",
                    model_prob=round(model_prob, 4),
                    implied_prob=round(implied_prob, 4),
                    edge_pct=round(edge * 100, 2),
                    decimal_odds=round(decimal_odds, 3),
                    recommended_stake=recommended_stake,
                    expected_value=round(ev, 2),
                    confidence=confidence,
                ))
    
    bets.sort(key=lambda x: x.edge_pct, reverse=True)
    top_bets = bets[:10]
    
    if not top_bets:
        return AssistantResponse(
            intent="best_bets",
            message="📊 No value bets found right now with 5%+ edge. Try checking back later when more matches are available.",
            bets=[],
            suggestions=["What matches are on today?", "Predict Arsenal vs Liverpool"]
        )
    
    total_ev = sum(b.expected_value for b in top_bets)
    avg_edge = sum(b.edge_pct for b in top_bets) / len(top_bets)
    
    message = f"""🎯 **Found {len(top_bets)} Value Bets!**

Our ML model identified these bets with positive edge:
• **Average Edge:** +{avg_edge:.1f}%
• **Total Expected Value:** ${total_ev:.2f}

⚠️ Remember: These are model predictions, not guarantees. Bet responsibly!"""
    
    return AssistantResponse(
        intent="best_bets",
        message=message,
        bets=top_bets,
        suggestions=["Show me more details", "Predict a specific match", "How does the model work?"]
    )


async def _handle_predict_match(query: str, context: dict) -> AssistantResponse:
    """Handle match prediction intent."""
    groups = context.get("groups", [])
    
    # Try to extract team names from the query
    home_team = None
    away_team = None
    
    if groups and len(groups) >= 2:
        home_team = groups[0].strip() if groups[0] else None
        away_team = groups[1].strip() if groups[1] else None
    
    if not home_team or not away_team:
        # Try to find team names in query
        query_lower = query.lower()
        found_teams = []
        for canonical, aliases in TEAM_ALIASES.items():
            for alias in aliases:
                if alias in query_lower and canonical not in found_teams:
                    found_teams.append(canonical)
                    break
        
        if len(found_teams) >= 2:
            home_team, away_team = found_teams[0], found_teams[1]
        elif len(found_teams) == 1:
            return AssistantResponse(
                intent="predict_match",
                message=f"I found {found_teams[0].title()}, but I need two teams to make a prediction. Who are they playing against?",
                suggestions=[
                    f"Predict {found_teams[0].title()} vs Arsenal",
                    f"Predict {found_teams[0].title()} vs Liverpool",
                    f"Predict {found_teams[0].title()} vs Chelsea",
                ]
            )
        else:
            return AssistantResponse(
                intent="predict_match",
                message="I couldn't identify the teams. Please specify both teams, like 'Predict Arsenal vs Liverpool'.",
                suggestions=[
                    "Predict Arsenal vs Liverpool",
                    "Predict Barcelona vs Real Madrid",
                    "Predict Man City vs Chelsea",
                ]
            )
    
    # Get prediction from database or model
    db = get_db_connection()
    
    # Search for matching teams in database
    search_query = text("""
        SELECT m.match_id, m.home_team, m.away_team, m.competition, m.date,
               p.home_prob, p.draw_prob, p.away_prob, p.winner
        FROM matches m
        LEFT JOIN predictions p ON m.match_id = p.match_id
        WHERE (LOWER(m.home_team) LIKE :home OR LOWER(m.away_team) LIKE :home)
          AND (LOWER(m.home_team) LIKE :away OR LOWER(m.away_team) LIKE :away)
          AND m.date >= NOW()
        ORDER BY m.date ASC
        LIMIT 1
    """)
    
    with db.connect() as conn:
        result = conn.execute(search_query, {
            "home": f"%{home_team}%",
            "away": f"%{away_team}%"
        }).fetchone()
    
    if result and result[5]:  # Has prediction
        home_prob, draw_prob, away_prob = float(result[5]), float(result[6]), float(result[7])
        winner = result[8]
        actual_home = result[1]
        actual_away = result[2]
        
        confidence = "High" if max(home_prob, draw_prob, away_prob) > 0.6 else "Medium" if max(home_prob, draw_prob, away_prob) > 0.45 else "Low"
        
        if winner == "home_win":
            prediction_text = f"**{actual_home}** to win"
        elif winner == "away_win":
            prediction_text = f"**{actual_away}** to win"
        else:
            prediction_text = "**Draw**"
        
        message = f"""⚽ **{actual_home} vs {actual_away}**
📅 {result[4].strftime('%b %d, %Y %H:%M') if result[4] else 'TBD'}
🏆 {result[3] or 'Football'}

**Prediction:** {prediction_text}

**Probabilities:**
• {actual_home}: **{home_prob*100:.1f}%**
• Draw: **{draw_prob*100:.1f}%**
• {actual_away}: **{away_prob*100:.1f}%**

**Confidence:** {confidence}"""
        
        return AssistantResponse(
            intent="predict_match",
            message=message,
            predictions=[PredictionCard(
                home_team=actual_home,
                away_team=actual_away,
                home_prob=home_prob,
                draw_prob=draw_prob,
                away_prob=away_prob,
                winner=winner,
                confidence=confidence,
                recommendation=f"Model predicts {prediction_text}"
            )],
            suggestions=[
                f"Is there value betting on {actual_home}?",
                "Show me the best bets",
                "What other matches are on?"
            ]
        )
    
    # No match found - provide general response
    return AssistantResponse(
        intent="predict_match",
        message=f"I couldn't find an upcoming match between {home_team.title()} and {away_team.title()} in our database. Try checking the upcoming matches or use the What-If predictor on the Predictions page.",
        suggestions=[
            "What matches are on today?",
            "Show me the best bets",
        ]
    )


async def _handle_upcoming_matches() -> AssistantResponse:
    """Handle upcoming matches intent."""
    db = get_db_connection()
    
    query = text("""
        SELECT match_id, home_team, away_team, competition, date, status
        FROM matches
        WHERE date >= NOW() 
          AND (status IS NULL OR status NOT IN ('FINISHED', 'CANCELLED'))
        ORDER BY date ASC
        LIMIT 15
    """)
    
    with db.connect() as conn:
        results = conn.execute(query).fetchall()
    
    if not results:
        return AssistantResponse(
            intent="upcoming_matches",
            message="📅 No upcoming matches found in the database. Try refreshing the data or check back later.",
            matches=[],
            suggestions=["Show me the best bets", "How does the model work?"]
        )
    
    matches = [
        MatchCard(
            match_id=row[0],
            home_team=row[1],
            away_team=row[2],
            competition=row[3],
            match_date=row[4],
            status=row[5]
        )
        for row in results
    ]
    
    # Group by date
    today = datetime.now().date()
    today_matches = [m for m in matches if m.match_date and m.match_date.date() == today]
    tomorrow_matches = [m for m in matches if m.match_date and m.match_date.date() == today + timedelta(days=1)]
    later_matches = [m for m in matches if m not in today_matches and m not in tomorrow_matches]
    
    message_parts = ["📅 **Upcoming Matches**\n"]
    
    if today_matches:
        message_parts.append(f"**Today ({len(today_matches)} matches):**")
        for m in today_matches[:5]:
            time_str = m.match_date.strftime('%H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({time_str})")
    
    if tomorrow_matches:
        message_parts.append(f"\n**Tomorrow ({len(tomorrow_matches)} matches):**")
        for m in tomorrow_matches[:5]:
            time_str = m.match_date.strftime('%H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({time_str})")
    
    if later_matches and not today_matches and not tomorrow_matches:
        message_parts.append(f"**Coming Up ({len(later_matches)} matches):**")
        for m in later_matches[:5]:
            date_str = m.match_date.strftime('%b %d %H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({date_str})")
    
    message = "\n".join(message_parts)
    
    # Create suggestions based on matches
    suggestions = ["Show me the best value bets"]
    if matches:
        suggestions.append(f"Predict {matches[0].home_team} vs {matches[0].away_team}")
    
    return AssistantResponse(
        intent="upcoming_matches",
        message=message,
        matches=matches,
        suggestions=suggestions
    )


async def _handle_team_analysis(query: str, context: dict) -> AssistantResponse:
    """Handle team analysis intent."""
    groups = context.get("groups", [])
    
    team_name = None
    if groups and groups[0]:
        team_name = groups[0].strip()
    
    if not team_name:
        # Try to find team in query
        query_lower = query.lower()
        for canonical, aliases in TEAM_ALIASES.items():
            for alias in aliases:
                if alias in query_lower:
                    team_name = canonical
                    break
            if team_name:
                break
    
    if not team_name:
        return AssistantResponse(
            intent="team_analysis",
            message="Which team would you like me to analyze?",
            suggestions=[
                "Analyze Arsenal",
                "How is Liverpool doing?",
                "Manchester City form",
            ]
        )
    
    db = get_db_connection()
    
    # Get team stats
    stats_query = text("""
        WITH recent AS (
            SELECT result, home_score, away_score, date,
                   CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as venue
            FROM matches
            WHERE (home_team ILIKE :team OR away_team ILIKE :team)
              AND result IS NOT NULL
            ORDER BY date DESC
            LIMIT 10
        )
        SELECT 
            COUNT(*) as matches,
            COUNT(CASE WHEN (venue = 'home' AND result = 'home_win') OR (venue = 'away' AND result = 'away_win') THEN 1 END) as wins,
            COUNT(CASE WHEN result = 'draw' THEN 1 END) as draws,
            COUNT(CASE WHEN (venue = 'home' AND result = 'away_win') OR (venue = 'away' AND result = 'home_win') THEN 1 END) as losses,
            AVG(CASE WHEN venue = 'home' THEN home_score ELSE away_score END) as goals_for,
            AVG(CASE WHEN venue = 'home' THEN away_score ELSE home_score END) as goals_against
        FROM recent
    """)
    
    with db.connect() as conn:
        result = conn.execute(stats_query, {"team": f"%{team_name}%"}).fetchone()
    
    if not result or result[0] == 0:
        return AssistantResponse(
            intent="team_analysis",
            message=f"I couldn't find recent match data for {team_name.title()}. They might not be in our database.",
            suggestions=["What matches are on today?", "Show me the best bets"]
        )
    
    matches, wins, draws, losses = result[0], result[1] or 0, result[2] or 0, result[3] or 0
    goals_for = float(result[4] or 0)
    goals_against = float(result[5] or 0)
    
    # Determine form
    win_rate = wins / matches if matches > 0 else 0
    if win_rate >= 0.6:
        form_emoji = "🔥"
        form_text = "Excellent form"
    elif win_rate >= 0.4:
        form_emoji = "✅"
        form_text = "Good form"
    elif win_rate >= 0.2:
        form_emoji = "😐"
        form_text = "Mixed form"
    else:
        form_emoji = "📉"
        form_text = "Poor form"
    
    message = f"""📊 **{team_name.title()} - Last {matches} Matches**

{form_emoji} **Form:** {form_text}

**Record:** {wins}W - {draws}D - {losses}L
**Win Rate:** {win_rate*100:.0f}%
**Goals For:** {goals_for:.1f} per game
**Goals Against:** {goals_against:.1f} per game
**Goal Difference:** {goals_for - goals_against:+.1f} per game"""
    
    return AssistantResponse(
        intent="team_analysis",
        message=message,
        suggestions=[
            f"Predict {team_name.title()} vs Arsenal",
            "Show me the best bets",
            "What matches are on today?"
        ]
    )


# ============================================================================
# PARLAY ENRICHMENT - Add ML predictions to parlay legs
# ============================================================================

class ParlayLegInput(BaseModel):
    event_id: Optional[str] = None
    match_id: Optional[int] = None
    home_team: str
    away_team: str
    selection: str  # "HOME", "AWAY", or "DRAW"
    odds: float  # American odds
    bet_type: Optional[str] = "MONEYLINE"


class ParlayLegEnriched(BaseModel):
    home_team: str
    away_team: str
    selection: str
    american_odds: float
    decimal_odds: float
    implied_prob: float
    model_prob: Optional[float] = None
    edge_pct: Optional[float] = None
    confidence: Optional[str] = None
    has_value: bool = False
    competition: Optional[str] = None
    match_date: Optional[datetime] = None


class ParlayEnrichRequest(BaseModel):
    legs: List[ParlayLegInput]


class ParlayEnrichResponse(BaseModel):
    legs: List[ParlayLegEnriched]
    combined_odds_american: float
    combined_odds_decimal: float
    combined_implied_prob: float
    combined_model_prob: Optional[float] = None
    combined_edge_pct: Optional[float] = None
    parlay_ev: Optional[float] = None
    correlation_warnings: List[str] = []
    has_correlated_legs: bool = False
    overall_confidence: Optional[str] = None


def american_to_decimal(american_odds: float) -> float:
    """Convert American odds to decimal odds."""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_american(decimal_odds: float) -> float:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return (decimal_odds - 1) * 100
    else:
        return -100 / (decimal_odds - 1)


@router.post("/parlay/enrich", response_model=ParlayEnrichResponse)
async def enrich_parlay_legs(request: ParlayEnrichRequest):
    """
    Enrich parlay legs with ML predictions and edge calculations.
    
    For each leg:
    1. Look up match in database
    2. Get ML prediction probabilities
    3. Calculate edge (model prob - implied prob)
    4. Detect correlations between legs
    
    Returns enriched legs with value indicators and correlation warnings.
    """
    try:
        db = get_db_connection()
        enriched_legs = []
        correlation_warnings = []
        leagues_seen = {}
        teams_seen = set()
        
        combined_decimal = 1.0
        combined_model_prob = 1.0
        all_have_predictions = True
        
        for leg in request.legs:
            # Convert American to decimal odds
            decimal_odds = american_to_decimal(leg.odds)
            implied_prob = 1 / decimal_odds if decimal_odds > 1 else 0.5
            
            # Search for match in database
            search_query = text("""
                SELECT m.match_id, m.home_team, m.away_team, m.competition, m.date,
                       p.home_prob, p.draw_prob, p.away_prob
                FROM matches m
                LEFT JOIN predictions p ON m.match_id = p.match_id
                WHERE (LOWER(m.home_team) LIKE :home AND LOWER(m.away_team) LIKE :away)
                   OR (LOWER(m.home_team) LIKE :away AND LOWER(m.away_team) LIKE :home)
                ORDER BY m.date DESC
                LIMIT 1
            """)
            
            with db.connect() as conn:
                result = conn.execute(search_query, {
                    "home": f"%{leg.home_team.lower()}%",
                    "away": f"%{leg.away_team.lower()}%"
                }).fetchone()
            
            model_prob = None
            edge_pct = None
            confidence = None
            has_value = False
            competition = None
            match_date = None
            
            if result:
                competition = result[3]
                match_date = result[4]
                
                # Get the appropriate probability based on selection
                if result[5] is not None:  # Has prediction
                    home_prob = float(result[5])
                    draw_prob = float(result[6])
                    away_prob = float(result[7])
                    
                    if leg.selection.upper() == "HOME":
                        model_prob = home_prob
                    elif leg.selection.upper() == "AWAY":
                        model_prob = away_prob
                    elif leg.selection.upper() == "DRAW":
                        model_prob = draw_prob
                    
                    if model_prob is not None:
                        edge_pct = (model_prob - implied_prob) * 100
                        has_value = edge_pct > 0
                        
                        if edge_pct > 15:
                            confidence = "High"
                        elif edge_pct > 5:
                            confidence = "Medium"
                        elif edge_pct > 0:
                            confidence = "Low"
                        else:
                            confidence = "Negative"
                        
                        combined_model_prob *= model_prob
                else:
                    all_have_predictions = False
                
                # Check for correlations
                if competition:
                    if competition in leagues_seen:
                        correlation_warnings.append(
                            f"⚠️ Multiple bets in {competition}: {leagues_seen[competition]} and {leg.home_team} vs {leg.away_team}"
                        )
                    leagues_seen[competition] = f"{leg.home_team} vs {leg.away_team}"
            else:
                all_have_predictions = False
            
            # Check for same team in multiple legs
            for team in [leg.home_team.lower(), leg.away_team.lower()]:
                if team in teams_seen:
                    correlation_warnings.append(
                        f"⚠️ Same team appears in multiple legs: {team.title()}"
                    )
                teams_seen.add(team)
            
            combined_decimal *= decimal_odds
            
            enriched_legs.append(ParlayLegEnriched(
                home_team=leg.home_team,
                away_team=leg.away_team,
                selection=leg.selection,
                american_odds=leg.odds,
                decimal_odds=round(decimal_odds, 3),
                implied_prob=round(implied_prob, 4),
                model_prob=round(model_prob, 4) if model_prob else None,
                edge_pct=round(edge_pct, 2) if edge_pct is not None else None,
                confidence=confidence,
                has_value=has_value,
                competition=competition,
                match_date=match_date,
            ))
        
        # Calculate combined metrics
        combined_american = decimal_to_american(combined_decimal)
        combined_implied = 1 / combined_decimal if combined_decimal > 1 else 0
        
        combined_edge = None
        parlay_ev = None
        overall_confidence = None
        
        if all_have_predictions and combined_model_prob > 0:
            combined_edge = (combined_model_prob - combined_implied) * 100
            # EV = (win_prob * profit) - (lose_prob * stake)
            # For $1 stake: EV = (model_prob * (decimal - 1)) - ((1 - model_prob) * 1)
            parlay_ev = (combined_model_prob * (combined_decimal - 1)) - (1 - combined_model_prob)
            parlay_ev = round(parlay_ev * 100, 2)  # As percentage
            
            if combined_edge > 10:
                overall_confidence = "High"
            elif combined_edge > 0:
                overall_confidence = "Medium"
            else:
                overall_confidence = "Low"
        
        return ParlayEnrichResponse(
            legs=enriched_legs,
            combined_odds_american=round(combined_american),
            combined_odds_decimal=round(combined_decimal, 3),
            combined_implied_prob=round(combined_implied, 4),
            combined_model_prob=round(combined_model_prob, 4) if all_have_predictions else None,
            combined_edge_pct=round(combined_edge, 2) if combined_edge is not None else None,
            parlay_ev=parlay_ev,
            correlation_warnings=correlation_warnings,
            has_correlated_legs=len(correlation_warnings) > 0,
            overall_confidence=overall_confidence,
        )
    
    except Exception as e:
        logger.error(f"Parlay enrichment error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SUGGESTED PARLAYS - AI-generated parlay suggestions from best value bets
# ============================================================================

class SuggestedParlayLeg(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    selection: str
    american_odds: float
    decimal_odds: float
    model_prob: float
    edge_pct: float
    competition: Optional[str] = None
    match_date: Optional[datetime] = None


class SuggestedParlay(BaseModel):
    name: str
    description: str
    legs: List[SuggestedParlayLeg]
    combined_odds_american: float
    combined_odds_decimal: float
    combined_model_prob: float
    combined_edge_pct: float
    expected_value_pct: float
    confidence: str
    risk_level: str
    recommended_stake_pct: float


class SuggestedParlaysResponse(BaseModel):
    parlays: List[SuggestedParlay]
    generated_at: datetime


@router.get("/suggested-parlays", response_model=SuggestedParlaysResponse)
async def get_suggested_parlays(
    min_edge: float = Query(0.05, description="Minimum edge for each leg"),
    max_legs: int = Query(3, ge=2, le=5, description="Maximum legs per parlay"),
    bankroll: float = Query(1000.0, description="Bankroll for stake calculation"),
):
    """
    Generate AI-suggested parlays from best value bets.
    
    Creates multiple parlay suggestions:
    1. Conservative (2 legs, high confidence)
    2. Balanced (3 legs, mixed confidence)
    3. Aggressive (4-5 legs, higher risk/reward)
    
    Each parlay avoids correlated legs (same league).
    """
    try:
        db = get_db_connection()
        
        # Get all value bets
        date_filter = " AND m.date >= NOW()"
        status_filter = " AND (m.status IS NULL OR m.status NOT IN ('FINISHED', 'CANCELLED', 'POSTPONED'))"
        
        query = text(f"""
            SELECT 
                m.match_id, m.home_team, m.away_team, m.competition, m.date,
                p.home_prob, p.draw_prob, p.away_prob,
                COALESCE(AVG(o.home_win), 2.5) as home_odds,
                COALESCE(AVG(o.draw), 3.2) as draw_odds,
                COALESCE(AVG(o.away_win), 2.8) as away_odds
            FROM matches m
            INNER JOIN predictions p ON m.match_id = p.match_id
            LEFT JOIN odds o ON m.match_id = o.match_id
            WHERE m.home_team IS NOT NULL AND m.away_team IS NOT NULL AND p.home_prob IS NOT NULL
                {date_filter} {status_filter}
            GROUP BY m.match_id, m.home_team, m.away_team, m.competition, m.date,
                     p.home_prob, p.draw_prob, p.away_prob
            ORDER BY m.date ASC NULLS LAST
            LIMIT 50
        """)
        
        with db.connect() as conn:
            results = conn.execute(query).fetchall()
        
        # Build list of value bets
        value_bets = []
        for row in results:
            match_id = row[0]
            home_team = row[1]
            away_team = row[2]
            competition = row[3]
            match_date = row[4]
            home_prob, draw_prob, away_prob = float(row[5]), float(row[6]), float(row[7])
            home_odds, draw_odds, away_odds = float(row[8]), float(row[9]), float(row[10])
            
            # Check each outcome
            outcomes = [
                ("HOME", home_team, home_prob, home_odds),
                ("DRAW", "Draw", draw_prob, draw_odds),
                ("AWAY", away_team, away_prob, away_odds),
            ]
            
            for selection, team, model_prob, decimal_odds in outcomes:
                implied_prob = 1 / decimal_odds if decimal_odds > 1 else 0.5
                edge = model_prob - implied_prob
                
                if edge >= min_edge:
                    american_odds = (decimal_odds - 1) * 100 if decimal_odds >= 2 else -100 / (decimal_odds - 1)
                    value_bets.append({
                        "match_id": match_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "selection": selection,
                        "team": team,
                        "model_prob": model_prob,
                        "decimal_odds": decimal_odds,
                        "american_odds": round(american_odds),
                        "edge_pct": round(edge * 100, 2),
                        "competition": competition,
                        "match_date": match_date,
                    })
        
        # Sort by edge
        value_bets.sort(key=lambda x: x["edge_pct"], reverse=True)
        
        if len(value_bets) < 2:
            return SuggestedParlaysResponse(
                parlays=[],
                generated_at=datetime.now()
            )
        
        # Generate parlays
        parlays = []
        
        # 1. Conservative Parlay (2 legs, highest edge, different leagues)
        conservative_legs = []
        used_leagues = set()
        for bet in value_bets:
            if bet["competition"] not in used_leagues and len(conservative_legs) < 2:
                conservative_legs.append(bet)
                if bet["competition"]:
                    used_leagues.add(bet["competition"])
        
        if len(conservative_legs) >= 2:
            parlays.append(_build_parlay(
                "Conservative Pick",
                "Low-risk 2-leg parlay with highest edge bets from different leagues",
                conservative_legs,
                "Low"
            ))
        
        # 2. Balanced Parlay (3 legs, good edge, different leagues)
        balanced_legs = []
        used_leagues = set()
        for bet in value_bets:
            if bet["competition"] not in used_leagues and len(balanced_legs) < 3:
                balanced_legs.append(bet)
                if bet["competition"]:
                    used_leagues.add(bet["competition"])
        
        if len(balanced_legs) >= 3:
            parlays.append(_build_parlay(
                "Balanced Builder",
                "3-leg parlay balancing risk and reward across leagues",
                balanced_legs,
                "Medium"
            ))
        
        # 3. Value Hunter (3 legs, top edge only)
        if len(value_bets) >= 3:
            top_edge_legs = value_bets[:3]
            parlays.append(_build_parlay(
                "Value Hunter",
                "3-leg parlay focusing on highest edge opportunities",
                top_edge_legs,
                "Medium"
            ))
        
        # 4. Aggressive Parlay (4-5 legs, higher payout)
        if len(value_bets) >= max_legs:
            aggressive_legs = []
            used_leagues = set()
            for bet in value_bets:
                if len(aggressive_legs) < max_legs:
                    aggressive_legs.append(bet)
                    if bet["competition"]:
                        used_leagues.add(bet["competition"])
            
            parlays.append(_build_parlay(
                "High Roller",
                f"{len(aggressive_legs)}-leg parlay for maximum payout potential",
                aggressive_legs,
                "High"
            ))
        
        return SuggestedParlaysResponse(
            parlays=parlays,
            generated_at=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Suggested parlays error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_parlay(name: str, description: str, legs: list, risk_level: str) -> SuggestedParlay:
    """Helper to build a SuggestedParlay from legs."""
    combined_decimal = 1.0
    combined_model_prob = 1.0
    
    parlay_legs = []
    for leg in legs:
        combined_decimal *= leg["decimal_odds"]
        combined_model_prob *= leg["model_prob"]
        
        parlay_legs.append(SuggestedParlayLeg(
            match_id=leg["match_id"],
            home_team=leg["home_team"],
            away_team=leg["away_team"],
            selection=f"{leg['team']} ({leg['selection']})",
            american_odds=leg["american_odds"],
            decimal_odds=round(leg["decimal_odds"], 3),
            model_prob=round(leg["model_prob"], 4),
            edge_pct=leg["edge_pct"],
            competition=leg["competition"],
            match_date=leg["match_date"],
        ))
    
    combined_american = (combined_decimal - 1) * 100 if combined_decimal >= 2 else -100 / (combined_decimal - 1)
    combined_implied = 1 / combined_decimal if combined_decimal > 1 else 0
    combined_edge = (combined_model_prob - combined_implied) * 100
    
    # EV calculation
    ev_pct = (combined_model_prob * (combined_decimal - 1) - (1 - combined_model_prob)) * 100
    
    # Confidence based on combined edge
    if combined_edge > 15:
        confidence = "High"
    elif combined_edge > 5:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    # Kelly-based stake recommendation (quarter Kelly)
    b = combined_decimal - 1
    kelly_full = (b * combined_model_prob - (1 - combined_model_prob)) / b if b > 0 else 0
    recommended_stake_pct = max(0, min(kelly_full * 0.25 * 100, 10))  # Cap at 10%
    
    return SuggestedParlay(
        name=name,
        description=description,
        legs=parlay_legs,
        combined_odds_american=round(combined_american),
        combined_odds_decimal=round(combined_decimal, 3),
        combined_model_prob=round(combined_model_prob, 4),
        combined_edge_pct=round(combined_edge, 2),
        expected_value_pct=round(ev_pct, 2),
        confidence=confidence,
        risk_level=risk_level,
        recommended_stake_pct=round(recommended_stake_pct, 2),
    )


# =============================================================================
# FPL ADVISOR ENDPOINTS
# =============================================================================

class FPLPlayerResponse(BaseModel):
    id: int
    web_name: str
    team_name: str
    position: str
    price: float
    total_points: int
    form: float
    points_per_game: float
    selected_by_percent: float
    fixture_difficulty_avg: float
    expected_points: float
    value_score: float
    captain_score: float
    status: str
    chance_of_playing: Optional[int]
    news: str


class FPLTeamResponse(BaseModel):
    players: List[FPLPlayerResponse]
    starting_xi: List[FPLPlayerResponse]
    bench: List[FPLPlayerResponse]
    captain: FPLPlayerResponse
    vice_captain: FPLPlayerResponse
    formation: Dict[str, int]
    total_cost: float
    expected_points: float
    budget_remaining: float


class FPLAdviceResponse(BaseModel):
    generated_at: Optional[str]
    gameweek: Optional[int]
    optimal_team: Optional[FPLTeamResponse]
    top_goalkeepers: List[FPLPlayerResponse]
    top_defenders: List[FPLPlayerResponse]
    top_midfielders: List[FPLPlayerResponse]
    top_forwards: List[FPLPlayerResponse]
    captain_picks: List[FPLPlayerResponse]
    differential_picks: List[FPLPlayerResponse]
    value_picks: List[FPLPlayerResponse]


@router.get("/fpl/advice", response_model=FPLAdviceResponse)
async def get_fpl_advice(refresh: bool = Query(False, description="Force refresh data from FPL API")):
    """
    Get FPL team advice including optimal team, top picks, and recommendations.
    """
    import json
    from etl.fetch_fpl_data import FPL_PROCESSED_DIR, fetch_and_process_all
    from etl.fpl_optimizer import generate_fpl_advice
    
    try:
        latest_file = FPL_PROCESSED_DIR / "fpl_data_latest.json"
        
        # Refresh data if requested or if file doesn't exist
        if refresh or not latest_file.exists():
            logger.info("Fetching fresh FPL data...")
            fetch_and_process_all()
        
        # Load data
        with open(latest_file, "r") as f:
            fpl_data = json.load(f)
        
        # Generate advice
        advice = generate_fpl_advice(fpl_data)
        
        return advice
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="FPL data not found. Use refresh=true to fetch.")
    except Exception as e:
        logger.error(f"FPL advice error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpl/players", response_model=List[FPLPlayerResponse])
async def get_fpl_players(
    position: Optional[str] = Query(None, description="Filter by position (GKP, DEF, MID, FWD)"),
    team: Optional[str] = Query(None, description="Filter by team name"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    sort_by: str = Query("expected_points", description="Sort by: expected_points, form, value_score, price"),
    limit: int = Query(50, description="Number of players to return"),
):
    """
    Get FPL players with filtering and sorting options.
    """
    import json
    from etl.fetch_fpl_data import FPL_PROCESSED_DIR
    from etl.fpl_optimizer import load_players_from_data, _player_to_dict
    
    try:
        latest_file = FPL_PROCESSED_DIR / "fpl_data_latest.json"
        
        if not latest_file.exists():
            raise HTTPException(status_code=404, detail="FPL data not found. Call /fpl/advice?refresh=true first.")
        
        with open(latest_file, "r") as f:
            fpl_data = json.load(f)
        
        players = load_players_from_data(fpl_data)
        
        # Apply filters
        if position:
            players = [p for p in players if p.position == position.upper()]
        
        if team:
            players = [p for p in players if team.lower() in p.team_name.lower()]
        
        if min_price is not None:
            players = [p for p in players if p.price >= min_price]
        
        if max_price is not None:
            players = [p for p in players if p.price <= max_price]
        
        # Sort
        sort_key = {
            "expected_points": lambda p: p.expected_points,
            "form": lambda p: p.form,
            "value_score": lambda p: p.value_score,
            "price": lambda p: p.price,
            "total_points": lambda p: p.total_points,
        }.get(sort_by, lambda p: p.expected_points)
        
        players.sort(key=sort_key, reverse=True)
        
        # Limit and convert
        result = [_player_to_dict(p) for p in players[:limit]]
        
        return result
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="FPL data not found")
    except Exception as e:
        logger.error(f"FPL players error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpl/fixtures")
async def get_fpl_fixtures(
    team: Optional[str] = Query(None, description="Filter by team name"),
    gameweek: Optional[int] = Query(None, description="Filter by gameweek"),
    upcoming_only: bool = Query(True, description="Only show upcoming fixtures"),
):
    """
    Get FPL fixtures with difficulty ratings.
    """
    import json
    from etl.fetch_fpl_data import FPL_PROCESSED_DIR
    
    try:
        latest_file = FPL_PROCESSED_DIR / "fpl_data_latest.json"
        
        if not latest_file.exists():
            raise HTTPException(status_code=404, detail="FPL data not found")
        
        with open(latest_file, "r") as f:
            fpl_data = json.load(f)
        
        fixtures = fpl_data.get("fixtures", [])
        
        # Filter
        if upcoming_only:
            fixtures = [f for f in fixtures if not f.get("finished")]
        
        if gameweek:
            fixtures = [f for f in fixtures if f.get("gameweek") == gameweek]
        
        if team:
            fixtures = [
                f for f in fixtures 
                if team.lower() in (f.get("home_team", "") or "").lower() 
                or team.lower() in (f.get("away_team", "") or "").lower()
            ]
        
        return {
            "fixtures": fixtures,
            "current_gameweek": fpl_data.get("current_gameweek"),
            "next_gameweek": fpl_data.get("next_gameweek"),
        }
        
    except Exception as e:
        logger.error(f"FPL fixtures error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fpl/refresh")
async def refresh_fpl_data():
    """
    Force refresh FPL data from the official API.
    """
    from etl.fetch_fpl_data import fetch_and_process_all
    
    try:
        result = fetch_and_process_all()
        
        return {
            "status": "success",
            "message": "FPL data refreshed successfully",
            "players_count": len(result.get("players", [])),
            "fixtures_count": len(result.get("fixtures", [])),
            "current_gameweek": result.get("current_gameweek"),
            "next_gameweek": result.get("next_gameweek"),
            "fetched_at": result.get("fetched_at"),
        }
        
    except Exception as e:
        logger.error(f"FPL refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
