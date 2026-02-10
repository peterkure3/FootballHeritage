"""
Fetch Fantasy Premier League data from the official FPL API.
Stores player, team, fixture, and gameweek data for the FPL Advisor feature.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL, DATA_DIR
from etl.utils import setup_logger, save_json, get_timestamp_str

logger = setup_logger(__name__, LOG_LEVEL)

# FPL API endpoints
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
FPL_BOOTSTRAP_URL = f"{FPL_BASE_URL}/bootstrap-static/"
FPL_FIXTURES_URL = f"{FPL_BASE_URL}/fixtures/"
FPL_LIVE_URL = f"{FPL_BASE_URL}/event/{{event_id}}/live/"
FPL_PLAYER_URL = f"{FPL_BASE_URL}/element-summary/{{player_id}}/"

# Data directory for FPL
FPL_DATA_DIR = DATA_DIR / "fpl"
FPL_RAW_DIR = FPL_DATA_DIR / "raw"
FPL_PROCESSED_DIR = FPL_DATA_DIR / "processed"

# Ensure directories exist
FPL_RAW_DIR.mkdir(parents=True, exist_ok=True)
FPL_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


class FPLFetcher:
    """Fetcher for Fantasy Premier League API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.bootstrap_data = None
    
    def fetch_bootstrap(self) -> Dict[str, Any]:
        """
        Fetch bootstrap-static data containing all players, teams, and gameweeks.
        This is the main data source for FPL.
        """
        logger.info("Fetching FPL bootstrap data...")
        
        try:
            response = self.session.get(FPL_BOOTSTRAP_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Cache for reuse
            self.bootstrap_data = data
            
            # Save raw data
            timestamp = get_timestamp_str()
            save_json(data, FPL_RAW_DIR / f"bootstrap_{timestamp}.json")
            
            logger.info(
                "Fetched bootstrap: %d players, %d teams, %d gameweeks",
                len(data.get("elements", [])),
                len(data.get("teams", [])),
                len(data.get("events", []))
            )
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch FPL bootstrap: {e}")
            raise
    
    def fetch_fixtures(self) -> List[Dict[str, Any]]:
        """Fetch all fixtures for the season."""
        logger.info("Fetching FPL fixtures...")
        
        try:
            response = self.session.get(FPL_FIXTURES_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            timestamp = get_timestamp_str()
            save_json(data, FPL_RAW_DIR / f"fixtures_{timestamp}.json")
            
            logger.info(f"Fetched {len(data)} fixtures")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch FPL fixtures: {e}")
            raise
    
    def fetch_live_gameweek(self, event_id: int) -> Dict[str, Any]:
        """Fetch live data for a specific gameweek."""
        logger.info(f"Fetching live data for gameweek {event_id}...")
        
        try:
            url = FPL_LIVE_URL.format(event_id=event_id)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch live gameweek {event_id}: {e}")
            raise
    
    def fetch_player_details(self, player_id: int) -> Dict[str, Any]:
        """Fetch detailed history for a specific player."""
        try:
            url = FPL_PLAYER_URL.format(player_id=player_id)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch player {player_id}: {e}")
            raise
    
    def get_current_gameweek(self) -> Optional[int]:
        """Get the current gameweek number."""
        if not self.bootstrap_data:
            self.fetch_bootstrap()
        
        events = self.bootstrap_data.get("events", [])
        for event in events:
            if event.get("is_current"):
                return event.get("id")
        
        # If no current, find next
        for event in events:
            if event.get("is_next"):
                return event.get("id")
        
        return None
    
    def get_next_gameweek(self) -> Optional[int]:
        """Get the next gameweek number."""
        if not self.bootstrap_data:
            self.fetch_bootstrap()
        
        events = self.bootstrap_data.get("events", [])
        for event in events:
            if event.get("is_next"):
                return event.get("id")
        
        return None


def process_players(bootstrap_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process raw player data into a structured format for analysis.
    """
    players = bootstrap_data.get("elements", [])
    teams = {t["id"]: t for t in bootstrap_data.get("teams", [])}
    positions = {p["id"]: p for p in bootstrap_data.get("element_types", [])}
    
    processed = []
    for p in players:
        team = teams.get(p.get("team"), {})
        position = positions.get(p.get("element_type"), {})
        
        processed.append({
            "id": p.get("id"),
            "web_name": p.get("web_name"),
            "first_name": p.get("first_name"),
            "second_name": p.get("second_name"),
            "team_id": p.get("team"),
            "team_name": team.get("name"),
            "team_short": team.get("short_name"),
            "position_id": p.get("element_type"),
            "position": position.get("singular_name_short"),  # GKP, DEF, MID, FWD
            "price": p.get("now_cost", 0) / 10,  # Convert to millions
            "total_points": p.get("total_points", 0),
            "points_per_game": float(p.get("points_per_game", 0) or 0),
            "form": float(p.get("form", 0) or 0),
            "selected_by_percent": float(p.get("selected_by_percent", 0) or 0),
            "minutes": p.get("minutes", 0),
            "goals_scored": p.get("goals_scored", 0),
            "assists": p.get("assists", 0),
            "clean_sheets": p.get("clean_sheets", 0),
            "goals_conceded": p.get("goals_conceded", 0),
            "bonus": p.get("bonus", 0),
            "bps": p.get("bps", 0),
            "influence": float(p.get("influence", 0) or 0),
            "creativity": float(p.get("creativity", 0) or 0),
            "threat": float(p.get("threat", 0) or 0),
            "ict_index": float(p.get("ict_index", 0) or 0),
            "expected_goals": float(p.get("expected_goals", 0) or 0),
            "expected_assists": float(p.get("expected_assists", 0) or 0),
            "expected_goal_involvements": float(p.get("expected_goal_involvements", 0) or 0),
            "expected_goals_conceded": float(p.get("expected_goals_conceded", 0) or 0),
            "value_form": float(p.get("value_form", 0) or 0),
            "value_season": float(p.get("value_season", 0) or 0),
            "transfers_in_event": p.get("transfers_in_event", 0),
            "transfers_out_event": p.get("transfers_out_event", 0),
            "chance_of_playing_next_round": p.get("chance_of_playing_next_round"),
            "chance_of_playing_this_round": p.get("chance_of_playing_this_round"),
            "news": p.get("news", ""),
            "status": p.get("status"),  # a=available, d=doubtful, i=injured, s=suspended, u=unavailable
        })
    
    return processed


def process_fixtures(fixtures: List[Dict], teams: Dict[int, Dict]) -> List[Dict[str, Any]]:
    """Process fixtures with team names and difficulty ratings."""
    processed = []
    
    for f in fixtures:
        home_team = teams.get(f.get("team_h"), {})
        away_team = teams.get(f.get("team_a"), {})
        
        processed.append({
            "id": f.get("id"),
            "gameweek": f.get("event"),
            "home_team_id": f.get("team_h"),
            "away_team_id": f.get("team_a"),
            "home_team": home_team.get("name"),
            "away_team": away_team.get("name"),
            "home_team_short": home_team.get("short_name"),
            "away_team_short": away_team.get("short_name"),
            "home_difficulty": f.get("team_h_difficulty"),
            "away_difficulty": f.get("team_a_difficulty"),
            "kickoff_time": f.get("kickoff_time"),
            "finished": f.get("finished", False),
            "home_score": f.get("team_h_score"),
            "away_score": f.get("team_a_score"),
        })
    
    return processed


def calculate_fixture_difficulty(
    fixtures: List[Dict],
    team_id: int,
    next_n_gameweeks: int = 5
) -> Dict[str, Any]:
    """
    Calculate fixture difficulty rating for a team over next N gameweeks.
    Lower is easier (1-2 = easy, 3 = medium, 4-5 = hard).
    """
    team_fixtures = []
    
    for f in fixtures:
        if f.get("finished"):
            continue
        
        if f.get("home_team_id") == team_id:
            team_fixtures.append({
                "gameweek": f.get("gameweek"),
                "opponent": f.get("away_team_short"),
                "is_home": True,
                "difficulty": f.get("home_difficulty", 3),
            })
        elif f.get("away_team_id") == team_id:
            team_fixtures.append({
                "gameweek": f.get("gameweek"),
                "opponent": f.get("home_team_short"),
                "is_home": False,
                "difficulty": f.get("away_difficulty", 3),
            })
    
    # Sort by gameweek and take next N (handle None gameweeks)
    team_fixtures.sort(key=lambda x: x.get("gameweek") or 999)
    upcoming = team_fixtures[:next_n_gameweeks]
    
    if not upcoming:
        return {"fixtures": [], "avg_difficulty": 3.0, "total_difficulty": 0}
    
    total_diff = sum(f.get("difficulty", 3) for f in upcoming)
    avg_diff = total_diff / len(upcoming)
    
    return {
        "fixtures": upcoming,
        "avg_difficulty": round(avg_diff, 2),
        "total_difficulty": total_diff,
    }


def fetch_and_process_all() -> Dict[str, Any]:
    """
    Fetch all FPL data and process it for the advisor.
    Returns processed data ready for optimization.
    """
    fetcher = FPLFetcher()
    
    # Fetch data
    bootstrap = fetcher.fetch_bootstrap()
    fixtures_raw = fetcher.fetch_fixtures()
    
    # Process data
    teams = {t["id"]: t for t in bootstrap.get("teams", [])}
    players = process_players(bootstrap)
    fixtures = process_fixtures(fixtures_raw, teams)
    
    # Calculate fixture difficulty for each team
    team_difficulties = {}
    for team_id, team in teams.items():
        team_difficulties[team_id] = calculate_fixture_difficulty(fixtures, team_id)
    
    # Add fixture difficulty to players
    for player in players:
        team_id = player.get("team_id")
        if team_id in team_difficulties:
            player["fixture_difficulty"] = team_difficulties[team_id]
    
    # Get gameweek info
    current_gw = fetcher.get_current_gameweek()
    next_gw = fetcher.get_next_gameweek()
    
    result = {
        "fetched_at": datetime.now().isoformat(),
        "current_gameweek": current_gw,
        "next_gameweek": next_gw,
        "players": players,
        "fixtures": fixtures,
        "teams": list(teams.values()),
        "team_difficulties": team_difficulties,
    }
    
    # Save processed data
    timestamp = get_timestamp_str()
    save_json(result, FPL_PROCESSED_DIR / f"fpl_data_{timestamp}.json")
    
    # Also save as latest
    save_json(result, FPL_PROCESSED_DIR / "fpl_data_latest.json")
    
    logger.info(
        "Processed FPL data: %d players, %d fixtures, GW %s",
        len(players),
        len(fixtures),
        current_gw or next_gw
    )
    
    return result


def main():
    """Main entry point for FPL data fetching."""
    fetch_and_process_all()


if __name__ == "__main__":
    main()
