"""
API routes for football betting predictions.
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
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
    odds_a: int
    odds_b: int
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
    odds: int
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


def american_to_decimal(odds: int) -> float:
    if odds == 0:
        raise ValueError("odds cannot be 0")
    if odds > 0:
        return 1.0 + (odds / 100.0)
    return 1.0 + (100.0 / abs(float(odds)))


def implied_probability_from_decimal(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1")
    return 1.0 / decimal_odds


def devig_two_way(odds_a: int, odds_b: int) -> Dict[str, float]:
    dec_a = american_to_decimal(odds_a)
    dec_b = american_to_decimal(odds_b)
    p1 = implied_probability_from_decimal(dec_a)
    p2 = implied_probability_from_decimal(dec_b)
    p_total = p1 + p2
    if p_total <= 0:
        raise ValueError("invalid implied probabilities")
    fair_p1 = p1 / p_total
    fair_p2 = p2 / p_total
    vig = p_total - 1.0
    return {"fair_prob_a": fair_p1, "fair_prob_b": fair_p2, "vig": vig}


def win_profit_from_american(odds: int, stake: float) -> float:
    if odds == 0:
        raise ValueError("odds cannot be 0")
    if stake <= 0:
        raise ValueError("stake must be > 0")
    if odds > 0:
        return stake * (odds / 100.0)
    return stake * (100.0 / abs(float(odds)))


def expected_value(true_probability: float, odds: int, stake: float) -> Dict[str, float]:
    if true_probability < 0 or true_probability > 1:
        raise ValueError("true_probability must be in [0, 1]")
    win_profit = win_profit_from_american(odds, stake)
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
    
    This endpoint allows you to get predictions for any matchup,
    even if the teams haven't played each other recently.
    
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
        
        # Load model
        model_dir = Path(__file__).parent.parent / "models" / "model_store"
        model_path = model_dir / "model_v1.0.0.pkl"
        features_path = model_dir / "features_v1.0.0.pkl"
        label_encoder_path = model_dir / "label_encoder_v1.0.0.pkl"
        
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Model not trained yet. Please run: python -m models.train_model"
            )
        
        model = joblib.load(model_path)
        feature_names = joblib.load(features_path)
        label_encoder = joblib.load(label_encoder_path)
        
        # Get team statistics from database
        engine = get_db_connection()
        
        # Calculate team form (last 5 matches)
        def get_team_stats(team_name):
            query = text("""
                WITH recent_matches AS (
                    SELECT 
                        CASE 
                            WHEN home_team ILIKE :team THEN 
                                CASE 
                                    WHEN result = 'home_win' THEN 1
                                    WHEN result = 'draw' THEN 0
                                    ELSE -1
                                END
                            WHEN away_team ILIKE :team THEN
                                CASE 
                                    WHEN result = 'away_win' THEN 1
                                    WHEN result = 'draw' THEN 0
                                    ELSE -1
                                END
                        END as result_value,
                        CASE 
                            WHEN home_team ILIKE :team THEN home_score - away_score
                            WHEN away_team ILIKE :team THEN away_score - home_score
                        END as goal_diff,
                        date
                    FROM matches
                    WHERE (home_team ILIKE :team OR away_team ILIKE :team)
                        AND result IS NOT NULL
                        AND home_score IS NOT NULL
                        AND away_score IS NOT NULL
                    ORDER BY date DESC
                    LIMIT 5
                )
                SELECT 
                    COUNT(CASE WHEN result_value = 1 THEN 1 END) as wins,
                    COUNT(CASE WHEN result_value = 0 THEN 1 END) as draws,
                    COUNT(CASE WHEN result_value = -1 THEN 1 END) as losses,
                    COALESCE(AVG(goal_diff), 0) as avg_gd
                FROM recent_matches
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {"team": f"%{team_name}%"}).fetchone()
            
            if result:
                return {
                    'wins': result[0] or 0,
                    'draws': result[1] or 0,
                    'losses': result[2] or 0,
                    'avg_gd': float(result[3] or 0.0)
                }
            return {'wins': 0, 'draws': 0, 'losses': 0, 'avg_gd': 0.0}
        
        # Get stats for both teams
        home_stats = get_team_stats(home_team)
        away_stats = get_team_stats(away_team)
        
        # Get average odds (use historical averages)
        odds_query = text("""
            SELECT 
                AVG(home_win) as avg_home_odds,
                AVG(draw) as avg_draw_odds,
                AVG(away_win) as avg_away_odds
            FROM odds
            WHERE home_win IS NOT NULL
        """)
        
        with engine.connect() as conn:
            odds_result = conn.execute(odds_query).fetchone()
        
        if odds_result and odds_result[0]:
            avg_home_odds = float(odds_result[0])
            avg_draw_odds = float(odds_result[1])
            avg_away_odds = float(odds_result[2])
        else:
            # Default odds if no data
            avg_home_odds = 2.5
            avg_draw_odds = 3.2
            avg_away_odds = 2.8
        
        # Build feature vector
        features = {
            'home_team_wins_last_n': home_stats['wins'],
            'home_team_draws_last_n': home_stats['draws'],
            'home_team_losses_last_n': home_stats['losses'],
            'away_team_wins_last_n': away_stats['wins'],
            'away_team_draws_last_n': away_stats['draws'],
            'away_team_losses_last_n': away_stats['losses'],
            'home_team_avg_gd_last_n': home_stats['avg_gd'],
            'away_team_avg_gd_last_n': away_stats['avg_gd'],
            'home_win': avg_home_odds,
            'draw': avg_draw_odds,
            'away_win': avg_away_odds,
            'odds_spread': max(avg_home_odds, avg_draw_odds, avg_away_odds) - 
                          min(avg_home_odds, avg_draw_odds, avg_away_odds)
        }
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([features])[feature_names]
        X = X.fillna(0)
        
        # Make prediction
        probabilities = model.predict_proba(X)[0]
        predicted_class = model.predict(X)[0]
        winner = label_encoder.inverse_transform([predicted_class])[0]
        
        # Map probabilities to outcomes
        prob_dict = dict(zip(label_encoder.classes_, probabilities))
        home_prob = prob_dict.get('home_win', 0.0)
        draw_prob = prob_dict.get('draw', 0.0)
        away_prob = prob_dict.get('away_win', 0.0)
        
        # Determine confidence level
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 0.6:
            confidence = "High"
        elif max_prob > 0.45:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Generate recommendation
        if winner == 'home_win':
            recommendation = f"{home_team} is favored to win at home"
        elif winner == 'away_win':
            recommendation = f"{away_team} is favored to win away"
        else:
            recommendation = "Match is likely to end in a draw"
        
        # Add context based on form
        if home_stats['wins'] >= 3:
            recommendation += f". {home_team} is in excellent form."
        elif home_stats['losses'] >= 3:
            recommendation += f". {home_team} is struggling recently."
        
        if away_stats['wins'] >= 3:
            recommendation += f" {away_team} is also in great form."
        elif away_stats['losses'] >= 3:
            recommendation += f" {away_team} has been losing recently."
        
        return WhatIfPredictionResponse(
            home_team=home_team,
            away_team=away_team,
            winner=winner,
            home_prob=float(home_prob),
            draw_prob=float(draw_prob),
            away_prob=float(away_prob),
            model_version="1.0.0",
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
        raise HTTPException(status_code=500, detail="Prediction failed")
