"""Match listing and service health endpoints."""

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
from api.db import get_db_connection

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


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

@router.get("/matches", response_model=List[MatchResponse])
def get_matches(
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
def health_check():
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


