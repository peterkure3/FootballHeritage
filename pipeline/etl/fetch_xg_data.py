"""
Fetch Expected Goals (xG) data from Understat for soccer ML feature improvement.
Uses the Understat API endpoints directly via requests (no Playwright needed
for the JSON API).

Rolling xG averages are calculated as features for the prediction model.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL, RAW_DATA_DIR, PROCESSED_DATA_DIR
from etl.cache import load_cache, store_cache
from etl.utils import setup_logger, retry_on_failure, ensure_dir, get_timestamp_str

logger = setup_logger(__name__, LOG_LEVEL)

UNDERSTAT_BASE_URL = "https://understat.com"
UNDERSTAT_API_URL = "https://understat.com/api"
XG_CACHE_TTL = 86400  # 24 hours

LEAGUE_MAP = {
    "EPL": "Premier League",
    "La Liga": "La Liga",
    "Bundesliga": "Bundesliga",
    "Serie A": "Serie A",
    "Ligue 1": "Ligue 1",
}


@retry_on_failure(max_attempts=3)
def fetch_league_xg_data(league_name: str, season: str = "2025") -> List[Dict]:
    """Fetch xG data for a league from Understat.

    Understat exposes a JSON API at api/... that returns match-level xG data.
    """
    url = f"{UNDERSTAT_BASE_URL}/league/{league_name}/{season}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    matches = []
    for match_data in data:
        matches.append({
            "id": match_data.get("id"),
            "season": season,
            "league": league_name,
            "date": match_data.get("datetime"),
            "home_team": match_data.get("h", {}).get("title"),
            "away_team": match_data.get("a", {}).get("title"),
            "home_goals": match_data.get("goals", {}).get("h"),
            "away_goals": match_data.get("goals", {}).get("a"),
            "home_xg": match_data.get("xG", {}).get("h"),
            "away_xg": match_data.get("xG", {}).get("a"),
            "home_xga": match_data.get("xGA", {}).get("h"),
            "away_xga": match_data.get("xGA", {}).get("a"),
            "home_deep": match_data.get("deep", {}).get("h"),
            "away_deep": match_data.get("deep", {}).get("a"),
            "home_ppda": match_data.get("ppda", {}).get("h", {}).get("att"),
            "away_ppda": match_data.get("ppda", {}).get("a", {}).get("att"),
        })
    return matches


def calculate_rolling_xg(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Calculate rolling xG averages for each team.

    Args:
        df: DataFrame with match-level xG data sorted by date
        window: Number of matches for rolling window

    Returns:
        DataFrame with rolling xG features
    """
    home_xg = df.groupby("home_team").apply(
        lambda g: g.sort_values("date")["home_xg"].rolling(window, min_periods=1).mean()
    ).reset_index(level=0, drop=True)

    away_xg = df.groupby("away_team").apply(
        lambda g: g.sort_values("date")["away_xg"].rolling(window, min_periods=1).mean()
    ).reset_index(level=0, drop=True)

    df["home_rolling_xg"] = home_xg
    df["away_rolling_xg"] = away_xg
    df["home_xg_advantage"] = df["home_rolling_xg"] - df["away_rolling_xg"]
    return df


def run():
    """Fetch xG data for all tracked leagues and save to processed data."""
    ensure_dir(PROCESSED_DATA_DIR)
    all_matches = []

    for league_key, league_name in LEAGUE_MAP.items():
        cache_key = {"endpoint": "xg_data", "league": league_name, "season": "2025"}
        cached = load_cache("xg_data", cache_key, XG_CACHE_TTL)
        if cached is not None:
            logger.info(f"Loaded cached xG data for {league_name} ({len(cached)} matches)")
            all_matches.extend(cached)
            continue

        logger.info(f"Fetching xG data for {league_name}...")
        try:
            matches = fetch_league_xg_data(league_name)
            if matches:
                all_matches.extend(matches)
                store_cache("xg_data", cache_key, matches)
                logger.info(f"  Got {len(matches)} matches with xG data")
            else:
                logger.warning(f"  No xG data returned for {league_name}")
        except Exception as e:
            logger.error(f"  Failed to fetch xG data for {league_name}: {e}")

    if not all_matches:
        logger.warning("No xG data fetched from any league")
        return

    df = pd.DataFrame(all_matches)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df = calculate_rolling_xg(df)

    timestamp = get_timestamp_str()
    output_path = PROCESSED_DATA_DIR / f"xg_features_{timestamp}.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved xG features to {output_path} ({len(df)} rows)")

    feature_summary = {
        "total_matches": len(df),
        "leagues": df["league"].unique().tolist(),
        "features": ["home_xg", "away_xg", "home_rolling_xg", "away_rolling_xg", "home_xg_advantage"],
    }
    logger.info(f"xG feature summary: {feature_summary}")
    return df


if __name__ == "__main__":
    run()
