"""Explicit candidate previews for independently trained sport winner models."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.sport_predict import candidate_teams, catalog, predict_candidate

router = APIRouter(prefix="/sport-models", tags=["sport models"])


class CandidatePredictionRequest(BaseModel):
    candidate_id: str = Field(pattern=r"^\d{8}T\d{12}Z$")
    sport: Literal["football", "basketball", "americanfootball", "baseball", "icehockey", "wnba", "ncaab", "ncaabw", "nfl", "ncaaf"]
    league: str | None = None
    home_team: str = Field(min_length=1, max_length=120)
    away_team: str = Field(min_length=1, max_length=120)
    kickoff: str
    home_odds: float | None = Field(default=None, gt=1)
    away_odds: float | None = Field(default=None, gt=1)
    draw_odds: float | None = Field(default=None, gt=1)
    neutral_site: bool = False


@router.get("")
def sport_models():
    return {"runs": catalog()}


@router.post("/preview")
def sport_model_preview(request: CandidatePredictionRequest):
    try:
        return predict_candidate(request.candidate_id, request.sport, request.home_team, request.away_team,
                                 request.kickoff, request.league, request.home_odds, request.away_odds, request.draw_odds, request.neutral_site)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="This sport candidate is unavailable or lacks enough training data")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/teams")
def sport_model_teams(candidate_id: str, sport: str, league: str | None = None):
    try:
        return {"teams": candidate_teams(candidate_id, sport, league)}
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Team history is unavailable for this candidate")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
