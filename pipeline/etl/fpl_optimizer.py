"""
FPL Team Optimizer - Suggests optimal Fantasy Premier League teams.
Uses linear programming to maximize expected points within budget and formation constraints.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

# FPL Constants
TOTAL_BUDGET = 100.0  # £100m
SQUAD_SIZE = 15
STARTING_XI = 11
BENCH_SIZE = 4
MAX_PER_TEAM = 3

# Position requirements
POSITION_LIMITS = {
    "GKP": {"min": 2, "max": 2},
    "DEF": {"min": 5, "max": 5},
    "MID": {"min": 5, "max": 5},
    "FWD": {"min": 3, "max": 3},
}

# Valid formations (outfield only, GK always 1)
VALID_FORMATIONS = [
    {"DEF": 3, "MID": 4, "FWD": 3},
    {"DEF": 3, "MID": 5, "FWD": 2},
    {"DEF": 4, "MID": 3, "FWD": 3},
    {"DEF": 4, "MID": 4, "FWD": 2},
    {"DEF": 4, "MID": 5, "FWD": 1},
    {"DEF": 5, "MID": 3, "FWD": 2},
    {"DEF": 5, "MID": 4, "FWD": 1},
]


@dataclass
class Player:
    """Represents an FPL player with scoring metrics."""
    id: int
    web_name: str
    team_id: int
    team_name: str
    position: str
    price: float
    total_points: int
    form: float
    points_per_game: float
    selected_by_percent: float
    fixture_difficulty_avg: float = 3.0
    expected_points: float = 0.0
    value_score: float = 0.0
    captain_score: float = 0.0
    status: str = "a"
    chance_of_playing: Optional[int] = 100
    news: str = ""
    
    @property
    def is_available(self) -> bool:
        """Check if player is available to play."""
        if self.status in ["i", "s", "u"]:  # injured, suspended, unavailable
            return False
        if self.chance_of_playing is not None and self.chance_of_playing < 50:
            return False
        return True


@dataclass
class TeamSuggestion:
    """Represents a suggested FPL team."""
    players: List[Player]
    starting_xi: List[Player]
    bench: List[Player]
    captain: Player
    vice_captain: Player
    formation: Dict[str, int]
    total_cost: float
    expected_points: float
    budget_remaining: float


def calculate_expected_points(player: Dict[str, Any], weights: Dict[str, float] = None) -> float:
    """
    Calculate expected points for a player based on multiple factors.
    
    Factors:
    - Form (recent performance)
    - Points per game (season average)
    - Fixture difficulty (upcoming matches)
    - ICT index (influence, creativity, threat)
    """
    if weights is None:
        weights = {
            "form": 0.35,
            "ppg": 0.25,
            "fixture": 0.20,
            "ict": 0.10,
            "xgi": 0.10,
        }
    
    form = player.get("form", 0) or 0
    ppg = player.get("points_per_game", 0) or 0
    ict = player.get("ict_index", 0) or 0
    xgi = player.get("expected_goal_involvements", 0) or 0
    
    # Fixture difficulty (invert so lower difficulty = higher score)
    fixture_diff = player.get("fixture_difficulty", {}).get("avg_difficulty", 3.0)
    fixture_score = (5 - fixture_diff) * 2  # Scale 0-8
    
    # Normalize ICT to similar scale as form
    ict_normalized = ict / 10 if ict else 0
    
    # Calculate weighted score
    expected = (
        weights["form"] * form +
        weights["ppg"] * ppg +
        weights["fixture"] * fixture_score +
        weights["ict"] * ict_normalized +
        weights["xgi"] * xgi * 4  # xGI typically 0-1, scale up
    )
    
    # Availability penalty
    chance = player.get("chance_of_playing_next_round")
    if chance is not None and chance < 100:
        expected *= (chance / 100)
    
    status = player.get("status", "a")
    if status in ["d"]:  # doubtful
        expected *= 0.75
    elif status in ["i", "s", "u"]:  # injured/suspended/unavailable
        expected *= 0.0
    
    return round(expected, 2)


def calculate_value_score(player: Dict[str, Any]) -> float:
    """
    Calculate value score (points per million).
    Higher = better value pick.
    """
    price = player.get("price", 0)
    if price <= 0:
        return 0
    
    expected = player.get("expected_points", 0)
    return round(expected / price, 3)


def calculate_captain_score(player: Dict[str, Any]) -> float:
    """
    Calculate captain suitability score.
    Factors: expected points, ownership (differential), fixture difficulty.
    """
    expected = player.get("expected_points", 0)
    ownership = player.get("selected_by_percent", 0) or 0
    
    # Differential bonus (less owned = higher differential value)
    differential_bonus = max(0, (50 - ownership) / 50) * 0.5
    
    # Captain score = expected points with differential consideration
    captain_score = expected * (1 + differential_bonus)
    
    return round(captain_score, 2)


def load_players_from_data(fpl_data: Dict[str, Any]) -> List[Player]:
    """Convert raw FPL data to Player objects with calculated scores."""
    players = []
    
    for p in fpl_data.get("players", []):
        # Calculate expected points
        expected = calculate_expected_points(p)
        p["expected_points"] = expected
        
        # Calculate value score
        value = calculate_value_score(p)
        
        # Calculate captain score
        captain = calculate_captain_score(p)
        
        fixture_diff = p.get("fixture_difficulty", {}).get("avg_difficulty", 3.0)
        
        player = Player(
            id=p.get("id"),
            web_name=p.get("web_name", ""),
            team_id=p.get("team_id"),
            team_name=p.get("team_name", ""),
            position=p.get("position", ""),
            price=p.get("price", 0),
            total_points=p.get("total_points", 0),
            form=p.get("form", 0),
            points_per_game=p.get("points_per_game", 0),
            selected_by_percent=p.get("selected_by_percent", 0),
            fixture_difficulty_avg=fixture_diff,
            expected_points=expected,
            value_score=value,
            captain_score=captain,
            status=p.get("status", "a"),
            chance_of_playing=p.get("chance_of_playing_next_round"),
            news=p.get("news", ""),
        )
        players.append(player)
    
    return players


def greedy_team_selection(
    players: List[Player],
    budget: float = TOTAL_BUDGET,
    prioritize: str = "expected_points"
) -> Optional[TeamSuggestion]:
    """
    Greedy algorithm to select optimal team within constraints.
    
    Args:
        players: List of available players
        budget: Total budget (default £100m)
        prioritize: Scoring metric to optimize ("expected_points", "value_score", "form")
    
    Returns:
        TeamSuggestion with optimal squad
    """
    # Filter available players
    available = [p for p in players if p.is_available and p.price > 0]
    
    if not available:
        logger.error("No available players found")
        return None
    
    # Track selected players
    selected: List[Player] = []
    position_counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
    team_counts: Dict[int, int] = {}
    remaining_budget = budget
    
    # Calculate target budget per position (weighted by typical costs)
    # GK: ~10%, DEF: ~25%, MID: ~35%, FWD: ~30%
    position_budget = {
        "GKP": budget * 0.10 / 2,   # 2 GKs, ~£5m each
        "DEF": budget * 0.25 / 5,   # 5 DEFs, ~£5m each
        "MID": budget * 0.35 / 5,   # 5 MIDs, ~£7m each
        "FWD": budget * 0.30 / 3,   # 3 FWDs, ~£10m each
    }
    
    # Fill each position with a mix of premium and budget players
    for position, limits in POSITION_LIMITS.items():
        position_players = [p for p in available if p.position == position]
        
        # Sort by value score (best points per million)
        position_players.sort(key=lambda p: (p.value_score or 0, p.expected_points or 0), reverse=True)
        
        slots_needed = limits["max"]
        avg_budget = position_budget[position]
        
        # First, pick best value players that fit budget
        for player in position_players:
            if position_counts[position] >= slots_needed:
                break
            
            if player in selected:
                continue
            if team_counts.get(player.team_id, 0) >= MAX_PER_TEAM:
                continue
            
            # For first half of slots, allow premium picks; for rest, be budget-conscious
            slots_filled = position_counts[position]
            if slots_filled < slots_needed // 2:
                # Premium slot - allow up to 1.5x average budget
                max_price = min(avg_budget * 1.8, remaining_budget)
            else:
                # Budget slot - stick to average or below
                max_price = min(avg_budget * 1.2, remaining_budget)
            
            if player.price > max_price:
                continue
            
            selected.append(player)
            position_counts[position] += 1
            team_counts[player.team_id] = team_counts.get(player.team_id, 0) + 1
            remaining_budget -= player.price
    
    # Second pass: fill any remaining slots with cheapest available
    for position, limits in POSITION_LIMITS.items():
        if position_counts[position] >= limits["max"]:
            continue
        
        position_players = [
            p for p in available 
            if p.position == position and p not in selected
        ]
        # Sort by price (cheapest first)
        position_players.sort(key=lambda p: p.price or 999)
        
        for player in position_players:
            if position_counts[position] >= limits["max"]:
                break
            
            if player.price > remaining_budget:
                continue
            if team_counts.get(player.team_id, 0) >= MAX_PER_TEAM:
                continue
            
            selected.append(player)
            position_counts[position] += 1
            team_counts[player.team_id] = team_counts.get(player.team_id, 0) + 1
            remaining_budget -= player.price
    
    # Verify we have a valid squad
    if len(selected) != SQUAD_SIZE:
        logger.warning(f"Could not fill squad: {len(selected)}/{SQUAD_SIZE} players (budget remaining: £{remaining_budget:.1f}m)")
        # Log what's missing
        for pos, limits in POSITION_LIMITS.items():
            if position_counts[pos] < limits["max"]:
                logger.warning(f"  Missing {limits['max'] - position_counts[pos]} {pos}")
        return None
    
    # Select starting XI with best formation
    starting_xi, bench, formation = select_starting_xi(selected)
    
    # Select captain and vice captain
    starting_xi.sort(key=lambda p: p.captain_score or 0, reverse=True)
    captain = starting_xi[0]
    vice_captain = starting_xi[1] if len(starting_xi) > 1 else starting_xi[0]
    
    # Calculate total expected points (captain gets 2x)
    total_expected = sum(p.expected_points for p in starting_xi)
    total_expected += captain.expected_points  # Captain bonus
    
    total_cost = sum(p.price for p in selected)
    
    return TeamSuggestion(
        players=selected,
        starting_xi=starting_xi,
        bench=bench,
        captain=captain,
        vice_captain=vice_captain,
        formation=formation,
        total_cost=round(total_cost, 1),
        expected_points=round(total_expected, 1),
        budget_remaining=round(budget - total_cost, 1),
    )


def select_starting_xi(squad: List[Player]) -> Tuple[List[Player], List[Player], Dict[str, int]]:
    """
    Select best starting XI from squad with valid formation.
    Returns (starting_xi, bench, formation).
    """
    # Group by position
    by_position = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        by_position[p.position].append(p)
    
    # Sort each position by expected points
    for pos in by_position:
        by_position[pos].sort(key=lambda p: p.expected_points or 0, reverse=True)
    
    best_xi = None
    best_bench = None
    best_formation = None
    best_points = -1
    
    # Try each valid formation
    for formation in VALID_FORMATIONS:
        xi = []
        bench = []
        
        # Always 1 GK in starting XI
        if len(by_position["GKP"]) >= 1:
            xi.append(by_position["GKP"][0])
            bench.extend(by_position["GKP"][1:])
        else:
            continue
        
        # Add outfield players per formation
        valid = True
        for pos in ["DEF", "MID", "FWD"]:
            required = formation[pos]
            available_pos = by_position[pos]
            
            if len(available_pos) < required:
                valid = False
                break
            
            xi.extend(available_pos[:required])
            bench.extend(available_pos[required:])
        
        if not valid or len(xi) != STARTING_XI:
            continue
        
        # Calculate total points
        total = sum(p.expected_points for p in xi)
        
        if total > best_points:
            best_points = total
            best_xi = xi
            best_bench = bench
            best_formation = formation
    
    if best_xi is None:
        # Fallback to first valid formation
        best_xi = squad[:STARTING_XI]
        best_bench = squad[STARTING_XI:]
        best_formation = {"DEF": 4, "MID": 4, "FWD": 2}
    
    return best_xi, best_bench, best_formation


def get_top_picks_by_position(
    players: List[Player],
    position: str,
    limit: int = 10,
    sort_by: str = "expected_points"
) -> List[Player]:
    """Get top players for a specific position."""
    position_players = [p for p in players if p.position == position and p.is_available]
    
    if sort_by == "value_score":
        position_players.sort(key=lambda p: p.value_score or 0, reverse=True)
    elif sort_by == "form":
        position_players.sort(key=lambda p: p.form or 0, reverse=True)
    else:
        position_players.sort(key=lambda p: p.expected_points or 0, reverse=True)
    
    return position_players[:limit]


def get_differential_picks(
    players: List[Player],
    max_ownership: float = 10.0,
    limit: int = 10
) -> List[Player]:
    """Get high-value players with low ownership (differentials)."""
    differentials = [
        p for p in players 
        if p.is_available and p.selected_by_percent <= max_ownership
    ]
    differentials.sort(key=lambda p: p.expected_points or 0, reverse=True)
    return differentials[:limit]


def get_captain_picks(players: List[Player], limit: int = 5) -> List[Player]:
    """Get best captain options."""
    available = [p for p in players if p.is_available]
    available.sort(key=lambda p: p.captain_score or 0, reverse=True)
    return available[:limit]


def get_value_picks(
    players: List[Player],
    max_price: float = 6.0,
    limit: int = 10
) -> List[Player]:
    """Get best budget-friendly players."""
    budget_players = [
        p for p in players 
        if p.is_available and p.price <= max_price
    ]
    budget_players.sort(key=lambda p: p.value_score or 0, reverse=True)
    return budget_players[:limit]


def generate_fpl_advice(fpl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive FPL advice including:
    - Optimal team suggestion
    - Top picks by position
    - Captain recommendations
    - Differential picks
    - Value picks
    """
    players = load_players_from_data(fpl_data)
    
    # Generate optimal team
    optimal_team = greedy_team_selection(players)
    
    # Get recommendations
    advice = {
        "generated_at": fpl_data.get("fetched_at"),
        "gameweek": fpl_data.get("next_gameweek") or fpl_data.get("current_gameweek"),
        "optimal_team": None,
        "top_goalkeepers": [],
        "top_defenders": [],
        "top_midfielders": [],
        "top_forwards": [],
        "captain_picks": [],
        "differential_picks": [],
        "value_picks": [],
    }
    
    if optimal_team:
        advice["optimal_team"] = {
            "players": [_player_to_dict(p) for p in optimal_team.players],
            "starting_xi": [_player_to_dict(p) for p in optimal_team.starting_xi],
            "bench": [_player_to_dict(p) for p in optimal_team.bench],
            "captain": _player_to_dict(optimal_team.captain),
            "vice_captain": _player_to_dict(optimal_team.vice_captain),
            "formation": optimal_team.formation,
            "total_cost": optimal_team.total_cost,
            "expected_points": optimal_team.expected_points,
            "budget_remaining": optimal_team.budget_remaining,
        }
    
    # Top picks by position
    advice["top_goalkeepers"] = [_player_to_dict(p) for p in get_top_picks_by_position(players, "GKP", 5)]
    advice["top_defenders"] = [_player_to_dict(p) for p in get_top_picks_by_position(players, "DEF", 10)]
    advice["top_midfielders"] = [_player_to_dict(p) for p in get_top_picks_by_position(players, "MID", 10)]
    advice["top_forwards"] = [_player_to_dict(p) for p in get_top_picks_by_position(players, "FWD", 10)]
    
    # Captain picks
    advice["captain_picks"] = [_player_to_dict(p) for p in get_captain_picks(players, 5)]
    
    # Differential picks
    advice["differential_picks"] = [_player_to_dict(p) for p in get_differential_picks(players, 10.0, 10)]
    
    # Value picks
    advice["value_picks"] = [_player_to_dict(p) for p in get_value_picks(players, 6.0, 10)]
    
    return advice


def _player_to_dict(player: Player) -> Dict[str, Any]:
    """Convert Player object to dictionary for JSON serialization."""
    return {
        "id": player.id,
        "web_name": player.web_name,
        "team_name": player.team_name,
        "position": player.position,
        "price": player.price,
        "total_points": player.total_points,
        "form": player.form,
        "points_per_game": player.points_per_game,
        "selected_by_percent": player.selected_by_percent,
        "fixture_difficulty_avg": player.fixture_difficulty_avg,
        "expected_points": player.expected_points,
        "value_score": player.value_score,
        "captain_score": player.captain_score,
        "status": player.status,
        "chance_of_playing": player.chance_of_playing,
        "news": player.news,
    }


def main():
    """Test the optimizer with latest FPL data."""
    from etl.fetch_fpl_data import FPL_PROCESSED_DIR
    
    latest_file = FPL_PROCESSED_DIR / "fpl_data_latest.json"
    
    if not latest_file.exists():
        logger.error("No FPL data found. Run fetch_fpl_data.py first.")
        return
    
    with open(latest_file, "r") as f:
        fpl_data = json.load(f)
    
    advice = generate_fpl_advice(fpl_data)
    
    # Print summary
    print("\n" + "=" * 60)
    print("FPL ADVISOR - TEAM SUGGESTION")
    print("=" * 60)
    
    if advice.get("optimal_team"):
        team = advice["optimal_team"]
        print(f"\nGameweek: {advice.get('gameweek')}")
        print(f"Formation: {team['formation']}")
        print(f"Total Cost: £{team['total_cost']}m")
        print(f"Expected Points: {team['expected_points']}")
        print(f"Budget Remaining: £{team['budget_remaining']}m")
        
        print(f"\nCaptain: {team['captain']['web_name']} ({team['captain']['expected_points']} xPts)")
        print(f"Vice Captain: {team['vice_captain']['web_name']}")
        
        print("\nStarting XI:")
        for p in team["starting_xi"]:
            print(f"  {p['position']:3} | {p['web_name']:15} | £{p['price']}m | {p['expected_points']} xPts")
        
        print("\nBench:")
        for p in team["bench"]:
            print(f"  {p['position']:3} | {p['web_name']:15} | £{p['price']}m | {p['expected_points']} xPts")
    
    print("\n" + "=" * 60)
    print("TOP CAPTAIN PICKS")
    print("=" * 60)
    for p in advice.get("captain_picks", []):
        print(f"  {p['web_name']:15} | {p['team_name']:15} | Captain Score: {p['captain_score']}")
    
    print("\n" + "=" * 60)
    print("DIFFERENTIAL PICKS (<10% ownership)")
    print("=" * 60)
    for p in advice.get("differential_picks", [])[:5]:
        print(f"  {p['web_name']:15} | {p['team_name']:15} | {p['selected_by_percent']}% owned | {p['expected_points']} xPts")


if __name__ == "__main__":
    main()
