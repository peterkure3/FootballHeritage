"""Sport identities, completed-game adapters and observed two-way moneylines."""

from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from config import RAW_DATA_DIR

SPORTS = {
    "basketball": {"leagues": ["basketball_nba", "basketball_ncaab"], "score_prior": 100., "window": 10, "home_advantage": 65., "classes": ["away_win", "home_win"]},
    "americanfootball": {"leagues": ["americanfootball_nfl", "americanfootball_ncaaf"], "score_prior": 24., "window": 8, "home_advantage": 45., "classes": ["away_win", "draw", "home_win"]},
    "baseball": {"leagues": ["baseball_mlb"], "score_prior": 4.5, "window": 20, "home_advantage": 25., "classes": ["away_win", "home_win"]},
    "icehockey": {"leagues": ["icehockey_nhl"], "score_prior": 3., "window": 10, "home_advantage": 40., "classes": ["away_win", "home_win"]},
    "wnba": {"leagues": ["basketball_wnba"], "score_prior": 80., "window": 10, "home_advantage": 55., "classes": ["away_win", "home_win"]},
    "ncaab": {"leagues": ["basketball_ncaab"], "score_prior": 70., "window": 10, "home_advantage": 55., "classes": ["away_win", "home_win"]},
    "ncaabw": {"leagues": ["basketball_wncaab"], "score_prior": 65., "window": 10, "home_advantage": 55., "classes": ["away_win", "home_win"]},
    "nfl": {"leagues": ["americanfootball_nfl"], "score_prior": 24., "window": 8, "home_advantage": 45., "classes": ["away_win", "home_win"], "conditional_on_decisive_result": True},
    "ncaaf": {"leagues": ["americanfootball_ncaaf"], "score_prior": 28., "window": 8, "home_advantage": 55., "classes": ["away_win", "home_win"]},
}


def capture_time(value) -> pd.Timestamp:
    """Legacy captures omit a timezone; wait two days instead of guessing one."""
    if isinstance(value, str) and len(value) == 15 and value[8] == "_":
        return pd.to_datetime(value, format="%Y%m%d_%H%M%S", utc=True).normalize() + pd.Timedelta(days=2)
    parsed = pd.to_datetime(value, utc=False)
    if parsed.tzinfo is None:
        raise ValueError("Capture timestamp lacks a timezone")
    return parsed.tz_convert("UTC")


def events_from(path: Path) -> tuple[list, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return (data, {}) if isinstance(data, list) else (data.get("events", []), data)


def identity_columns(frame: pd.DataFrame, sport: str) -> list[str]:
    if sport != "basketball" and "provider_event_id" in frame and frame.provider_event_id.notna().all():
        return ["league", "provider_event_id"]
    return ["league", "fixture_day", "home_key", "away_key"]


def canonical_games(rows: list[dict], sport: str) -> pd.DataFrame:
    if sport not in SPORTS:
        raise ValueError("Unsupported sport")
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    required = ["date", "league", "home_team", "away_team", "home_score", "away_score"]
    if not set(required).issubset(frame):
        raise ValueError("Missing completed-game fields")
    frame["date"] = pd.to_datetime(frame.date, utc=True, format="mixed", errors="raise")
    frame["result_available_at"] = pd.to_datetime(frame.result_available_at, utc=True, format="mixed", errors="raise")
    if not frame.league.isin(SPORTS[sport]["leagues"]).all():
        raise ValueError("Cross-sport training records are forbidden")
    if not frame.get("completed", pd.Series(False, index=frame.index)).eq(True).all():
        raise ValueError("Only explicitly completed games may train")
    for side in ["home", "away"]:
        frame[f"{side}_score"] = pd.to_numeric(frame[f"{side}_score"], errors="raise")
        score = frame[f"{side}_score"]
        if not (np.isfinite(score) & score.ge(0) & score.eq(np.floor(score))).all():
            raise ValueError("Invalid final score")
        frame[f"{side}_key"] = frame[f"{side}_team"].astype(str).str.casefold().str.strip()
    if frame.home_key.eq(frame.away_key).any() or frame.home_key.eq("").any() or frame.away_key.eq("").any():
        raise ValueError("Invalid competitors")
    frame["fixture_day"] = frame.date.dt.normalize()
    keys = identity_columns(frame, sport)
    if frame.groupby(keys)[["home_score", "away_score"]].nunique().gt(1).any().any():
        raise ValueError("Conflicting completed scores across sources")
    frame = frame.sort_values("result_available_at").drop_duplicates(keys, keep="first")
    frame["result"] = np.where(frame.home_score > frame.away_score, "home_win", np.where(frame.home_score < frame.away_score, "away_win", "draw"))
    if "draw" not in SPORTS[sport]["classes"] and not SPORTS[sport].get("conditional_on_decisive_result") and frame.result.eq("draw").any():
        raise ValueError("Tied final scores cannot train a two-way winner model")
    return frame.sort_values(["date", "league", "home_key", "away_key"]).reset_index(drop=True)


def load_games(sport: str, root: Path = RAW_DATA_DIR) -> pd.DataFrame:
    spec = SPORTS[sport]
    rows = []
    now = pd.Timestamp(datetime.now(timezone.utc))
    if sport in {"nfl", "ncaaf"}:
        for manifest_file in sorted((root / "historical/americanfootball_leagues").glob("*/manifest.json")):
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            path = manifest_file.parent / "normalized.jsonl"
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["normalized_sha256"]:
                raise ValueError("Historical American football capture checksum mismatch")
            rows.extend(row for line in path.read_text(encoding="utf-8").splitlines()
                        if line and (row := json.loads(line))["league"] in spec["leagues"])
    if sport in {"wnba", "ncaab", "ncaabw"}:
        for manifest_file in sorted((root / "historical/basketball_leagues").glob("*/manifest.json")):
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            path = manifest_file.parent / "normalized.jsonl"
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["normalized_sha256"]:
                raise ValueError("Historical basketball capture checksum mismatch")
            rows.extend(row for line in path.read_text(encoding="utf-8").splitlines()
                        if line and (row := json.loads(line))["league"] in spec["leagues"])
        if any(row.get("collection_scope") == "SEASON_RELEASE" for row in rows):
            rows = [row for row in rows if row.get("collection_scope") == "SEASON_RELEASE"]
    if sport == "basketball":
        for path in sorted((root / "historical/nba/games").glob("nba_games_*.json")):
            events, _ = events_from(path)
            for event in events:
                date = pd.to_datetime(event["date"], utc=True, errors="coerce")
                if pd.isna(date) or date >= now or pd.isna(event.get("home_pts")) or pd.isna(event.get("visitor_pts")):
                    continue
                rows.append({"date": date, "league": "basketball_nba", "home_team": event["home"], "away_team": event["visitor"],
                    "home_score": event["home_pts"], "away_score": event["visitor_pts"], "completed": True,
                    "result_available_at": date.normalize() + pd.Timedelta(days=2), "source_file": str(path), "date_precision": "DAY"})
    directories = [root / "the_odds_api"] + ([root / "nba"] if sport == "basketball" else [])
    if sport in {"nfl", "ncaaf"} and rows:
        # ESPN seasonal IDs and provider score IDs are different namespaces.
        # Prefer the historical corpus rather than duplicate the same fixture.
        directories = []
    all_stars = set()
    if sport == "wnba":
        # Older normalized captures did not retain ESPN's ALLSTAR type. Those
        # rosters have explicit Team ... names, not WNBA franchise identities.
        all_stars = {row["provider_event_id"] for row in rows if row.get("competition_type") == "ALLSTAR" or
                     row["home_team"].startswith("Team ") or row["away_team"].startswith("Team ")}
        rows = [row for row in rows if row["provider_event_id"] not in all_stars]
    if sport in {"ncaab", "ncaabw"} and any(row.get("collection_scope") == "SEASON_RELEASE" for row in rows):
        directories = []
    rows = [row for row in rows if pd.to_datetime(row["date"], utc=True) < now and pd.to_datetime(row["result_available_at"], utc=True) <= now]
    for directory in directories:
        paths = sorted({p for league in spec["leagues"] for p in directory.glob(f"scores_{league}_*.json")})
        if directory.name == "nba":
            paths = sorted(directory.glob("nba_scores_*.json"))
        for path in paths:
            events, metadata = events_from(path)
            for event in events:
                league = event.get("sport_key", "basketball_nba" if directory.name == "nba" else "")
                if league not in spec["leagues"] or event.get("completed") is not True:
                    continue
                date = pd.to_datetime(event["commence_time"], utc=True)
                scores = {score["name"]: score["score"] for score in event.get("scores") or []}
                if date >= now or not {event["home_team"], event["away_team"]}.issubset(scores):
                    continue
                # Without an explicit result observation timestamp, use the last
                # source update conservatively and never expose same-day outcomes.
                available = metadata.get("fetched_at") or event.get("last_update")
                if not available:
                    continue
                available = max(capture_time(available), date.normalize() + pd.Timedelta(days=1))
                if available > now:
                    continue
                rows.append({"date": date, "league": league, "home_team": event["home_team"], "away_team": event["away_team"],
                    "home_score": scores[event["home_team"]], "away_score": scores[event["away_team"]], "completed": True,
                    "result_available_at": available, "source_file": str(path), "provider_event_id": event["id"], "date_precision": "TIMESTAMP"})
    # Older repeated score captures contain contradictory finals. Quarantine the
    # entire fixture instead of picking a score or silently training on a correction.
    raw = pd.DataFrame(rows)
    excluded = 0
    examples = []
    if not raw.empty:
        raw["fixture_day"] = pd.to_datetime(raw.date, utc=True).dt.normalize()
        raw["home_key"] = raw.home_team.str.casefold().str.strip()
        raw["away_key"] = raw.away_team.str.casefold().str.strip()
        keys = identity_columns(raw, sport)
        for column in ["home_score", "away_score"]:
            raw[column] = pd.to_numeric(raw[column], errors="raise")
        conflicts = raw.groupby(keys)[["home_score", "away_score"]].nunique().gt(1).any(axis=1)
        bad = conflicts[conflicts].index
        excluded = len(bad)
        examples = [dict(zip(keys, [str(value) for value in key])) for key in list(bad)[:5]]
        raw = raw[~pd.MultiIndex.from_frame(raw[keys]).isin(bad)]
    games = canonical_games(raw.to_dict("records"), sport)
    games.attrs["data_quality"] = {"conflicting_fixtures_quarantined": excluded, "examples": examples}
    if sport == "wnba": games.attrs["data_quality"]["all_star_games_excluded"] = len(all_stars)
    return games


def attach_moneylines(games: pd.DataFrame, sport: str, root: Path = RAW_DATA_DIR) -> pd.DataFrame:
    """Only exact scheduled times and explicitly timestamped captures can join."""
    frame = games.copy()
    frame["home_win"], frame["away_win"] = np.nan, np.nan
    if frame.empty or sport == "americanfootball":
        # This model includes ties; two-way markets have different settlement rules.
        return frame
    offers = []
    for league in SPORTS[sport]["leagues"]:
        for path in sorted((root / "the_odds_api").glob(f"odds_{league}_*.json")):
            events, metadata = events_from(path)
            if not metadata.get("fetched_at"):
                continue
            observed = capture_time(metadata["fetched_at"])
            for event in events:
                if event.get("sport_key") != league:
                    continue
                kickoff = pd.to_datetime(event["commence_time"], utc=True)
                if observed >= kickoff:
                    continue
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("key") != "h2h":
                            continue
                        outcomes = market.get("outcomes", [])
                        prices = {o["name"]: o["price"] for o in outcomes}
                        if len(outcomes) != 2 or set(prices) != {event["home_team"], event["away_team"]}:
                            continue
                        h, a = float(prices[event["home_team"]]), float(prices[event["away_team"]])
                        if not np.isfinite([h, a]).all() or min(h, a) <= 1:
                            continue
                        offers.append({"league": league, "date": kickoff, "home_key": event["home_team"].casefold().strip(),
                            "away_key": event["away_team"].casefold().strip(), "bookmaker": bookmaker["key"],
                            "observed_at": observed, "home_win": h, "away_win": a})
    if offers:
        keys = ["league", "date", "home_key", "away_key"]
        latest = pd.DataFrame(offers).sort_values("observed_at").drop_duplicates(keys + ["bookmaker"], keep="last")
        average = latest.groupby(keys)[["home_win", "away_win"]].mean().reset_index()
        frame = frame.drop(columns=["home_win", "away_win"]).merge(average, on=keys, how="left", validate="one_to_one")
    return frame
