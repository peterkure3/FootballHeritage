"""Capture public ESPN results for independent WNBA and NCAA training corpora."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time
import io

import requests
import pandas as pd

from config import RAW_DATA_DIR

LEAGUES = {"wnba": ("wnba", "basketball_wnba"), "ncaab": ("mens-college-basketball", "basketball_ncaab"),
           "ncaabw": ("womens-college-basketball", "basketball_wncaab")}


def normalize_events(events, league, raw_ref, allow_ties=False):
    rows = []
    for event in events:
        if event.get("season", {}).get("type") not in {2, 3}:
            continue
        for competition in event.get("competitions", []):
            if competition.get("type", {}).get("abbreviation") == "ALLSTAR":
                continue
            if competition.get("status", {}).get("type", {}).get("completed") is not True:
                continue
            competitors = competition.get("competitors", [])
            if len(competitors) != 2:
                continue
            home = next((team for team in competitors if team.get("homeAway") == "home"), None)
            away = next((team for team in competitors if team.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            try:
                date = datetime.fromisoformat(competition["date"].replace("Z", "+00:00"))
                hs, aws = int(home["score"]), int(away["score"])
            except (ValueError, KeyError, TypeError):
                continue
            if min(hs, aws) < 0 or (hs == aws and not allow_ties) or date.tzinfo is None or date >= datetime.now(timezone.utc):
                continue
            available = date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
            rows.append({"date": date.isoformat(), "result_available_at": available.isoformat(),
                "league": league, "home_team": home["team"]["displayName"], "away_team": away["team"]["displayName"],
                "home_score": hs, "away_score": aws, "completed": True, "neutral_site": competition.get("neutralSite") is True,
                "provider": "espn", "provider_event_id": str(event["id"]), "competition_type": competition.get("type", {}).get("abbreviation"),
                "provider_home_team_id": str(home["team"]["id"]), "provider_away_team_id": str(away["team"]["id"]),
                "season": event["season"].get("year"), "season_type": event["season"]["type"],
                "source_file": raw_ref, "date_precision": "TIMESTAMP", "result_availability_precision": "CONSERVATIVE_TWO_DAYS"})
    return rows


def normalize_schedule(frame, league, raw_ref):
    rows = []
    now = pd.Timestamp(datetime.now(timezone.utc))
    for event in frame.to_dict("records"):
        if event.get("status_type_completed") != True or event.get("season_type") not in {2, 3}:
            continue
        date = pd.to_datetime(event["date"], utc=True)
        hs, aws = event.get("home_score"), event.get("away_score")
        if pd.isna(hs) or pd.isna(aws) or min(hs, aws) < 0 or hs == aws or date >= now:
            continue
        rows.append({"date": date.isoformat(), "result_available_at": (date.normalize() + pd.Timedelta(days=2)).isoformat(),
            "league": league, "home_team": event["home_display_name"], "away_team": event["away_display_name"],
            "home_score": hs, "away_score": aws, "completed": True, "neutral_site": event.get("neutral_site") is True,
            "provider": "sportsdataverse_espn", "provider_event_id": str(event["id"]),
            "provider_home_team_id": str(event["home_id"]), "provider_away_team_id": str(event["away_id"]),
            "season": event["season"], "season_type": event["season_type"], "source_file": raw_ref,
            "date_precision": "TIMESTAMP", "result_availability_precision": "CONSERVATIVE_TWO_DAYS", "collection_scope": "SEASON_RELEASE"})
    return rows


def collect(leagues, years, output=None):
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = output or RAW_DATA_DIR / "historical/basketball_leagues" / run
    output.mkdir(parents=True, exist_ok=False)
    records, captures = [], []
    for model in leagues:
        endpoint_key, league = LEAGUES[model]
        for year in years:
            if model != "wnba":
                tag = "espn_mens_college_basketball_schedules" if model == "ncaab" else "espn_womens_college_basketball_schedules"
                stem = "mbb" if model == "ncaab" else "wbb"
                url = f"https://github.com/sportsdataverse/sportsdataverse-data/releases/download/{tag}/{stem}_schedule_{year}.parquet"
                response = requests.get(url, timeout=(10, 60))
                response.raise_for_status()
                path = output / f"{model}_{year}.parquet"
                path.write_bytes(response.content)
                frame = pd.read_parquet(io.BytesIO(response.content))
                parsed = normalize_schedule(frame, league, str(path.resolve()))
                captured = datetime.now(timezone.utc).isoformat()
                for row in parsed: row["historical_retrieved_at"] = captured
                records.extend(parsed)
                report = {"model": model, "season": year, "source_url": url, "rows_returned": len(frame),
                    "completed_nonpreseason_games": len(parsed), "possibly_truncated": False, "collection_scope": "SEASON_RELEASE",
                    "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "first_game": min((row["date"] for row in parsed), default=None), "last_game": max((row["date"] for row in parsed), default=None)}
                captures.append(report)
                print(json.dumps(report), flush=True)
                time.sleep(.3)
                continue
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{endpoint_key}/scoreboard"
            params = {"dates": str(year), "limit": 1000}
            if model != "wnba": params["groups"] = "50"
            response = requests.get(url, params=params, timeout=(10, 60))
            response.raise_for_status()
            data = response.json()
            events = data.get("events", [])
            captured = datetime.now(timezone.utc).isoformat()
            path = output / f"{model}_{year}.json"
            path.write_text(json.dumps({"captured_at": captured, "source_url": response.url, "payload": data}), encoding="utf-8")
            parsed = normalize_events(events, league, str(path.resolve()))
            for row in parsed: row["historical_retrieved_at"] = captured
            records.extend(parsed)
            report = {"model": model, "year": year, "http_status": response.status_code, "source_url": response.url,
                "events_returned": len(events), "completed_nonpreseason_games": len(parsed),
                "possibly_truncated": len(events) >= 1000, "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "first_game": min((row["date"] for row in parsed), default=None), "last_game": max((row["date"] for row in parsed), default=None)}
            captures.append(report)
            print(json.dumps(report), flush=True)
            time.sleep(.3)
    with (output / "normalized.jsonl").open("x", encoding="utf-8") as stream:
        for row in records: stream.write(json.dumps(row) + "\n")
    manifest = {"run_id": run, "captures": captures, "records": len(records),
        "sampling_note": "College games use seasonal SportsDataverse ESPN release files; WNBA uses annual public ESPN scoreboards. Only completed nonpreseason games are retained.",
        "normalized_sha256": hashlib.sha256((output / "normalized.jsonl").read_bytes()).hexdigest()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Historical basketball capture: {output}", flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leagues", nargs="+", choices=list(LEAGUES), default=list(LEAGUES))
    parser.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023, 2024, 2025, 2026])
    args = parser.parse_args()
    if any(year < 2000 or year > datetime.now(timezone.utc).year for year in args.years):
        parser.error("Use historical years from 2000 through the current year")
    collect(list(dict.fromkeys(args.leagues)), sorted(set(args.years)))


if __name__ == "__main__":
    main()
