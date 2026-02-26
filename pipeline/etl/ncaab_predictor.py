"""
NCAAB (NCAA Basketball) Prediction Engine.
Generates predictions for college basketball games using odds-implied probabilities
and basic statistical analysis.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

sys.path.append(str(Path(__file__).parent.parent))

from config import NCAAB_DATA_DIR, LOG_LEVEL
from etl.utils import setup_logger, load_json

logger = setup_logger(__name__, LOG_LEVEL)


@dataclass
class NcaabPrediction:
    """Represents a prediction for an NCAAB game."""
    event_id: str
    home_team: str
    away_team: str
    commence_time: str
    home_win_prob: float
    away_win_prob: float
    predicted_winner: str
    confidence: str  # "High", "Medium", "Low"
    spread: Optional[float] = None
    total: Optional[float] = None
    home_spread_odds: Optional[float] = None
    away_spread_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    best_bet: Optional[str] = None
    best_bet_odds: Optional[float] = None
    edge_pct: Optional[float] = None


def decimal_to_implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 1.0:
        return 0.0
    return 1.0 / decimal_odds


def remove_vig(prob_a: float, prob_b: float) -> tuple:
    """Remove vig from two-way market to get fair probabilities."""
    total = prob_a + prob_b
    if total <= 0:
        return 0.5, 0.5
    return prob_a / total, prob_b / total


def get_confidence_tier(prob: float) -> str:
    """Determine confidence tier based on win probability."""
    if prob >= 0.70:
        return "High"
    elif prob >= 0.55:
        return "Medium"
    else:
        return "Low"


def extract_odds_from_bookmakers(bookmakers: List[Dict]) -> Dict[str, Any]:
    """
    Extract best odds from bookmakers list.
    Returns dict with h2h, spreads, and totals.
    """
    result = {
        "h2h_home": None,
        "h2h_away": None,
        "spread": None,
        "spread_home_odds": None,
        "spread_away_odds": None,
        "total": None,
        "over_odds": None,
        "under_odds": None,
    }
    
    # Priority bookmakers (sharp books first)
    priority_books = ["pinnacle", "betfair", "draftkings", "fanduel", "betmgm"]
    
    for book_key in priority_books:
        for bookmaker in bookmakers:
            if bookmaker.get("key", "").lower() == book_key:
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key", "")
                    outcomes = market.get("outcomes", [])
                    
                    if market_key == "h2h" and not result["h2h_home"]:
                        for outcome in outcomes:
                            name = outcome.get("name", "")
                            price = outcome.get("price", 0)
                            # First outcome is typically away, second is home
                            # But we need to match by position or name
                            if len(outcomes) >= 2:
                                result["h2h_away"] = outcomes[0].get("price")
                                result["h2h_home"] = outcomes[1].get("price")
                    
                    elif market_key == "spreads" and not result["spread"]:
                        for outcome in outcomes:
                            point = outcome.get("point", 0)
                            price = outcome.get("price", 0)
                            # Home team spread
                            if point is not None:
                                if result["spread"] is None:
                                    result["spread"] = abs(point)
                                    result["spread_home_odds"] = price
                                else:
                                    result["spread_away_odds"] = price
                    
                    elif market_key == "totals" and not result["total"]:
                        for outcome in outcomes:
                            name = outcome.get("name", "").upper()
                            point = outcome.get("point", 0)
                            price = outcome.get("price", 0)
                            if name == "OVER":
                                result["total"] = point
                                result["over_odds"] = price
                            elif name == "UNDER":
                                result["under_odds"] = price
    
    # Fallback to any available bookmaker
    if not result["h2h_home"]:
        for bookmaker in bookmakers:
            for market in bookmaker.get("markets", []):
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    if len(outcomes) >= 2:
                        result["h2h_away"] = outcomes[0].get("price")
                        result["h2h_home"] = outcomes[1].get("price")
                        break
            if result["h2h_home"]:
                break
    
    return result


def generate_prediction(event: Dict[str, Any]) -> Optional[NcaabPrediction]:
    """
    Generate a prediction for a single NCAAB event.
    Uses odds-implied probabilities with vig removal.
    """
    event_id = event.get("id", "")
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    commence_time = event.get("commence_time", "")
    bookmakers = event.get("bookmakers", [])
    
    if not home_team or not away_team:
        return None
    
    # Extract odds
    odds = extract_odds_from_bookmakers(bookmakers)
    
    # Calculate probabilities from h2h odds
    if odds["h2h_home"] and odds["h2h_away"]:
        home_implied = decimal_to_implied_prob(odds["h2h_home"])
        away_implied = decimal_to_implied_prob(odds["h2h_away"])
        home_prob, away_prob = remove_vig(home_implied, away_implied)
    else:
        # Default to 50/50 if no odds available
        home_prob, away_prob = 0.5, 0.5
    
    # Determine winner and confidence
    if home_prob > away_prob:
        predicted_winner = home_team
        confidence = get_confidence_tier(home_prob)
    else:
        predicted_winner = away_team
        confidence = get_confidence_tier(away_prob)
    
    # Find best bet (highest edge)
    best_bet = None
    best_bet_odds = None
    edge_pct = None
    
    # Check spread value
    if odds["spread_home_odds"] and odds["spread_away_odds"]:
        home_spread_implied = decimal_to_implied_prob(odds["spread_home_odds"])
        away_spread_implied = decimal_to_implied_prob(odds["spread_away_odds"])
        home_spread_fair, away_spread_fair = remove_vig(home_spread_implied, away_spread_implied)
        
        # Edge = fair prob - implied prob
        home_edge = home_spread_fair - home_spread_implied
        away_edge = away_spread_fair - away_spread_implied
        
        if home_edge > 0.02:  # 2% edge threshold
            best_bet = f"{home_team} {odds['spread']:+.1f}" if odds['spread'] else f"{home_team} spread"
            best_bet_odds = odds["spread_home_odds"]
            edge_pct = home_edge * 100
        elif away_edge > 0.02:
            best_bet = f"{away_team} {-odds['spread']:+.1f}" if odds['spread'] else f"{away_team} spread"
            best_bet_odds = odds["spread_away_odds"]
            edge_pct = away_edge * 100
    
    return NcaabPrediction(
        event_id=event_id,
        home_team=home_team,
        away_team=away_team,
        commence_time=commence_time,
        home_win_prob=round(home_prob, 4),
        away_win_prob=round(away_prob, 4),
        predicted_winner=predicted_winner,
        confidence=confidence,
        spread=odds.get("spread"),
        total=odds.get("total"),
        home_spread_odds=odds.get("spread_home_odds"),
        away_spread_odds=odds.get("spread_away_odds"),
        over_odds=odds.get("over_odds"),
        under_odds=odds.get("under_odds"),
        best_bet=best_bet,
        best_bet_odds=best_bet_odds,
        edge_pct=round(edge_pct, 2) if edge_pct else None,
    )


def prediction_to_dict(pred: NcaabPrediction) -> Dict[str, Any]:
    """Convert prediction dataclass to dictionary."""
    return {
        "event_id": pred.event_id,
        "home_team": pred.home_team,
        "away_team": pred.away_team,
        "commence_time": pred.commence_time,
        "home_win_prob": pred.home_win_prob,
        "away_win_prob": pred.away_win_prob,
        "predicted_winner": pred.predicted_winner,
        "confidence": pred.confidence,
        "spread": pred.spread,
        "total": pred.total,
        "home_spread_odds": pred.home_spread_odds,
        "away_spread_odds": pred.away_spread_odds,
        "over_odds": pred.over_odds,
        "under_odds": pred.under_odds,
        "best_bet": pred.best_bet,
        "best_bet_odds": pred.best_bet_odds,
        "edge_pct": pred.edge_pct,
    }


def generate_all_predictions(odds_data: List[Dict]) -> List[Dict]:
    """
    Generate predictions for all NCAAB events.
    
    Args:
        odds_data: List of event dicts from The Odds API
        
    Returns:
        List of prediction dicts
    """
    predictions = []
    
    for event in odds_data:
        try:
            pred = generate_prediction(event)
            if pred:
                predictions.append(prediction_to_dict(pred))
        except Exception as e:
            logger.warning(f"Failed to generate prediction for event {event.get('id')}: {e}")
    
    # Sort by commence time
    predictions.sort(key=lambda x: x.get("commence_time", ""))
    
    logger.info(f"Generated {len(predictions)} NCAAB predictions")
    return predictions


def load_latest_odds() -> List[Dict]:
    """Load the most recent NCAAB odds file."""
    if not NCAAB_DATA_DIR.exists():
        logger.warning(f"NCAAB data directory does not exist: {NCAAB_DATA_DIR}")
        return []
    
    # Find most recent odds file
    odds_files = sorted(NCAAB_DATA_DIR.glob("ncaab_odds_*.json"), reverse=True)
    
    if not odds_files:
        logger.warning("No NCAAB odds files found")
        return []
    
    latest_file = odds_files[0]
    logger.info(f"Loading NCAAB odds from {latest_file}")
    
    return load_json(latest_file) or []


def get_ncaab_predictions() -> Dict[str, Any]:
    """
    Main function to get NCAAB predictions.
    Loads latest odds and generates predictions.
    """
    odds_data = load_latest_odds()
    
    if not odds_data:
        return {
            "predictions": [],
            "count": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "message": "No NCAAB odds data available. Run fetch_ncaab_odds.py first.",
        }
    
    predictions = generate_all_predictions(odds_data)
    
    return {
        "predictions": predictions,
        "count": len(predictions),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    result = get_ncaab_predictions()
    print(f"\nGenerated {result['count']} predictions")
    
    for pred in result["predictions"][:5]:
        print(f"\n{pred['away_team']} @ {pred['home_team']}")
        print(f"  Winner: {pred['predicted_winner']} ({pred['confidence']})")
        print(f"  Probs: Home {pred['home_win_prob']:.1%} | Away {pred['away_win_prob']:.1%}")
        if pred['spread']:
            print(f"  Spread: {pred['spread']}")
        if pred['best_bet']:
            print(f"  Best Bet: {pred['best_bet']} @ {pred['best_bet_odds']} (+{pred['edge_pct']}% edge)")
