"""The Predictions UI's aggregate fixture feed."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from api.prediction_dashboard import fixtures

router = APIRouter(prefix="/prediction-dashboard", tags=["predictions dashboard"])


@router.get("/operations")
def operations_overview():
    from api.operations import overview
    try:
        return overview()
    except (SQLAlchemyError, ValueError, OSError, KeyError, TypeError):
        raise HTTPException(status_code=503, detail="Operations overview is unavailable")


@router.get("/paper-trials")
def paper_trials():
    from models.paper_trial import dashboard
    try:
        return dashboard()
    except (ValueError, OSError, KeyError, TypeError):
        raise HTTPException(status_code=503, detail="Paper trial evidence is unavailable")


@router.get("/fixtures")
def fixture_feed(page: int = Query(1, ge=1), page_size: int = Query(6, ge=1, le=50),
                 competition: str | None = None, match_date: date | None = None):
    try:
        return fixtures(page, page_size, competition, match_date)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Prediction database is unavailable")
