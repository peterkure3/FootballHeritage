"""Betting intelligence endpoints: devig, EV, arbitrage, value bets."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import LOG_LEVEL
from etl.utils import setup_logger
from api.db import get_db_connection, get_heritage_db_connection
from api.odds_math import arbitrage_two_way, devig_two_way, expected_value

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


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


@router.post("/intelligence/devig", response_model=DevigResponse)
def devig_endpoint(payload: DevigRequest):
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
def ev_endpoint(payload: EvRequest):
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
def ev_batch_endpoint(payload: EvBatchRequest):
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
def arbitrage_scan(payload: ArbitrageScanRequest):
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
def get_best_value_bets(
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

