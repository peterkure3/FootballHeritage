"""Parlay enrichment and suggested parlays."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from config import LOG_LEVEL
from etl.utils import setup_logger
from api.db import get_db_connection
from api.odds_math import american_to_decimal, decimal_to_american

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


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



@router.post("/parlay/enrich", response_model=ParlayEnrichResponse)
def enrich_parlay_legs(request: ParlayEnrichRequest):
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
def get_suggested_parlays(
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


