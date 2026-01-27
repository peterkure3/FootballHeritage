import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import sys

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL, THE_ODDS_API_DIR
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


def _iter_odds_files(raw_dir: Path) -> List[Path]:
    return sorted(raw_dir.glob("odds_*.json"), reverse=True)


def _parse_dt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        return value


def _map_sport(sport_key: Optional[str]) -> Optional[str]:
    if not sport_key:
        return None
    sk = sport_key.lower()
    if sk.startswith("soccer_"):
        return "football"
    if sk.startswith("basketball_"):
        return "basketball"
    return sport_key


def _normalize_selection(
    market_key: str,
    outcome_name: Optional[str],
    home_team: Optional[str],
    away_team: Optional[str],
) -> Optional[str]:
    if not outcome_name:
        return None

    mk = (market_key or "").lower()
    name = outcome_name.strip()

    if mk == "h2h":
        if home_team and name == home_team:
            return "HOME"
        if away_team and name == away_team:
            return "AWAY"
        if name.lower() == "draw":
            return "DRAW"
        return None

    if mk == "spreads":
        if home_team and name == home_team:
            return "HOME"
        if away_team and name == away_team:
            return "AWAY"
        return None

    if mk == "totals":
        if name.lower() == "over":
            return "OVER"
        if name.lower() == "under":
            return "UNDER"
        return None

    return None


def _extract_offers(
    event: Dict[str, Any],
    provider_book_key_to_book_key: Dict[str, str],
    provider: str,
    source_updated_at_fallback: Optional[str],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    provider_event_id = event.get("id")
    sport_key = event.get("sport_key")
    league = sport_key
    sport = _map_sport(sport_key)

    home_team = event.get("home_team")
    away_team = event.get("away_team")
    commence_time = _parse_dt(event.get("commence_time"))

    provider_event_row = {
        "provider": provider,
        "provider_event_id": provider_event_id,
        "sport": sport,
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "source_updated_at": _parse_dt(event.get("last_update")) or source_updated_at_fallback,
    }

    offers: List[Dict[str, Any]] = []

    for bookmaker in event.get("bookmakers", []) or []:
        provider_book_key = bookmaker.get("key")
        book_key = provider_book_key_to_book_key.get(provider_book_key)
        if not book_key:
            continue

        for market in bookmaker.get("markets", []) or []:
            market_key = (market.get("key") or "").lower()
            if market_key not in {"h2h", "spreads", "totals"}:
                continue

            market_updated_at = _parse_dt(market.get("last_update"))
            for outcome in market.get("outcomes", []) or []:
                selection = _normalize_selection(
                    market_key,
                    outcome.get("name"),
                    home_team,
                    away_team,
                )
                if not selection:
                    continue

                odds_decimal = outcome.get("price")
                try:
                    odds_decimal = float(odds_decimal) if odds_decimal is not None else None
                except Exception:
                    odds_decimal = None

                if odds_decimal is None or odds_decimal <= 1.0:
                    continue

                line = outcome.get("point")
                try:
                    line = float(line) if line is not None else None
                except Exception:
                    line = None

                offers.append(
                    {
                        "provider": provider,
                        "provider_event_id": provider_event_id,
                        "book_key": book_key,
                        "market": market_key,
                        "selection": selection,
                        "line": line,
                        "participant": None,
                        "odds_decimal": odds_decimal,
                        "source_updated_at": market_updated_at
                        or _parse_dt(bookmaker.get("last_update"))
                        or _parse_dt(event.get("last_update"))
                        or source_updated_at_fallback,
                    }
                )

    return provider_event_row, offers


def _load_enabled_books(conn) -> Dict[str, str]:
    rows = conn.execute(
        text(
            """
            SELECT provider_book_key, book_key
            FROM sportsbook_registry
            WHERE enabled = TRUE AND provider = 'oddsapi'
            """
        )
    ).fetchall()
    return {r[0]: r[1] for r in rows if r[0] and r[1]}


def ingest_latest_raw_files(max_files: int = 3) -> Dict[str, int]:
    engine = create_engine(HERITAGE_DATABASE_URI)

    files = _iter_odds_files(THE_ODDS_API_DIR)
    files = files[:max_files] if max_files and max_files > 0 else files

    inserted_events = 0
    inserted_offers = 0

    if not files:
        logger.info("No odds_*.json files found in %s", THE_ODDS_API_DIR)
        return {"events": 0, "offers": 0}

    provider = "oddsapi"

    try:
        with engine.begin() as conn:
            provider_book_key_to_book_key = _load_enabled_books(conn)
            if not provider_book_key_to_book_key:
                logger.warning("No enabled books found in sportsbook_registry for provider=oddsapi")

            upsert_provider_event = text(
                """
                INSERT INTO provider_events (
                    provider, provider_event_id, sport, league, home_team, away_team, commence_time, event_id, source_updated_at
                ) VALUES (
                    :provider, :provider_event_id, :sport, :league, :home_team, :away_team, :commence_time, NULL, :source_updated_at
                )
                ON CONFLICT (provider, provider_event_id)
                DO UPDATE SET
                    sport = EXCLUDED.sport,
                    league = EXCLUDED.league,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    commence_time = EXCLUDED.commence_time,
                    source_updated_at = EXCLUDED.source_updated_at
                """
            )

            insert_offer = text(
                """
                INSERT INTO odds_offers (
                    provider, provider_event_id, event_id, book_key, market, selection, line, participant, odds_decimal, source_updated_at
                ) VALUES (
                    :provider, :provider_event_id, NULL, :book_key, :market, :selection, :line, :participant, :odds_decimal, :source_updated_at
                )
                ON CONFLICT DO NOTHING
                """
            )

            for path in files:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)

                fetched_at = payload.get("fetched_at")
                source_updated_at_fallback = _parse_dt(fetched_at)

                events = payload.get("events") or []
                if not isinstance(events, list):
                    continue

                for event in events:
                    if not isinstance(event, dict):
                        continue

                    provider_event_row, offers = _extract_offers(
                        event,
                        provider_book_key_to_book_key,
                        provider,
                        source_updated_at_fallback,
                    )

                    if not provider_event_row.get("provider_event_id"):
                        continue

                    conn.execute(upsert_provider_event, provider_event_row)
                    inserted_events += 1

                    for offer in offers:
                        conn.execute(insert_offer, offer)
                        inserted_offers += 1

    except SQLAlchemyError as e:
        logger.error("Failed ingesting offers to heritage DB: %s", str(e), exc_info=True)
        raise

    logger.info("Ingested %s provider events and %s offers from %s file(s)", inserted_events, inserted_offers, len(files))
    return {"events": inserted_events, "offers": inserted_offers}


def main():
    ingest_latest_raw_files(max_files=3)


if __name__ == "__main__":
    main()
