"""
Enhanced Elo Rating Model with Form Adjustments

Features:
- Base Elo ratings with configurable K-factor
- Form adjustments based on recent results (last 5 games)
- Home advantage modeling
- League-specific parameters
- Goal difference margin adjustments
- Head-to-head history weighting
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


# League-specific parameters
LEAGUE_PARAMS = {
    "Premier League": {"k_factor": 32, "home_advantage": 65, "draw_factor": 0.26},
    "La Liga": {"k_factor": 30, "home_advantage": 70, "draw_factor": 0.28},
    "Bundesliga": {"k_factor": 32, "home_advantage": 55, "draw_factor": 0.24},
    "Serie A": {"k_factor": 28, "home_advantage": 60, "draw_factor": 0.27},
    "Ligue 1": {"k_factor": 30, "home_advantage": 60, "draw_factor": 0.26},
    "UEFA Champions League": {"k_factor": 40, "home_advantage": 50, "draw_factor": 0.22},
    "NFL": {"k_factor": 20, "home_advantage": 48, "draw_factor": 0.01},
    "NBA": {"k_factor": 20, "home_advantage": 60, "draw_factor": 0.0},
    "default": {"k_factor": 32, "home_advantage": 60, "draw_factor": 0.25},
}

DEFAULT_ELO = 1500.0
FORM_WINDOW = 5  # Last N games for form calculation
FORM_WEIGHT = 0.15  # How much form affects probability


@dataclass
class TeamRating:
    """Team's Elo rating with metadata."""
    team_name: str
    elo: float = DEFAULT_ELO
    form_score: float = 0.0  # -1 to +1 scale
    games_played: int = 0
    last_updated: Optional[datetime] = None
    recent_results: List[str] = field(default_factory=list)  # W/D/L
    
    def add_result(self, result: str, goals_for: int = 0, goals_against: int = 0):
        """Add a match result and update form."""
        self.recent_results.append(result)
        if len(self.recent_results) > FORM_WINDOW:
            self.recent_results = self.recent_results[-FORM_WINDOW:]
        self.games_played += 1
        self._update_form_score()
    
    def _update_form_score(self):
        """Calculate form score from recent results."""
        if not self.recent_results:
            self.form_score = 0.0
            return
        
        # Weight recent games more heavily
        weights = [1.0, 0.9, 0.8, 0.7, 0.6][:len(self.recent_results)]
        weights.reverse()  # Most recent = highest weight
        
        total_weight = sum(weights)
        score = 0.0
        
        for i, result in enumerate(self.recent_results):
            if result == "W":
                score += weights[i] * 1.0
            elif result == "D":
                score += weights[i] * 0.0
            else:  # L
                score += weights[i] * -1.0
        
        self.form_score = score / total_weight if total_weight > 0 else 0.0


@dataclass
class MatchPrediction:
    """Prediction for a single match."""
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    home_form: float
    away_form: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence: float  # 0-1 scale based on data quality
    
    def to_dict(self) -> Dict:
        return {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_elo": round(self.home_elo, 1),
            "away_elo": round(self.away_elo, 1),
            "home_form": round(self.home_form, 3),
            "away_form": round(self.away_form, 3),
            "home_win_prob": round(self.home_win_prob, 4),
            "draw_prob": round(self.draw_prob, 4),
            "away_win_prob": round(self.away_win_prob, 4),
            "confidence": round(self.confidence, 3),
        }


class EloModel:
    """Enhanced Elo rating model with form adjustments."""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or create_engine(HERITAGE_DATABASE_URI)
        self.ratings: Dict[str, TeamRating] = {}
        self.h2h_cache: Dict[Tuple[str, str], List[Dict]] = {}
    
    def get_league_params(self, league: str) -> Dict:
        """Get league-specific parameters."""
        return LEAGUE_PARAMS.get(league, LEAGUE_PARAMS["default"])
    
    def get_or_create_rating(self, team_name: str) -> TeamRating:
        """Get existing rating or create new one."""
        if team_name not in self.ratings:
            self.ratings[team_name] = TeamRating(team_name=team_name)
        return self.ratings[team_name]
    
    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score using Elo formula."""
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))
    
    def update_ratings(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        league: str = "default",
    ) -> Tuple[float, float]:
        """Update Elo ratings after a match."""
        params = self.get_league_params(league)
        k = params["k_factor"]
        home_adv = params["home_advantage"]
        
        home_rating = self.get_or_create_rating(home_team)
        away_rating = self.get_or_create_rating(away_team)
        
        # Adjust for home advantage
        home_elo_adj = home_rating.elo + home_adv
        away_elo_adj = away_rating.elo
        
        # Calculate expected scores
        home_expected = self.expected_score(home_elo_adj, away_elo_adj)
        away_expected = 1.0 - home_expected
        
        # Determine actual scores
        if home_goals > away_goals:
            home_actual = 1.0
            away_actual = 0.0
            home_result = "W"
            away_result = "L"
        elif home_goals < away_goals:
            home_actual = 0.0
            away_actual = 1.0
            home_result = "L"
            away_result = "W"
        else:
            home_actual = 0.5
            away_actual = 0.5
            home_result = "D"
            away_result = "D"
        
        # Goal difference multiplier (margin of victory matters)
        goal_diff = abs(home_goals - away_goals)
        margin_multiplier = 1.0 + (goal_diff - 1) * 0.1 if goal_diff > 1 else 1.0
        margin_multiplier = min(margin_multiplier, 1.5)  # Cap at 1.5x
        
        # Update Elo ratings
        k_adj = k * margin_multiplier
        home_rating.elo += k_adj * (home_actual - home_expected)
        away_rating.elo += k_adj * (away_actual - away_expected)
        
        # Update form
        home_rating.add_result(home_result, home_goals, away_goals)
        away_rating.add_result(away_result, away_goals, home_goals)
        home_rating.last_updated = datetime.utcnow()
        away_rating.last_updated = datetime.utcnow()
        
        return home_rating.elo, away_rating.elo
    
    def predict_match(
        self,
        home_team: str,
        away_team: str,
        league: str = "default",
    ) -> MatchPrediction:
        """Predict match outcome probabilities."""
        params = self.get_league_params(league)
        home_adv = params["home_advantage"]
        draw_factor = params["draw_factor"]
        
        home_rating = self.get_or_create_rating(home_team)
        away_rating = self.get_or_create_rating(away_team)
        
        # Base Elo probability
        home_elo_adj = home_rating.elo + home_adv
        base_home_prob = self.expected_score(home_elo_adj, away_rating.elo)
        
        # Form adjustment
        form_diff = home_rating.form_score - away_rating.form_score
        form_adjustment = form_diff * FORM_WEIGHT
        
        # Adjusted home win probability (before draw allocation)
        adj_home_prob = base_home_prob + form_adjustment
        adj_home_prob = max(0.05, min(0.95, adj_home_prob))  # Clamp
        
        # Allocate draw probability
        # Draw is more likely when teams are evenly matched
        elo_diff = abs(home_elo_adj - away_rating.elo)
        draw_base = draw_factor * (1.0 - elo_diff / 600.0)
        draw_prob = max(0.05, min(0.35, draw_base))
        
        # Distribute remaining probability
        remaining = 1.0 - draw_prob
        home_win_prob = adj_home_prob * remaining
        away_win_prob = (1.0 - adj_home_prob) * remaining
        
        # Normalize to ensure sum = 1
        total = home_win_prob + draw_prob + away_win_prob
        home_win_prob /= total
        draw_prob /= total
        away_win_prob /= total
        
        # Calculate confidence based on data quality
        min_games = min(home_rating.games_played, away_rating.games_played)
        confidence = min(1.0, min_games / 10.0)  # Full confidence after 10 games each
        
        return MatchPrediction(
            home_team=home_team,
            away_team=away_team,
            home_elo=home_rating.elo,
            away_elo=away_rating.elo,
            home_form=home_rating.form_score,
            away_form=away_rating.form_score,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            confidence=confidence,
        )
    
    def load_historical_results(self, league: Optional[str] = None, days_back: int = 365):
        """Load historical match results to build ratings."""
        with self.engine.connect() as conn:
            query = """
                SELECT 
                    home_team, away_team, home_score, away_score, 
                    event_date, league
                FROM events
                WHERE home_score IS NOT NULL 
                  AND away_score IS NOT NULL
                  AND event_date >= NOW() - INTERVAL '1 day' * :days_back
            """
            params = {"days_back": days_back}
            
            if league:
                query += " AND league = :league"
                params["league"] = league
            
            query += " ORDER BY event_date ASC"
            
            results = conn.execute(text(query), params).fetchall()
            
            logger.info("Loading %d historical results for Elo calculation", len(results))
            
            for row in results:
                home_team = row[0]
                away_team = row[1]
                home_score = row[2]
                away_score = row[3]
                match_league = row[5] or "default"
                
                if home_team and away_team and home_score is not None and away_score is not None:
                    self.update_ratings(
                        home_team=home_team,
                        away_team=away_team,
                        home_goals=int(home_score),
                        away_goals=int(away_score),
                        league=match_league,
                    )
            
            logger.info("Loaded ratings for %d teams", len(self.ratings))
    
    def get_all_ratings(self) -> List[Dict]:
        """Get all team ratings sorted by Elo."""
        ratings = []
        for team, rating in sorted(self.ratings.items(), key=lambda x: -x[1].elo):
            ratings.append({
                "team": team,
                "elo": round(rating.elo, 1),
                "form": round(rating.form_score, 3),
                "games_played": rating.games_played,
                "recent_form": "".join(rating.recent_results[-5:]),
            })
        return ratings
    
    def save_ratings_to_db(self):
        """Save current ratings to database."""
        with self.engine.begin() as conn:
            # Create table if not exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS team_elo_ratings (
                    id SERIAL PRIMARY KEY,
                    team_name VARCHAR(255) UNIQUE NOT NULL,
                    elo FLOAT NOT NULL,
                    form_score FLOAT DEFAULT 0,
                    games_played INT DEFAULT 0,
                    recent_results VARCHAR(10),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            for team, rating in self.ratings.items():
                conn.execute(text("""
                    INSERT INTO team_elo_ratings (team_name, elo, form_score, games_played, recent_results, updated_at)
                    VALUES (:team, :elo, :form, :games, :recent, NOW())
                    ON CONFLICT (team_name) DO UPDATE SET
                        elo = :elo,
                        form_score = :form,
                        games_played = :games,
                        recent_results = :recent,
                        updated_at = NOW()
                """), {
                    "team": team,
                    "elo": rating.elo,
                    "form": rating.form_score,
                    "games": rating.games_played,
                    "recent": "".join(rating.recent_results[-5:]),
                })
            
            logger.info("Saved %d team ratings to database", len(self.ratings))
    
    def load_ratings_from_db(self):
        """Load ratings from database."""
        with self.engine.connect() as conn:
            try:
                results = conn.execute(text("""
                    SELECT team_name, elo, form_score, games_played, recent_results
                    FROM team_elo_ratings
                """)).fetchall()
                
                for row in results:
                    rating = TeamRating(
                        team_name=row[0],
                        elo=row[1],
                        form_score=row[2] or 0.0,
                        games_played=row[3] or 0,
                        recent_results=list(row[4]) if row[4] else [],
                    )
                    self.ratings[row[0]] = rating
                
                logger.info("Loaded %d team ratings from database", len(self.ratings))
            except Exception as e:
                logger.warning("Could not load ratings from DB: %s", e)


def compute_elo_ratings(league: Optional[str] = None, save: bool = True) -> Dict:
    """Compute Elo ratings from historical data."""
    model = EloModel()
    model.load_historical_results(league=league)
    
    if save:
        model.save_ratings_to_db()
    
    return {
        "teams_rated": len(model.ratings),
        "top_10": model.get_all_ratings()[:10],
    }


def predict_upcoming_matches(league: Optional[str] = None) -> List[Dict]:
    """Predict outcomes for upcoming matches."""
    model = EloModel()
    model.load_ratings_from_db()
    
    # If no saved ratings, compute from scratch
    if not model.ratings:
        model.load_historical_results(league=league)
    
    predictions = []
    
    with model.engine.connect() as conn:
        query = """
            SELECT home_team, away_team, event_date, league
            FROM events
            WHERE event_date > NOW()
              AND home_score IS NULL
        """
        params = {}
        
        if league:
            query += " AND league = :league"
            params["league"] = league
        
        query += " ORDER BY event_date ASC LIMIT 50"
        
        results = conn.execute(text(query), params).fetchall()
        
        for row in results:
            home_team = row[0]
            away_team = row[1]
            event_date = row[2]
            match_league = row[3] or "default"
            
            if home_team and away_team:
                pred = model.predict_match(home_team, away_team, match_league)
                pred_dict = pred.to_dict()
                pred_dict["event_date"] = event_date.isoformat() if event_date else None
                pred_dict["league"] = match_league
                predictions.append(pred_dict)
    
    return predictions


def main():
    """Compute ratings and show predictions."""
    import json
    
    logger.info("Computing Elo ratings...")
    result = compute_elo_ratings()
    print("=== Top 10 Teams by Elo ===")
    print(json.dumps(result["top_10"], indent=2))
    
    logger.info("Predicting upcoming matches...")
    predictions = predict_upcoming_matches()
    print("\n=== Upcoming Match Predictions ===")
    print(json.dumps(predictions[:10], indent=2))


if __name__ == "__main__":
    main()
