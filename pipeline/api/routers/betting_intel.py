"""Read-only intelligence: refresh jobs publish inputs; requests recheck freshness."""
from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException, Query

from api.betting_intel import SPORTS, build_intelligence, timestamp
from etl.betting_intel import SNAPSHOT_PATH

router = APIRouter(prefix='/betting-intel',tags=['betting intelligence'])


def read_snapshot():
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding='utf-8'))
        if payload.get('schema_version') != 1 or not isinstance(payload.get('fixtures'),list) or timestamp(payload.get('snapshot_at')) is None:
            raise ValueError('Unsupported snapshot')
        return payload
    except (OSError,ValueError):
        raise HTTPException(status_code=503,detail='Intelligence snapshot unavailable. Run python -m etl.betting_intel after the data refresh.')


def attach_state(result, payload, now):
    age = (now-timestamp(payload['snapshot_at'])).total_seconds()
    result.update(snapshot_at=payload['snapshot_at'],source_errors=payload.get('source_errors',[]),
                  snapshot_status='stale' if age>1800 or age<0 else 'partial' if payload.get('source_errors') else 'current',
                  model_policy=payload.get('model_policy'))
    return result


@router.get('')
def overview():
    payload, now = read_snapshot(), datetime.now(timezone.utc)
    summaries = []
    for sport in SPORTS:
        result = build_intelligence(sport,payload['fixtures'],now)
        summaries.append({'sport':sport,'label':result['label'],'summary':result['summary'],
                          'top_pick':next(iter(result['ai_picks']),None),
                          'next_prediction':next(iter(result['predictions']),None)})
    return attach_state({'sports':summaries,'generated_at':now.isoformat()},payload,now)


@router.get('/{sport}')
def sport_intelligence(sport: str, competition: str | None = Query(None,max_length=120)):
    if sport not in SPORTS:
        raise HTTPException(status_code=404,detail='Unsupported sport')
    payload, now = read_snapshot(), datetime.now(timezone.utc)
    fixtures = [f for f in payload['fixtures'] if not competition or f.get('competition') == competition]
    return attach_state(build_intelligence(sport,fixtures,now),payload,now)
