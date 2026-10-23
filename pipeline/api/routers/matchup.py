"""What-if matchup prediction through the same model service as batch inference."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from api.db import get_db_connection
from config import LOG_LEVEL
from etl.utils import setup_logger
from models.predict_v2 import predict_match

logger = setup_logger(__name__, LOG_LEVEL)
router = APIRouter()


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


@router.get("/predict-matchup", response_model=WhatIfPredictionResponse)
def predict_matchup(home_team: str = Query(..., min_length=1, description="Home team name"),
                    away_team: str = Query(..., min_length=1, description="Away team name")) -> WhatIfPredictionResponse:
    try:
        result = predict_match(home_team, away_team, engine=get_db_connection())
        winner = result["winner"]
        if winner == "draw":
            recommendation = f"Draw is the most likely outcome ({result['draw_prob']:.1%})."
        else:
            team = home_team if winner == "home_win" else away_team
            probability = result["home_prob"] if winner == "home_win" else result["away_prob"]
            recommendation = f"{team} is favored to win ({probability:.1%})."
        recommendation += " This hypothetical matchup uses fallback odds rather than a live market."
        return WhatIfPredictionResponse(home_team=home_team, away_team=away_team,
                                        recommendation=recommendation, **result)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=503, detail="Compatible model artifacts are unavailable")
    except SQLAlchemyError:
        logger.error("Matchup database query failed")
        raise HTTPException(status_code=503, detail="Prediction data is unavailable")
