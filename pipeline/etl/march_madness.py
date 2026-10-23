"""Source NCAA men's tournament games from ESPN's public scoreboard feed."""
import json
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "ncaab" / "brackets"
SOURCE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
ROUNDS = ["First Four", "Round of 64", "Round of 32", "Sweet 16", "Elite Eight", "Final Four", "Championship"]
ROUND_LABELS = {"first four": "First Four", "1st round": "Round of 64", "2nd round": "Round of 32", "sweet 16": "Sweet 16", "elite 8": "Elite Eight", "elite eight": "Elite Eight", "final four": "Final Four", "national semifinal": "Final Four", "national championship": "Championship"}


def normalize_event(event):
    competition = (event.get("competitions") or [{}])[0]
    headline = " ".join(note.get("headline", "") for note in competition.get("notes", []))
    if "NCAA Men's Basketball Championship" not in headline:
        return None
    round_name = next((label for source, label in ROUND_LABELS.items() if source in headline.lower()), None)
    if not round_name:
        raise ValueError(f"Unrecognized NCAA tournament round: {headline}")
    region_match = re.search(r"(East|West|South|Midwest) Region", headline)
    state = competition.get("status", event.get("status", {})).get("type", {})
    status = "finished" if state.get("completed") else "live" if state.get("state") == "in" else "upcoming"
    teams = []
    for entry in competition.get("competitors", []):
        team = entry.get("team", {})
        if not team.get("id"):
            continue
        seed = entry.get("curatedRank", {}).get("current")
        score = entry.get("score")
        teams.append({
            "id": str(team["id"]), "name": team.get("shortDisplayName") or team.get("displayName"),
            "full_name": team.get("displayName"), "logo": team.get("logo"),
            "seed": seed if isinstance(seed, int) and 1 <= seed <= 16 else None,
            "score": int(score) if status != "upcoming" and str(score).isdigit() else None,
            "winner": bool(entry.get("winner")) if status == "finished" else False,
            "record": next((record.get("summary") for record in entry.get("records", []) if record.get("type") == "total"), None),
            "url": next((link["href"] for link in team.get("links", []) if "clubhouse" in link.get("rel", [])), None),
        })
    if len(teams) != 2:
        raise ValueError(f"Tournament event {event.get('id')} has incomplete teams")
    return {"id": str(event["id"]), "date": event.get("date"), "round": round_name,
            "region": region_match.group(1) if region_match else None,
            "status": status, "status_detail": state.get("shortDetail") or state.get("description"),
            "venue": competition.get("venue", {}).get("fullName"), "teams": teams,
            "source_url": next((link["href"] for link in event.get("links", []) if "summary" in link.get("rel", [])), None)}


def build_bracket(events, season):
    games = {}
    for event in events:
        game = normalize_event(event)
        if game:
            games[game["id"]] = game
    games = sorted(games.values(), key=lambda game: (game["date"] or "", game["id"]))
    teams = {}
    for game in games:
        for team in game["teams"]:
            previous = teams.get(team["id"], {})
            teams[team["id"]] = {**team, "region": game["region"] or previous.get("region")}
    final = next((game for game in games if game["round"] == "Championship" and game["status"] == "finished"), None)
    champion = next((team for team in final["teams"] if team["winner"]), None) if final else None
    return {"season": season, "source": "ESPN", "source_url": SOURCE,
            "official_bracket_url": f"https://www.ncaa.com/brackets/basketball-men/d1/{season}",
            "fetched_at": datetime.now(timezone.utc).isoformat(), "stale": False,
            "status": "complete" if champion else "in_progress" if games else "unavailable",
            "champion": champion, "games": games, "teams": sorted(teams.values(), key=lambda team: team["name"]), "rounds": ROUNDS}


def fetch_bracket(season):
    # Single dates are supported by this feed; date-range requests return HTTP 400.
    start, end = date(season, 3, 14), date(season, 4, 10)
    dates = [(start + timedelta(days=offset)).strftime("%Y%m%d") for offset in range((end - start).days + 1)]
    def fetch_day(day):
        response = requests.get(SOURCE, params={"dates": day, "limit": 100}, timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("events"), list):
            raise ValueError("ESPN returned an invalid scoreboard")
        return payload["events"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        events = [event for daily in pool.map(fetch_day, dates) for event in daily]
    result = build_bracket(events, season)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA_DIR, suffix=".json", delete=False) as output:
        json.dump(result, output, ensure_ascii=False)
        temporary = Path(output.name)
    temporary.replace(DATA_DIR / f"{season}.json")
    return result


def get_bracket(season, refresh=False):
    path = DATA_DIR / f"{season}.json"
    cached = None
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    if cached and not refresh:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cached["fetched_at"])
        if cached.get("status") == "complete" or age.total_seconds() < 300:
            return cached
    try:
        return fetch_bracket(season)
    except (requests.RequestException, ValueError) as error:
        if cached:
            return {**cached, "stale": True, "warning": "Refresh failed. Showing the last successful tournament snapshot."}
        raise RuntimeError("Tournament data is unavailable from ESPN. Please retry.") from error


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=date.today().year)
    result = fetch_bracket(parser.parse_args().season)
    print(json.dumps({"season": result["season"], "games": len(result["games"]), "teams": len(result["teams"]), "champion": result["champion"], "rounds": {name: sum(game["round"] == name for game in result["games"]) for name in ROUNDS}}))
