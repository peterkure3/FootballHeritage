"""
Ingest player props from The Odds API into the player_props table.
Supports player props markets: player_points, player_rebounds, player_assists,
player_passing_yards, player_rushing_yards, player_receiving_yards, etc.
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    LOG_LEVEL,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    API_TIMEOUT,
    RAW_DATA_DIR,
)
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger, get_requests_session

logger = setup_logger(__name__, LOG_LEVEL)

PLAYER_PROP_MARKETS = [
    "player_points",
    "player_rebounds",
    "player_assists",
    "player_points_rebounds_assists",
    "player_passing_yards",
    "player_rushing_yards",
    "player_receiving_yards",
    "player_touchdowns",
    "player_home_runs",
    "player_hits",
    "player_strikeouts",
    "player_goalscorer",
]

SPORT_KEY_MAP = {
    "soccer": "soccer",
    "basketball": "basketball",
    "americanfootball": "americanfootball",
    "baseball": "baseball",
    "icehockey": "icehockey",
}


def _map_sport(sport_key: str) -> str:
    sk = sport_key.lower()
    for prefix, mapped in SPORT_KEY_MAP.items():
        if sk.startswith(prefix):
            return mapped
    return sport_key


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except Exception:
        return None


def fetch_player_props_for_sport(sport_key: str, regions: str = "us", max_events: int = 10) -> List[Dict]:
    """Additional markets require the event-odds endpoint, not bulk sport odds."""
    if not THE_ODDS_API_KEY:
        raise ValueError('The Odds API key is not configured')
    markets = ['player_points','player_rebounds','player_assists','player_points_rebounds_assists'] if sport_key.startswith('basketball_') else (
        ['player_passing_yards','player_rushing_yards','player_receiving_yards'] if sport_key.startswith('americanfootball_') else [])
    if not markets:
        return []
    session = get_requests_session()
    base = f'{THE_ODDS_API_BASE_URL}/sports/{sport_key}'
    resp = session.get(f'{base}/events',params={'apiKey':THE_ODDS_API_KEY},timeout=API_TIMEOUT)
    resp.raise_for_status()
    events = []
    upcoming = [event for event in resp.json() if _parse_dt(event.get('commence_time'))
                and _parse_dt(event['commence_time']) > datetime.now(timezone.utc)]
    for event in sorted(upcoming,key=lambda row:row['commence_time'])[:max_events]:
        response = session.get(f"{base}/events/{event['id']}/odds",params={
            'apiKey':THE_ODDS_API_KEY,'regions':regions,'markets':','.join(markets),'oddsFormat':'decimal'},timeout=API_TIMEOUT)
        response.raise_for_status()
        events.append({**event,**response.json(),'sport_key':sport_key})
    return events


def extract_player_props(event: Dict) -> List[Dict]:
    """Extract individual player props from an Odds API event response."""
    props = {}
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    sport_key = event.get("sport_key", "")
    sport = _map_sport(sport_key)
    commence_time = _parse_dt(event.get("commence_time"))

    for bookmaker in event.get("bookmakers", []):
        book_name = bookmaker.get("key")
        if not book_name:
            continue
        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            if market_key not in PLAYER_PROP_MARKETS:
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description", "")
                if not player_name:
                    continue

                point = outcome.get("point")
                if point is None:
                    continue

                price = outcome.get("price")
                if price is None:
                    continue

                try:
                    point, price = float(point), float(price)
                except (TypeError,ValueError):
                    continue
                if not math.isfinite(point) or not math.isfinite(price) or price<=1:
                    continue
                label = outcome.get("name", "").lower()
                if label not in ('over','under'):
                    continue

                observed = _parse_dt(market.get('last_update') or bookmaker.get('last_update'))
                if not observed or not commence_time or observed>=commence_time:
                    continue
                key = (book_name,market_key,player_name,point,observed)
                prop = props.setdefault(key,{
                    "sport": sport,
                    "league": sport_key,
                    "provider_event_id": event.get('id'),
                    "home_team": home_team,
                    "away_team": away_team,
                    "commence_time": commence_time,
                    "player_name": player_name,
                    "team": home_team if outcome.get("team") == home_team else away_team
                             if outcome.get("team") == away_team else None,
                    "market": market_key,
                    "line": float(point),
                    "over_odds": None,
                    "under_odds": None,
                    "source": book_name,
                    "source_updated_at": observed,
                })
                prop['over_odds' if label=='over' else 'under_odds'] = price
    return [prop for prop in props.values() if prop['over_odds'] is not None and prop['under_odds'] is not None]


def write_player_props(engine, props: List[Dict]) -> int:
    """Write player props to the database using upsert."""
    from sqlalchemy import text

    written = 0
    with engine.begin() as conn:
        for prop in props:
            from api.betting_intel import SPORTS, sport_key
            key = sport_key(prop['sport'],prop['league'])
            if not key or not prop.get('provider_event_id') or not prop.get('commence_time'):
                continue
            matches = conn.execute(text('''SELECT id FROM events
                WHERE LOWER(league)=ANY(:leagues) AND event_date=:commence_time
                  AND LOWER(home_team)=LOWER(:home_team) AND LOWER(away_team)=LOWER(:away_team)
                LIMIT 2'''), {**prop,'leagues':[prop['league'].lower(),SPORTS[key]['label'].lower()]}).scalars().all()
            if len(matches)!=1:
                logger.warning('Skipped prop without a unique fixture match')
                continue
            result = conn.execute(
                text("""
                    INSERT INTO player_props
                        (event_id, sport, league, player_name, team, market, line,
                         over_odds, under_odds, source, source_updated_at, is_active)
                    SELECT :event_id,
                        :sport, :league, :player_name, :team, :market, :line,
                        :over_odds, :under_odds, :source, :source_updated_at, true
                    WHERE NOT EXISTS (SELECT 1 FROM player_props WHERE event_id=:event_id
                        AND source=:source AND player_name=:player_name AND market=:market AND line=:line
                        AND source_updated_at=:source_updated_at)
                    ON CONFLICT DO NOTHING
                """),
                {**prop,'event_id':matches[0]},
            )
            written += result.rowcount
    return written


def run(sport_keys=None):
    """Bounded NBA props collection by default; provider quota is required."""
    from sqlalchemy import create_engine

    engine = create_engine(HERITAGE_DATABASE_URI)
    total_written = 0

    for sport_key in sport_keys or ['basketball_nba']:
        logger.info(f"Fetching player props for {sport_key}...")
        try:
            events = fetch_player_props_for_sport(sport_key)
            capture = RAW_DATA_DIR/'player_props'
            capture.mkdir(parents=True,exist_ok=True)
            path = capture/(sport_key+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
            path.write_text(json.dumps({'events':events,'fetched_at':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
            logger.info(f"  Got {len(events)} events with player props")
            for event in events:
                props = extract_player_props(event)
                if props:
                    n = write_player_props(engine, props)
                    total_written += n
                    logger.info(f"  Wrote {n} props for {event.get('home_team')} vs {event.get('away_team')}")
        except Exception as e:
            logger.error('Prop collection failed for %s: %s',sport_key,type(e).__name__)
            raise RuntimeError('Player prop provider unavailable; check access and quota') from None

    logger.info(f"Total player props written: {total_written}")
    return total_written


if __name__ == "__main__":
    run()
