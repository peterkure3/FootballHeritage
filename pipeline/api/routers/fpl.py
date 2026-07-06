"""Fantasy Premier League advisor endpoints."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


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
def get_fpl_advice(refresh: bool = Query(False, description="Force refresh data from FPL API")):
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
        
        # Load data (use UTF-8 for player names with special characters)
        with open(latest_file, "r", encoding="utf-8") as f:
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
def get_fpl_players(
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
        
        with open(latest_file, "r", encoding="utf-8") as f:
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
def get_fpl_fixtures(
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
        
        with open(latest_file, "r", encoding="utf-8") as f:
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
def refresh_fpl_data():
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


