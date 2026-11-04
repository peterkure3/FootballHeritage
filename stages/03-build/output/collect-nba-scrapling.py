"""Capture a bounded NBA snapshot using the workspace's Scrapling transport.

Run from pipeline/: .venv-scrapling/Scripts/python.exe ../stages/03-build/output/collect-nba-scrapling.py
"""
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from etl.scrapling_transport import ScraplingTransport, USER_AGENT


def main():
    now = datetime.now(timezone.utc)
    start, end = now.date() - timedelta(days=7), now.date() + timedelta(days=14)
    output = ROOT / "pipeline/data/raw/nba/scrapling" / now.strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    transport = ScraplingTransport()
    base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    sources = {
        "teams": base + "/teams?limit=100",
        "scoreboard": base + f"/scoreboard?dates={start:%Y%m%d}-{end:%Y%m%d}&limit=1000",
        "standings": "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings",
    }
    captures, payloads, failures = [], {}, []
    for name, url in sources.items():
        try:
            response = transport.get(url, timeout=45, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            raw = output / f"{name}-raw.json"
            raw.write_bytes(response.content)
            payloads[name] = payload
            captures.append({"name": name, "url": response.url, "http_status": response.status_code,
                "captured_at": datetime.now(timezone.utc).isoformat(), "file": raw.name,
                "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()})
            print(json.dumps({"source": name, "status": response.status_code}), flush=True)
        except Exception as exc:
            failures.append({"source": name, "error": str(exc)})
            print(json.dumps(failures[-1]), flush=True)
        time.sleep(1)

    teams = []
    for sport in payloads.get("teams", {}).get("sports", []):
        for league in sport.get("leagues", []):
            if league.get("abbreviation", "").lower() != "nba":
                continue
            for entry in league.get("teams", []):
                team = entry["team"]
                teams.append({"id": team["id"], "name": team["displayName"],
                    "abbreviation": team.get("abbreviation"), "location": team.get("location")})
    games, seen = [], set()
    for event in payloads.get("scoreboard", {}).get("events", []):
        for competition in event.get("competitions", []):
            identity = str(competition.get("id", event["id"]))
            if identity in seen:
                continue
            seen.add(identity)
            opponents = competition.get("competitors", [])
            home = next((x for x in opponents if x.get("homeAway") == "home"), None)
            away = next((x for x in opponents if x.get("homeAway") == "away"), None)
            if not home or not away:
                raise ValueError(f"Missing competitors for {identity}")
            status = competition.get("status", event.get("status", {})).get("type", {})
            completed = status.get("completed") is True
            state = status.get("state")
            def score(team):
                value = team.get("score")
                return int(value) if (completed or state == "in") and value is not None else None
            games.append({"id": identity, "league": "basketball_nba", "date": competition["date"],
                "home_team": home["team"]["displayName"], "away_team": away["team"]["displayName"],
                "home_team_id": home["team"]["id"], "away_team_id": away["team"]["id"],
                "home_score": score(home), "away_score": score(away), "completed": completed,
                "status": status.get("name"), "status_detail": status.get("detail"),
                "season": event.get("season", {}).get("year"),
                "season_type": event.get("season", {}).get("type"),
                "venue": competition.get("venue", {}).get("fullName"),
                "neutral_site": competition.get("neutralSite") is True,
                "provider": "espn", "captured_at": now.isoformat()})
    standings = []
    def walk(node, group=None):
        group = node.get("name", group)
        for entry in node.get("standings", {}).get("entries", []):
            standings.append({"team_id": entry["team"]["id"], "team": entry["team"]["displayName"],
                "group": group, "stats": {s["name"]: s.get("value", s.get("displayValue")) for s in entry.get("stats", [])}})
        for child in node.get("children", []):
            walk(child, group)
    walk(payloads.get("standings", {}))
    for name, rows in [("teams", teams), ("games", games), ("standings", standings)]:
        (output / f"{name}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        if rows:
            with (output / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows({key: json.dumps(value) if isinstance(value, dict) else value
                    for key, value in row.items()} for row in rows)
    if not teams or not games:
        failures.append({"source": "validation", "error": "Empty teams or games export"})
    if len(payloads.get("scoreboard", {}).get("events", [])) >= 1000:
        failures.append({"source": "validation", "error": "Scoreboard may be truncated at limit=1000"})
    manifest = {"transport": "scrapling", "provider": "espn", "captured_at": now.isoformat(),
        "date_start": str(start), "date_end": str(end), "teams": len(teams), "games": len(games),
        "completed_games": sum(x["completed"] for x in games), "standings_rows": len(standings),
        "season_types": dict(Counter(str(x["season_type"]) for x in games)),
        "captures": captures, "failures": failures,
        "note": "Season type 1 is preseason, 2 regular season, 3 playoffs. Scheduled scores are null. Standings reflect the provider's current season; inspect raw season metadata. No database writes or training."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), **manifest}, indent=2), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
