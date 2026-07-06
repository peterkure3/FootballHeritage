"""NCAA basketball predictions and odds endpoints."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config import LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


# =============================================================================
# NCAAB (NCAA Basketball) Endpoints
# =============================================================================

@router.get("/ncaab/predictions")
def get_ncaab_predictions(
    limit: int = Query(50, description="Maximum number of predictions to return"),
    confidence: Optional[str] = Query(None, description="Filter by confidence: High, Medium, Low"),
):
    """
    Get NCAAB game predictions with win probabilities and best bets.
    """
    from etl.ncaab_predictor import get_ncaab_predictions
    
    try:
        result = get_ncaab_predictions()
        predictions = result.get("predictions", [])
        
        # Filter by confidence if specified
        if confidence:
            predictions = [p for p in predictions if p.get("confidence", "").lower() == confidence.lower()]
        
        # Apply limit
        predictions = predictions[:limit]
        
        return {
            "predictions": predictions,
            "count": len(predictions),
            "total_available": result.get("count", 0),
            "generated_at": result.get("generated_at"),
        }
        
    except Exception as e:
        logger.error(f"NCAAB predictions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ncaab/odds")
def get_ncaab_odds(
    limit: int = Query(50, description="Maximum number of games to return"),
):
    """
    Get current NCAAB odds from The Odds API.
    """
    from etl.ncaab_predictor import load_latest_odds
    
    try:
        odds_data = load_latest_odds()
        
        if not odds_data:
            return {
                "games": [],
                "count": 0,
                "message": "No NCAAB odds available. Run /ncaab/refresh to fetch.",
            }
        
        # Transform to simpler format
        games = []
        for event in odds_data[:limit]:
            bookmakers = event.get("bookmakers", [])
            
            # Get best odds from first available bookmaker
            h2h_odds = {}
            spread_odds = {}
            total_odds = {}
            
            for bm in bookmakers:
                for market in bm.get("markets", []):
                    key = market.get("key")
                    outcomes = market.get("outcomes", [])
                    
                    if key == "h2h" and not h2h_odds:
                        for o in outcomes:
                            h2h_odds[o.get("name")] = o.get("price")
                    
                    elif key == "spreads" and not spread_odds:
                        for o in outcomes:
                            spread_odds[o.get("name")] = {
                                "point": o.get("point"),
                                "price": o.get("price"),
                            }
                    
                    elif key == "totals" and not total_odds:
                        for o in outcomes:
                            total_odds[o.get("name")] = {
                                "point": o.get("point"),
                                "price": o.get("price"),
                            }
            
            games.append({
                "id": event.get("id"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "sport_key": event.get("sport_key"),
                "h2h": h2h_odds,
                "spreads": spread_odds,
                "totals": total_odds,
                "bookmaker_count": len(bookmakers),
            })
        
        return {
            "games": games,
            "count": len(games),
            "total_available": len(odds_data),
        }
        
    except Exception as e:
        logger.error(f"NCAAB odds error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ncaab/games")
def get_ncaab_games(
    status: Optional[str] = Query(None, description="Filter by status: upcoming, live, finished"),
    limit: int = Query(50, description="Maximum number of games to return"),
):
    """
    Get NCAAB games with odds, predictions, and scores combined.
    """
    from etl.ncaab_predictor import get_ncaab_predictions, load_latest_odds
    from config import NCAAB_DATA_DIR
    from etl.utils import load_json
    
    try:
        # Load predictions
        pred_result = get_ncaab_predictions()
        predictions_map = {p["event_id"]: p for p in pred_result.get("predictions", [])}
        
        # Load odds
        odds_data = load_latest_odds() or []
        
        if not odds_data:
            return {
                "games": [],
                "count": 0,
                "total_available": 0,
                "message": "No NCAAB data available. Click 'Refresh Data' to fetch from The Odds API.",
            }
        
        # Load scores if available
        scores_map = {}
        try:
            scores_files = sorted(NCAAB_DATA_DIR.glob("ncaab_scores_*.json"), reverse=True) if NCAAB_DATA_DIR.exists() else []
            if scores_files:
                scores_data = load_json(scores_files[0])
                if scores_data and isinstance(scores_data, list):
                    scores_map = {s.get("id"): s for s in scores_data if s and isinstance(s, dict)}
        except Exception as e:
            logger.warning(f"Could not load NCAAB scores: {e}")
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        games = []
        for event in odds_data:
            if not event or not isinstance(event, dict):
                continue
            
            event_id = event.get("id")
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            commence_time = event.get("commence_time")
            
            if not home_team or not away_team:
                continue
            
            # Filter out past games (unless they have scores)
            if commence_time:
                try:
                    game_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                    if game_time < now and not scores_map.get(event_id):
                        continue
                except (ValueError, TypeError):
                    pass
            
            # Get prediction
            pred = predictions_map.get(event_id, {})
            
            # Get score if available
            score = scores_map.get(event_id, {})
            home_score = None
            away_score = None
            game_status = "UPCOMING"
            
            if score:
                scores_list = score.get("scores") or []
                completed = score.get("completed", False)
                
                for s in scores_list:
                    if not s or not isinstance(s, dict):
                        continue
                    if s.get("name") == home_team:
                        home_score = s.get("score")
                    elif s.get("name") == away_team:
                        away_score = s.get("score")
                
                if completed:
                    game_status = "FINISHED"
                elif home_score is not None or away_score is not None:
                    game_status = "LIVE"
            
            # Filter by status
            if status:
                if status.lower() == "upcoming" and game_status != "UPCOMING":
                    continue
                elif status.lower() == "live" and game_status != "LIVE":
                    continue
                elif status.lower() == "finished" and game_status != "FINISHED":
                    continue
            
            # Extract odds
            bookmakers = event.get("bookmakers") or []
            odds_info = {}
            
            for bm in bookmakers[:1]:  # Just first bookmaker for simplicity
                if not bm or not isinstance(bm, dict):
                    continue
                markets = bm.get("markets") or []
                for market in markets:
                    if not market or not isinstance(market, dict):
                        continue
                    key = market.get("key")
                    outcomes = market.get("outcomes") or []
                    
                    if key == "spreads" and outcomes:
                        for o in outcomes:
                            if not o or not isinstance(o, dict):
                                continue
                            if o.get("name") == home_team:
                                point = o.get("point")
                                odds_info["spread"] = f"{home_team} {point:+.1f}" if point is not None else None
                    
                    elif key == "totals" and outcomes:
                        for o in outcomes:
                            if not o or not isinstance(o, dict):
                                continue
                            if o.get("name") == "Over":
                                odds_info["total"] = o.get("point")
            
            games.append({
                "id": event_id,
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": commence_time,
                "status": game_status,
                "home_score": int(home_score) if home_score else None,
                "away_score": int(away_score) if away_score else None,
                "competition": "NCAA Basketball",
                "odds": odds_info,
                "prediction": {
                    "predicted_winner": pred.get("predicted_winner"),
                    "home_win_prob": pred.get("home_win_prob"),
                    "away_win_prob": pred.get("away_win_prob"),
                    "confidence": pred.get("confidence"),
                    "best_bet": pred.get("best_bet"),
                    "edge_pct": pred.get("edge_pct"),
                } if pred else None,
            })
        
        # Sort by commence time
        games.sort(key=lambda x: x.get("commence_time", ""))
        
        # Get data freshness from file timestamp
        data_timestamp = None
        odds_files = sorted(NCAAB_DATA_DIR.glob("ncaab_odds_*.json"), reverse=True) if NCAAB_DATA_DIR.exists() else []
        if odds_files:
            # Extract timestamp from filename: ncaab_odds_YYYYMMDD_HHMMSS.json
            filename = odds_files[0].stem
            try:
                ts_str = filename.replace("ncaab_odds_", "")
                data_timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").isoformat()
            except ValueError:
                pass
        
        return {
            "games": games[:limit],
            "count": len(games[:limit]),
            "total_available": len(games),
            "data_timestamp": data_timestamp,
            "is_stale": len(games) == 0 and len(odds_data) > 0,
        }
        
    except Exception as e:
        logger.error(f"NCAAB games error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ncaab/refresh")
def refresh_ncaab_data():
    """
    Fetch fresh NCAAB odds and scores from The Odds API.
    """
    from etl.fetch_ncaab_odds import fetch_all_ncaab_data
    
    try:
        success = fetch_all_ncaab_data()
        
        if success:
            return {
                "status": "success",
                "message": "NCAAB data refreshed successfully",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch NCAAB data. Check API key configuration."
            )
        
    except Exception as e:
        logger.error(f"NCAAB refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


