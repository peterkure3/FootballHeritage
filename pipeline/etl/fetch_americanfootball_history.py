"""Capture completed NFL and FBS-participant college games with source provenance."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests

from config import RAW_DATA_DIR
from etl.fetch_basketball_history import normalize_events

LEAGUES = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}


def normalize_college_schedule(frame: pd.DataFrame, raw_ref: str) -> list[dict]:
    rows = []
    now = pd.Timestamp(datetime.now(timezone.utc))
    for event in frame.to_dict("records"):
        if event.get("completed") is not True or event.get("season_type_id") not in {2, 3}:
            continue
        # FBS vs FCS games are relevant to FBS team history; standalone lower
        # divisions and spring/exhibition games are outside this candidate scope.
        if event.get("fbs_participant") is not True:
            continue
        date = pd.to_datetime(event.get("start_date"), utc=True, errors="coerce")
        scores = [event.get("home_points"), event.get("away_points")]
        if pd.isna(date) or date >= now or any(pd.isna(score) for score in scores):
            continue
        if not np.isfinite(scores).all() or min(scores) < 0 or any(score != int(score) for score in scores):
            continue
        if scores[0] == scores[1]:
            raise ValueError("Unexpected tied final in an overtime college football schedule")
        rows.append({"date": date.isoformat(), "result_available_at": (date.normalize() + pd.Timedelta(days=2)).isoformat(),
            "league": LEAGUES["ncaaf"], "home_team": event["home_team"], "away_team": event["away_team"],
            "home_score": int(scores[0]), "away_score": int(scores[1]), "completed": True,
            "neutral_site": event.get("neutral_site") is True, "provider": "sportsdataverse_espn",
            "provider_event_id": str(event["game_id"]), "provider_home_team_id": str(event["home_id"]),
            "provider_away_team_id": str(event["away_id"]), "home_division": event.get("home_division"),
            "away_division": event.get("away_division"), "season": int(event["season"]),
            "season_type": int(event["season_type_id"]), "source_file": raw_ref,
            "date_precision": "DAY" if event.get("start_time_tbd") is True else "TIMESTAMP",
            "result_availability_precision": "CONSERVATIVE_TWO_DAYS", "collection_scope": "SEASON_RELEASE"})
    return rows


def canonical_team_names(rows: list[dict]) -> list[dict]:
    """Relocations and renamed teams retain their ESPN franchise/school identity."""
    latest = {}
    for row in sorted(rows, key=lambda value: value["date"]):
        for side in ["home", "away"]:
            latest[(row["league"], row[f"provider_{side}_team_id"])] = row[f"{side}_team"]
    for row in rows:
        for side in ["home", "away"]:
            row[f"source_{side}_team"] = row[f"{side}_team"]
            row[f"{side}_team"] = latest[(row["league"], row[f"provider_{side}_team_id"])]
    return rows


def nfl_coverage_audit(rows: list[dict], reference: pd.DataFrame, years: list[int]) -> dict:
    """Independent schedule cross-check, without importing its untimestamped odds."""
    day = pd.to_datetime(reference.gameday, utc=True)
    cutoff = pd.Timestamp(datetime.now(timezone.utc)).normalize() - pd.Timedelta(days=3)
    eligible = reference[day.dt.year.isin(years) & day.le(cutoff)
                         & reference.home_score.notna() & reference.away_score.notna()]
    expected = set(eligible.espn.dropna().astype(str).str.replace(r"\.0$", "", regex=True))
    captured = {row["provider_event_id"] for row in rows if row["league"] == LEAGUES["nfl"]}
    missing = sorted(expected - captured)
    if missing:
        raise ValueError(f"NFL scoreboard is missing {len(missing)} reference games: {missing[:10]}")
    return {"expected_completed_games": len(expected), "missing_games": 0,
            "through_local_game_day": cutoff.date().isoformat(), "reference_odds_used": False}


def collect(leagues: list[str], years: list[int], output: Path | None = None) -> Path:
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = output or RAW_DATA_DIR / "historical/americanfootball_leagues" / run
    output.mkdir(parents=True, exist_ok=False)
    records, captures = [], []
    for model in leagues:
        for year in years:
            if model == "ncaaf":
                url = f"https://github.com/sportsdataverse/sportsdataverse-data/releases/download/cfb_schedules/cfb_schedules_{year}.parquet"
                response = requests.get(url, timeout=(10, 60))
                response.raise_for_status()
                path = output / f"ncaaf_{year}.parquet"
                path.write_bytes(response.content)
                frame = pd.read_parquet(io.BytesIO(response.content))
                parsed = normalize_college_schedule(frame, str(path.resolve()))
                total = len(frame)
                possibly_truncated = False
            else:
                url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
                response = requests.get(url, params={"dates": str(year), "limit": 1000}, timeout=(10, 60))
                response.raise_for_status()
                data = response.json()
                events = data.get("events", [])
                total = len(events)
                possibly_truncated = total >= 1000
                path = output / f"nfl_{year}.json"
                path.write_text(json.dumps({"captured_at": datetime.now(timezone.utc).isoformat(),
                    "source_url": response.url, "payload": data}), encoding="utf-8")
                parsed = normalize_events(events, LEAGUES[model], str(path.resolve()), allow_ties=True)
                for row in parsed:
                    row["collection_scope"] = "CALENDAR_YEAR_SCOREBOARD"
            if possibly_truncated or not parsed:
                raise ValueError(f"Incomplete or empty historical response for {model}/{year}; capture retained for diagnosis")
            captured = datetime.now(timezone.utc).isoformat()
            for row in parsed:
                row["historical_retrieved_at"] = captured
            records.extend(parsed)
            report = {"model": model, "year": year, "source_url": url if model == "ncaaf" else response.url, "retrieved_at": captured,
                "rows_returned": total, "completed_games_in_scope": len(parsed), "possibly_truncated": possibly_truncated,
                "source_file": str(path.resolve()), "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "first_game": min(row["date"] for row in parsed), "last_game": max(row["date"] for row in parsed)}
            captures.append(report)
            print(json.dumps(report), flush=True)
            time.sleep(.3)
    coverage = None
    if "nfl" in leagues:
        url = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
        response = requests.get(url, timeout=(10, 60))
        response.raise_for_status()
        reference_path = output / "nflverse_coverage_reference.csv"
        reference_path.write_bytes(response.content)
        coverage = nfl_coverage_audit(records, pd.read_csv(io.BytesIO(response.content)), years)
        coverage.update(source_url=url, source_file=str(reference_path.resolve()),
                        capture_sha256=hashlib.sha256(response.content).hexdigest())
        print(json.dumps({"nfl_coverage": coverage}), flush=True)
    canonical_team_names(records)
    path = output / "normalized.jsonl"
    with path.open("x", encoding="utf-8") as stream:
        for row in records:
            stream.write(json.dumps(row) + "\n")
    manifest = {"run_id": run, "captures": captures, "records": len(records), "nfl_coverage": coverage,
        "normalized_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sampling_note": "NFL calendar-year ESPN scoreboards; college SportsDataverse ESPN seasonal releases with at least one FBS participant. Completed regular/postseason games only; NFL ties retained. Historical availability is estimated conservatively, not the retrieval timestamp."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Historical American football capture: {output}", flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leagues", nargs="+", choices=list(LEAGUES), default=list(LEAGUES))
    parser.add_argument("--years", nargs="+", type=int, default=list(range(2016, datetime.now(timezone.utc).year + 1)))
    args = parser.parse_args()
    if any(year < 2001 or year > datetime.now(timezone.utc).year for year in args.years):
        parser.error("Use historical years from 2001 through the current year")
    collect(list(dict.fromkeys(args.leagues)), sorted(set(args.years)))


if __name__ == "__main__":
    main()
