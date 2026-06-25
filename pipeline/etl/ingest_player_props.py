"""
Ingest player props from The Odds API into the player_props table.
Supports player props markets: player_points, player_rebounds, player_assists,
player_passing_yards, player_rushing_yards, player_receiving_yards, etc.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    LOG_LEVEL,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    ODDS_API_SPORTS,
    ODDS_API_ODDS_FORMAT,
    API_TIMEOUT,
)
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger, retry_on_failure, get_requests_session

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
        return dt
    except Exception:
        return None


@retry_on_failure(max_attempts=3)
def fetch_player_props_for_sport(sport_key: str, regions: str = "us,au") -> List[Dict]:
    """Fetch player props for a given sport from The Odds API."""
    markets = ",".join(PLAYER_PROP_MARKETS)
    url = (
        f"{THE_ODDS_API_BASE_URL}/sports/{sport_key}/odds"
        f"?apiKey={THE_ODDS_API_KEY}"
        f"&regions={regions}"
        f"&markets={markets}"
        f"&oddsFormat={ODDS_API_ODDS_FORMAT}"
    )
    session = get_requests_session()
    resp = session.get(url, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def extract_player_props(event: Dict) -> List[Dict]:
    """Extract individual player props from an Odds API event response."""
    props = []
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    sport_key = event.get("sport_key", "")
    sport = _map_sport(sport_key)
    commence_time = _parse_dt(event.get("commence_time"))

    for bookmaker in event.get("bookmakers", []):
        book_name = bookmaker.get("title", "unknown")
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

                label = outcome.get("name", "").lower()
                if label in ("over", "yes"):
                    over_price = price
                    under_price = None
                elif label in ("under", "no"):
                    over_price = None
                    under_price = price
                else:
                    continue

                props.append({
                    "sport": sport,
                    "player_name": player_name,
                    "team": home_team if outcome.get("team") == home_team else away_team
                             if outcome.get("team") == away_team else None,
                    "market": market_key,
                    "line": float(point),
                    "over_odds": float(over_price) if over_price else None,
                    "under_odds": float(under_price) if under_price else None,
                    "source": book_name,
                    "source_updated_at": _parse_dt(bookmaker.get("last_update")),
                })
    return props


def write_player_props(engine, props: List[Dict]) -> int:
    """Write player props to the database using upsert."""
    from sqlalchemy import text

    written = 0
    with engine.begin() as conn:
        for prop in props:
            conn.execute(
                text("""
                    INSERT INTO player_props
                        (event_id, sport, player_name, team, market, line,
                         over_odds, under_odds, source, source_updated_at, is_active)
                    VALUES (
                        (SELECT id FROM events WHERE sport = :sport LIMIT 1),
                        :sport, :player_name, :team, :market, :line,
                        :over_odds, :under_odds, :source, :source_updated_at, true
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "sport": prop["sport"],
                    "player_name": prop["player_name"],
                    "team": prop["team"],
                    "market": prop["market"],
                    "line": prop["line"],
                    "over_odds": prop["over_odds"],
                    "under_odds": prop["under_odds"],
                    "source": prop["source"],
                    "source_updated_at": prop["source_updated_at"],
                },
            )
            written += 1
    return written


def run():
    """Main entry point: fetch and ingest player props for all tracked sports."""
    from sqlalchemy import create_engine

    engine = create_engine(HERITAGE_DATABASE_URI)
    total_written = 0

    for sport_key in ODDS_API_SPORTS:
        logger.info(f"Fetching player props for {sport_key}...")
        try:
            events = fetch_player_props_for_sport(sport_key)
            logger.info(f"  Got {len(events)} events with player props")
            for event in events:
                props = extract_player_props(event)
                if props:
                    n = write_player_props(engine, props)
                    total_written += n
                    logger.info(f"  Wrote {n} props for {event.get('home_team')} vs {event.get('away_team')}")
        except Exception as e:
            logger.error(f"  Failed to fetch/ingest props for {sport_key}: {e}")

    logger.info(f"Total player props written: {total_written}")
    return total_written


if __name__ == "__main__":
    run()
