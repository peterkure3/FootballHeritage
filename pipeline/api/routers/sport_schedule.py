"""Read-only schedule feed shared by sport home and schedule pages."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from api.betting_intel import SPORTS
from api.routers.betting_intel import read_snapshot
from api.sport_schedule import build_schedule
from etl.update_sport_results import load_recent_results

router = APIRouter(prefix='/sport-schedule', tags=['sport schedules'])


@router.get('/{sport}')
def sport_schedule(sport: str, start_date: date | None = None, end_date: date | None = None):
    if sport not in SPORTS or sport == 'football':
        raise HTTPException(status_code=404, detail='Unsupported schedule sport')
    now = datetime.now(timezone.utc)
    start = start_date or now.date() - timedelta(days=7)
    end = end_date or now.date() + timedelta(days=7)
    if end < start or (end - start).days > 31:
        raise HTTPException(status_code=422, detail='Choose an ordered date range of at most 32 days')
    issues, fixtures, results = [], [], []
    try:
        fixtures = read_snapshot()['fixtures']
    except HTTPException:
        issues.append('Upcoming schedule is unavailable')
    try:
        results = load_recent_results([SPORTS[sport]['league']])
    except (OSError, ValueError, KeyError, TypeError):
        issues.append('Verified final scores are unavailable')
    if len(issues) == 2:
        raise HTTPException(status_code=503, detail='Sport schedule sources are unavailable')
    result = build_schedule(sport, fixtures, results, start, end, now)
    return {**result, 'source_issues': issues}
