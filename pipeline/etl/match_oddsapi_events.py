from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import unicodedata
import re

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from config import LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


def _norm_team(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip().lower()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(ch for ch in v if not unicodedata.combining(ch))
    v = re.sub(r"[^a-z0-9\s]", " ", v)
    v = re.sub(r"\s+", " ", v).strip()
    for token in (" fc ", " cf ", " sc ", " afc ", " cfc "):
        v = v.replace(token, " ")
    v = re.sub(r"\s+", " ", v).strip()
    return v


def _team_match_score(a: str, b: str) -> int:
    """Higher is better. 0 means no match."""
    if not a or not b:
        return 0
    if a == b:
        return 100
    if a in b or b in a:
        return 80
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    if union == 0:
        return 0
    j = inter / union
    if j >= 0.6:
        return 70
    if j >= 0.45:
        return 55
    if j >= 0.34:
        return 40
    return 0


def _detect_sport_bucket(sport_value: Optional[str], league_value: Optional[str]) -> Optional[str]:
    """Return 'basketball' | 'football' | None based on provider_events.sport/league."""
    candidates = [sport_value, league_value]
    for v in candidates:
        if not v:
            continue
        vl = v.lower()
        if vl.startswith("basketball") or vl.startswith("basketball_"):
            return "basketball"
        if vl.startswith("soccer") or vl.startswith("soccer_"):
            return "football"
        if vl == "football":
            return "football"
    return None


def _time_window(commence_time: datetime, minutes: int = 90) -> Tuple[datetime, datetime]:
    delta = timedelta(minutes=minutes)
    return commence_time - delta, commence_time + delta


def link_oddsapi_events(time_window_minutes: int = 90, limit: int = 5000) -> Dict[str, int]:
    """Link provider_events/odds_offers to canonical events.

    Basketball: upsert events by (external_source='oddsapi', external_id=provider_event_id)
    Football: match to existing events by (home_team, away_team, event_date window)

    Returns counts.
    """

    engine = create_engine(HERITAGE_DATABASE_URI)

    basketball_upserts = 0
    football_links = 0
    offers_updated = 0

    try:
        with engine.begin() as conn:
            totals = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE provider = 'oddsapi') AS oddsapi_total,
                        COUNT(*) FILTER (WHERE provider = 'oddsapi' AND event_id IS NULL) AS oddsapi_unlinked,
                        COUNT(*) FILTER (WHERE provider = 'oddsapi' AND event_id IS NULL AND commence_time IS NOT NULL) AS oddsapi_candidates
                    FROM provider_events
                    """
                )
            ).fetchone()
            if totals:
                logger.info(
                    "provider_events totals: total=%s oddsapi_total=%s oddsapi_unlinked=%s oddsapi_candidates=%s",
                    totals[0],
                    totals[1],
                    totals[2],
                    totals[3],
                )

            sample = conn.execute(
                text(
                    """
                    SELECT provider_event_id, sport, league, home_team, away_team, commence_time
                    FROM provider_events
                    WHERE provider = 'oddsapi'
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
            ).fetchall()
            if sample:
                for s in sample:
                    logger.info(
                        "provider_events sample: provider_event_id=%s sport=%s league=%s home=%s away=%s commence=%s",
                        s[0],
                        s[1],
                        s[2],
                        s[3],
                        s[4],
                        s[5],
                    )

            provider_rows = conn.execute(
                text(
                    """
                    SELECT id, provider, provider_event_id, sport, league, home_team, away_team, commence_time
                    FROM provider_events
                    WHERE provider = 'oddsapi'
                    AND (event_id IS NULL)
                    AND commence_time IS NOT NULL
                    ORDER BY commence_time ASC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()

            for r in provider_rows:
                provider_event_uuid = r[0]
                provider = r[1]
                provider_event_id = r[2]
                sport_val = r[3]
                league_val = r[4]
                home_team = r[5]
                away_team = r[6]
                commence_time = r[7]

                bucket = _detect_sport_bucket(sport_val, league_val)

                if bucket == "basketball":
                    # Create/update canonical event using external tracking.
                    # NOTE: We cannot rely on ON CONFLICT here because events only has a partial
                    # unique index (external_id, external_source). Use select-then-update/insert.
                    existing = conn.execute(
                        text(
                            """
                            SELECT id
                            FROM events
                            WHERE external_source = 'oddsapi'
                              AND external_id = :external_id
                            LIMIT 1
                            """
                        ),
                        {"external_id": provider_event_id},
                    ).fetchone()

                    if existing:
                        event_id = existing[0]
                        conn.execute(
                            text(
                                """
                                UPDATE events
                                SET league = :league,
                                    home_team = :home_team,
                                    away_team = :away_team,
                                    event_date = :event_date
                                WHERE id = :id
                                """
                            ),
                            {
                                "id": event_id,
                                "league": league_val or "basketball",
                                "home_team": home_team,
                                "away_team": away_team,
                                "event_date": commence_time,
                            },
                        )
                    else:
                        res = conn.execute(
                            text(
                                """
                                INSERT INTO events (
                                    sport, league, home_team, away_team, event_date, status,
                                    external_id, external_source
                                ) VALUES (
                                    'basketball', :league, :home_team, :away_team, :event_date, 'UPCOMING',
                                    :external_id, 'oddsapi'
                                )
                                RETURNING id
                                """
                            ),
                            {
                                "league": league_val or "basketball",
                                "home_team": home_team,
                                "away_team": away_team,
                                "event_date": commence_time,
                                "external_id": provider_event_id,
                            },
                        ).fetchone()

                        if not res:
                            continue
                        event_id = res[0]

                    conn.execute(
                        text(
                            """
                            UPDATE provider_events
                            SET event_id = :event_id
                            WHERE id = :provider_events_id
                            """
                        ),
                        {"event_id": event_id, "provider_events_id": provider_event_uuid},
                    )

                    upd = conn.execute(
                        text(
                            """
                            UPDATE odds_offers
                            SET event_id = :event_id
                            WHERE provider = :provider
                            AND provider_event_id = :provider_event_id
                            AND event_id IS NULL
                            """
                        ),
                        {
                            "event_id": event_id,
                            "provider": provider,
                            "provider_event_id": provider_event_id,
                        },
                    )

                    basketball_upserts += 1
                    offers_updated += int(getattr(upd, "rowcount", 0) or 0)
                    continue

                if bucket == "football":
                    # Create canonical football event from OddsAPI (authoritative when football-data fixtures are missing).
                    # Same constraint issue as basketball: use select-then-update/insert.
                    existing = conn.execute(
                        text(
                            """
                            SELECT id
                            FROM events
                            WHERE external_source = 'oddsapi'
                              AND external_id = :external_id
                            LIMIT 1
                            """
                        ),
                        {"external_id": provider_event_id},
                    ).fetchone()

                    if existing:
                        event_id = existing[0]
                        conn.execute(
                            text(
                                """
                                UPDATE events
                                SET league = :league,
                                    home_team = :home_team,
                                    away_team = :away_team,
                                    event_date = :event_date
                                WHERE id = :id
                                """
                            ),
                            {
                                "id": event_id,
                                "league": league_val or "football",
                                "home_team": home_team,
                                "away_team": away_team,
                                "event_date": commence_time,
                            },
                        )
                    else:
                        res = conn.execute(
                            text(
                                """
                                INSERT INTO events (
                                    sport, league, home_team, away_team, event_date, status,
                                    external_id, external_source
                                ) VALUES (
                                    'football', :league, :home_team, :away_team, :event_date, 'UPCOMING',
                                    :external_id, 'oddsapi'
                                )
                                RETURNING id
                                """
                            ),
                            {
                                "league": league_val or "football",
                                "home_team": home_team,
                                "away_team": away_team,
                                "event_date": commence_time,
                                "external_id": provider_event_id,
                            },
                        ).fetchone()

                        if not res:
                            continue
                        event_id = res[0]

                    conn.execute(
                        text(
                            """
                            UPDATE provider_events
                            SET event_id = :event_id
                            WHERE id = :provider_events_id
                            """
                        ),
                        {"event_id": event_id, "provider_events_id": provider_event_uuid},
                    )

                    upd = conn.execute(
                        text(
                            """
                            UPDATE odds_offers
                            SET event_id = :event_id
                            WHERE provider = :provider
                            AND provider_event_id = :provider_event_id
                            AND event_id IS NULL
                            """
                        ),
                        {
                            "event_id": event_id,
                            "provider": provider,
                            "provider_event_id": provider_event_id,
                        },
                    )

                    football_links += 1
                    offers_updated += int(getattr(upd, "rowcount", 0) or 0)

    except SQLAlchemyError as e:
        logger.error("Event matching failed: %s", str(e), exc_info=True)
        raise

    logger.info(
        "Linked oddsapi events. basketball_upserts=%s football_links=%s offers_updated=%s",
        basketball_upserts,
        football_links,
        offers_updated,
    )

    return {
        "basketball_upserts": basketball_upserts,
        "football_links": football_links,
        "offers_updated": offers_updated,
    }


def main():
    link_oddsapi_events(time_window_minutes=90, limit=5000)


if __name__ == "__main__":
    main()
