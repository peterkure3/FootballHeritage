"""Explicit parsers for anonymous public sportsbook price responses."""

from datetime import datetime, timezone
import math
from uuid import uuid4


def normalize_bovada(groups: list[dict], observed: str, raw_ref: str, run_id: str) -> list[dict]:
    observed_time = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    records = []
    for group in groups:
        league = next((part for part in group.get("path", []) if part.get("type") == "LEAGUE"), {})
        country = next((part.get("description") for part in group.get("path", []) if part.get("type") == "COUNTRY"), None)
        for event in group.get("events", []):
            if event.get("type") != "GAMEEVENT" or event.get("sport") != "SOCC" or event.get("live") is not False or event.get("status") != "U":
                continue
            try:
                kickoff = datetime.fromtimestamp(float(event["startTime"]) / 1000, timezone.utc)
                if kickoff <= observed_time:
                    continue
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                continue
            home = next((team for team in event.get("competitors", []) if team.get("home") is True), None)
            away = next((team for team in event.get("competitors", []) if team.get("home") is False), None)
            if not home or not away or not home.get("name") or not away.get("name") or home.get("id") == away.get("id") or not event.get("id") or not league.get("description"):
                continue
            for display in event.get("displayGroups", []):
                for market in display.get("markets", []):
                    period = market.get("period", {})
                    if market.get("key") != "3W-1X2" or market.get("status") != "O" or str(period.get("id")) != "100" or period.get("description") != "Regulation Time":
                        continue
                    outcomes = {}
                    for outcome in market.get("outcomes", []):
                        selection = {"H": "HOME", "A": "AWAY", "D": "DRAW"}.get(outcome.get("type"))
                        if not selection or outcome.get("status") != "O":
                            continue
                        if selection in {"HOME", "AWAY"}:
                            team = home if selection == "HOME" else away
                            if outcome.get("competitorId") != team.get("id"):
                                continue
                        price = outcome.get("price", {})
                        try:
                            decimal = float(price["decimal"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        if not math.isfinite(decimal) or decimal <= 1 or selection in outcomes:
                            outcomes = {}
                            break
                        outcomes[selection] = {"selection": selection, "selection_name_raw": outcome.get("description"),
                            "provider_selection_id": str(outcome.get("id", "")), "odds_decimal": decimal,
                            "odds_raw": price["decimal"], "odds_format_raw": "decimal", "status": "OPEN",
                            "line": None, "participant": None}
                    if set(outcomes) != {"HOME", "DRAW", "AWAY"}:
                        continue
                    source_updated = None
                    if event.get("lastModified") is not None:
                        try:
                            source_updated = datetime.fromtimestamp(float(event["lastModified"]) / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
                        except (TypeError, ValueError, OverflowError, OSError):
                            pass
                    records.append({"schema_version": "1.0", "snapshot_id": str(uuid4()),
                        "provider": "scraper_bovada", "collection_route": "direct_public_feed", "bookmaker": "bovada",
                        "provider_event_id": str(event["id"]), "provider_market_id": str(market.get("id", "")),
                        "provider_home_team_id": home.get("id"), "provider_away_team_id": away.get("id"),
                        "sport": "football", "competition": league["description"], "provider_competition_id": str(league.get("id", "")), "country": country,
                        "home_team": home["name"], "away_team": away["name"],
                        "commence_time": kickoff.isoformat().replace("+00:00", "Z"), "observed_at": observed,
                        "source_updated_at": source_updated, "is_live": False, "event_status": "SCHEDULED",
                        "market": "h2h", "market_name_raw": market.get("description"),
                        "period": "FULL_TIME_90_MIN", "settlement_rule": "REGULATION_TIME", "market_status": "OPEN",
                        "outcomes": [outcomes[key] for key in ["HOME", "DRAW", "AWAY"]], "region": None,
                        "source_url": "https://www.bovada.lv" + event.get("link", "/sports/soccer"),
                        "scraper_version": "1.0.0", "scrape_run_id": run_id, "raw_capture_ref": raw_ref})
    return records
