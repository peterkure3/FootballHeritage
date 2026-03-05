"""
Improved True Probability Calculator

Combines multiple methods to estimate true probabilities:
1. Sharp bookmaker devigging (Pinnacle, Betfair)
2. Consensus odds from multiple bookmakers
3. Elo model predictions
4. Power method devigging
5. Shin method for detecting favorite-longshot bias

The final probability is a weighted ensemble of these methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
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
from etl.elo_model import EloModel

logger = setup_logger(__name__, LOG_LEVEL)


# Sharp bookmakers (lower vig, more accurate lines)
SHARP_BOOKS = ["pinnacle", "betfair", "betfair_exchange", "matchbook"]

# Soft bookmakers (higher vig, exploitable)
SOFT_BOOKS = ["draftkings", "fanduel", "betmgm", "caesars", "pointsbet"]

# Method weights for ensemble
METHOD_WEIGHTS = {
    "sharp_devig": 0.40,      # Sharp book devigged odds
    "consensus": 0.25,        # Average across all books
    "elo_model": 0.20,        # Our Elo predictions
    "power_method": 0.10,     # Power devigging
    "shin_method": 0.05,      # Shin method for bias correction
}


@dataclass
class TrueProbability:
    """True probability estimate with confidence."""
    selection: str
    probability: float
    confidence: float  # 0-1 scale
    method_contributions: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            "selection": self.selection,
            "probability": round(self.probability, 5),
            "confidence": round(self.confidence, 3),
            "method_contributions": {k: round(v, 5) for k, v in self.method_contributions.items()},
        }


def implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 1.0:
        return 1.0
    return 1.0 / decimal_odds


def devig_multiplicative(odds_list: List[float]) -> List[float]:
    """Standard multiplicative devigging (remove vig proportionally)."""
    implied = [implied_prob(o) for o in odds_list]
    total = sum(implied)
    if total <= 0:
        return implied
    return [p / total for p in implied]


def devig_power_method(odds_list: List[float], iterations: int = 100) -> List[float]:
    """
    Power method devigging.
    
    Finds the power k such that sum(p_i^k) = 1, where p_i are implied probs.
    This method better handles favorite-longshot bias.
    """
    implied = [implied_prob(o) for o in odds_list]
    
    # Binary search for k
    k_low, k_high = 0.5, 2.0
    
    for _ in range(iterations):
        k_mid = (k_low + k_high) / 2
        total = sum(p ** k_mid for p in implied)
        
        if abs(total - 1.0) < 1e-10:
            break
        elif total > 1.0:
            k_low = k_mid
        else:
            k_high = k_mid
    
    k = (k_low + k_high) / 2
    fair_probs = [p ** k for p in implied]
    
    # Normalize to ensure sum = 1
    total = sum(fair_probs)
    return [p / total for p in fair_probs] if total > 0 else implied


def devig_shin_method(odds_list: List[float], iterations: int = 100) -> List[float]:
    """
    Shin method devigging.
    
    Accounts for the presence of informed bettors in the market.
    Better for markets with potential insider information.
    """
    implied = [implied_prob(o) for o in odds_list]
    n = len(implied)
    
    if n != 2:
        # Shin method works best for 2-way markets
        return devig_multiplicative(odds_list)
    
    # Binary search for z (proportion of informed bettors)
    z_low, z_high = 0.0, 0.5
    
    for _ in range(iterations):
        z = (z_low + z_high) / 2
        
        # Calculate fair probabilities given z
        fair_probs = []
        for p in implied:
            numerator = math.sqrt(z ** 2 + 4 * (1 - z) * p ** 2 / sum(implied)) - z
            denominator = 2 * (1 - z)
            if denominator > 0:
                fair_probs.append(numerator / denominator)
            else:
                fair_probs.append(p)
        
        total = sum(fair_probs)
        
        if abs(total - 1.0) < 1e-10:
            break
        elif total > 1.0:
            z_low = z
        else:
            z_high = z
    
    # Final calculation with found z
    z = (z_low + z_high) / 2
    fair_probs = []
    for p in implied:
        numerator = math.sqrt(z ** 2 + 4 * (1 - z) * p ** 2 / sum(implied)) - z
        denominator = 2 * (1 - z)
        if denominator > 0:
            fair_probs.append(numerator / denominator)
        else:
            fair_probs.append(p)
    
    total = sum(fair_probs)
    return [p / total for p in fair_probs] if total > 0 else implied


class TrueProbabilityCalculator:
    """Calculates true probabilities using ensemble of methods."""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or create_engine(HERITAGE_DATABASE_URI)
        self.elo_model: Optional[EloModel] = None
    
    def _get_elo_model(self) -> EloModel:
        """Lazy load Elo model."""
        if self.elo_model is None:
            self.elo_model = EloModel(self.engine)
            self.elo_model.load_ratings_from_db()
            if not self.elo_model.ratings:
                self.elo_model.load_historical_results()
        return self.elo_model
    
    def calculate_two_way(
        self,
        event_id: str,
        market: str,
        selection_a: str,
        selection_b: str,
        odds_by_book: Dict[str, Tuple[float, float]],  # book -> (odds_a, odds_b)
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        league: Optional[str] = None,
        exclude_book: Optional[str] = None,  # Exclude this book from baseline calculation
    ) -> Tuple[TrueProbability, TrueProbability]:
        """
        Calculate true probabilities for a two-way market.
        
        Returns probabilities for selection_a and selection_b.
        If exclude_book is provided, that book is excluded from the baseline calculation
        (used when comparing a specific book against the market).
        """
        method_probs_a: Dict[str, float] = {}
        method_probs_b: Dict[str, float] = {}
        method_confidences: Dict[str, float] = {}
        
        # Filter out excluded book for baseline calculation
        baseline_odds = {k: v for k, v in odds_by_book.items() if k != exclude_book}
        if not baseline_odds:
            baseline_odds = odds_by_book  # Fallback if only one book
        
        # 1. Sharp book devigging (prefer Pinnacle/Betfair)
        sharp_odds = [(book, odds) for book, odds in baseline_odds.items() if book.lower() in SHARP_BOOKS]
        if sharp_odds:
            # Use the sharpest available book
            book, (odds_a, odds_b) = sharp_odds[0]
            probs = devig_multiplicative([odds_a, odds_b])
            method_probs_a["sharp_devig"] = probs[0]
            method_probs_b["sharp_devig"] = probs[1]
            method_confidences["sharp_devig"] = 0.95  # High confidence in sharp books
        
        # 2. Consensus across all books (excluding target book)
        if baseline_odds:
            all_probs_a = []
            all_probs_b = []
            for book, (odds_a, odds_b) in baseline_odds.items():
                probs = devig_multiplicative([odds_a, odds_b])
                all_probs_a.append(probs[0])
                all_probs_b.append(probs[1])
            
            method_probs_a["consensus"] = sum(all_probs_a) / len(all_probs_a)
            method_probs_b["consensus"] = sum(all_probs_b) / len(all_probs_b)
            method_confidences["consensus"] = min(1.0, len(baseline_odds) / 5.0)  # More books = more confidence
        
        # 3. Elo model (for h2h markets only)
        if market == "h2h" and home_team and away_team:
            try:
                model = self._get_elo_model()
                pred = model.predict_match(home_team, away_team, league or "default")
                
                # Map selections to probabilities
                if selection_a.upper() == "HOME":
                    method_probs_a["elo_model"] = pred.home_win_prob
                    method_probs_b["elo_model"] = pred.away_win_prob
                elif selection_a.upper() == "AWAY":
                    method_probs_a["elo_model"] = pred.away_win_prob
                    method_probs_b["elo_model"] = pred.home_win_prob
                else:
                    # Try to match team names
                    if home_team.lower() in selection_a.lower():
                        method_probs_a["elo_model"] = pred.home_win_prob
                        method_probs_b["elo_model"] = pred.away_win_prob
                    else:
                        method_probs_a["elo_model"] = pred.away_win_prob
                        method_probs_b["elo_model"] = pred.home_win_prob
                
                method_confidences["elo_model"] = pred.confidence
            except Exception as e:
                logger.debug("Elo model failed for %s vs %s: %s", home_team, away_team, e)
        
        # 4. Power method devigging
        if odds_by_book:
            # Use average odds across books
            avg_odds_a = sum(o[0] for o in odds_by_book.values()) / len(odds_by_book)
            avg_odds_b = sum(o[1] for o in odds_by_book.values()) / len(odds_by_book)
            probs = devig_power_method([avg_odds_a, avg_odds_b])
            method_probs_a["power_method"] = probs[0]
            method_probs_b["power_method"] = probs[1]
            method_confidences["power_method"] = 0.7
        
        # 5. Shin method
        if odds_by_book:
            avg_odds_a = sum(o[0] for o in odds_by_book.values()) / len(odds_by_book)
            avg_odds_b = sum(o[1] for o in odds_by_book.values()) / len(odds_by_book)
            probs = devig_shin_method([avg_odds_a, avg_odds_b])
            method_probs_a["shin_method"] = probs[0]
            method_probs_b["shin_method"] = probs[1]
            method_confidences["shin_method"] = 0.6
        
        # Ensemble: weighted average
        final_prob_a = 0.0
        final_prob_b = 0.0
        total_weight = 0.0
        
        for method, weight in METHOD_WEIGHTS.items():
            if method in method_probs_a and method in method_probs_b:
                conf = method_confidences.get(method, 0.5)
                adj_weight = weight * conf
                final_prob_a += method_probs_a[method] * adj_weight
                final_prob_b += method_probs_b[method] * adj_weight
                total_weight += adj_weight
        
        if total_weight > 0:
            final_prob_a /= total_weight
            final_prob_b /= total_weight
        else:
            # Fallback to simple average
            if odds_by_book:
                avg_odds_a = sum(o[0] for o in odds_by_book.values()) / len(odds_by_book)
                avg_odds_b = sum(o[1] for o in odds_by_book.values()) / len(odds_by_book)
                probs = devig_multiplicative([avg_odds_a, avg_odds_b])
                final_prob_a, final_prob_b = probs[0], probs[1]
        
        # Normalize
        total = final_prob_a + final_prob_b
        if total > 0:
            final_prob_a /= total
            final_prob_b /= total
        
        # Calculate overall confidence
        overall_confidence = sum(method_confidences.values()) / len(method_confidences) if method_confidences else 0.5
        
        return (
            TrueProbability(
                selection=selection_a,
                probability=final_prob_a,
                confidence=overall_confidence,
                method_contributions=method_probs_a,
            ),
            TrueProbability(
                selection=selection_b,
                probability=final_prob_b,
                confidence=overall_confidence,
                method_contributions=method_probs_b,
            ),
        )
    
    def calculate_ev(
        self,
        true_prob: float,
        decimal_odds: float,
        stake: float = 100.0,
    ) -> Tuple[float, float]:
        """Calculate expected value and EV percentage."""
        win_profit = stake * (decimal_odds - 1.0)
        ev = (true_prob * win_profit) - ((1.0 - true_prob) * stake)
        ev_pct = ev / stake
        return ev, ev_pct
    
    def find_value_bets(
        self,
        min_ev_pct: float = 0.02,
        min_confidence: float = 0.6,
        limit: int = 100,
    ) -> List[Dict]:
        """Find value bets using improved true probability calculation."""
        value_bets = []
        
        with self.engine.connect() as conn:
            # Get odds grouped by event and market
            rows = conn.execute(text("""
                SELECT 
                    oo.event_id,
                    oo.provider_event_id,
                    e.home_team,
                    e.away_team,
                    e.league,
                    oo.market,
                    oo.selection,
                    oo.line,
                    oo.book_key,
                    oo.odds_decimal
                FROM odds_offers oo
                LEFT JOIN events e ON e.id = oo.event_id
                WHERE oo.event_id IS NOT NULL
                  AND oo.market IN ('h2h', 'spreads', 'totals')
                  AND oo.odds_decimal > 1.0
                ORDER BY oo.event_id, oo.market, oo.line
            """)).fetchall()
            
            # Group by (event_id, market, line)
            groups: Dict[Tuple, Dict[str, List]] = {}
            event_info: Dict[str, Dict] = {}
            
            logger.info("Loaded %d odds offers for value bet analysis", len(rows))
            
            for row in rows:
                event_id = str(row[0])
                key = (event_id, row[5], row[7])  # event_id, market, line
                
                if key not in groups:
                    groups[key] = {}
                
                selection = row[6]
                book = row[8]
                odds = float(row[9])
                
                if selection not in groups[key]:
                    groups[key][selection] = {}
                groups[key][selection][book] = odds
                
                if event_id not in event_info:
                    event_info[event_id] = {
                        "provider_event_id": row[1],
                        "home_team": row[2],
                        "away_team": row[3],
                        "league": row[4],
                    }
            
            logger.info("Grouped into %d market groups", len(groups))
            
            # Process each market
            two_way_count = 0
            for (event_id, market, line), selections in groups.items():
                if len(selections) != 2:
                    continue  # Only handle 2-way markets for now
                two_way_count += 1
                
                sel_names = sorted(selections.keys())
                sel_a, sel_b = sel_names[0], sel_names[1]
                
                # Build odds_by_book
                odds_by_book = {}
                for book in set(selections[sel_a].keys()) & set(selections[sel_b].keys()):
                    odds_by_book[book] = (selections[sel_a][book], selections[sel_b][book])
                
                if not odds_by_book:
                    continue
                
                info = event_info.get(event_id, {})
                
                # Check each book for value - calculate baseline excluding that book
                for book, (odds_a, odds_b) in odds_by_book.items():
                    # Skip sharp books - we want to find value at soft books
                    if book.lower() in SHARP_BOOKS:
                        continue
                    
                    # Calculate true probabilities excluding this book from baseline
                    prob_a, prob_b = self.calculate_two_way(
                        event_id=event_id,
                        market=market,
                        selection_a=sel_a,
                        selection_b=sel_b,
                        odds_by_book=odds_by_book,
                        home_team=info.get("home_team"),
                        away_team=info.get("away_team"),
                        league=info.get("league"),
                        exclude_book=book,  # Exclude this book from baseline
                    )
                    
                    if prob_a.confidence < min_confidence:
                        continue
                    
                    # Check selection A
                    ev_a, ev_pct_a = self.calculate_ev(prob_a.probability, odds_a)
                    if ev_pct_a >= min_ev_pct:
                        value_bets.append({
                            "event_id": event_id,
                            "pipeline_match_id": info.get("provider_event_id"),
                            "home_team": info.get("home_team"),
                            "away_team": info.get("away_team"),
                            "league": info.get("league"),
                            "market": market,
                            "line": line,
                            "selection": sel_a,
                            "bookmaker": book,
                            "odds": odds_a,
                            "true_probability": prob_a.probability,
                            "confidence": prob_a.confidence,
                            "expected_value": ev_a,
                            "expected_value_pct": ev_pct_a,
                            "method_contributions": prob_a.method_contributions,
                        })
                    
                    # Check selection B
                    ev_b, ev_pct_b = self.calculate_ev(prob_b.probability, odds_b)
                    if ev_pct_b >= min_ev_pct:
                        value_bets.append({
                            "event_id": event_id,
                            "pipeline_match_id": info.get("provider_event_id"),
                            "home_team": info.get("home_team"),
                            "away_team": info.get("away_team"),
                            "league": info.get("league"),
                            "market": market,
                            "line": line,
                            "selection": sel_b,
                            "bookmaker": book,
                            "odds": odds_b,
                            "true_probability": prob_b.probability,
                            "confidence": prob_b.confidence,
                            "expected_value": ev_b,
                            "expected_value_pct": ev_pct_b,
                            "method_contributions": prob_b.method_contributions,
                        })
        
        logger.info("Analyzed %d two-way markets, found %d value bets", two_way_count, len(value_bets))
        
        # Sort by EV% descending
        value_bets.sort(key=lambda x: -x["expected_value_pct"])
        
        return value_bets[:limit]


def main():
    """Find and display value bets."""
    import json
    
    calculator = TrueProbabilityCalculator()
    
    logger.info("Finding value bets with improved probability calculation...")
    
    # First check with 0% threshold to see what's available
    all_bets = calculator.find_value_bets(min_ev_pct=0.0, min_confidence=0.0, limit=500)
    logger.info("Total bets at 0%% threshold: %d", len(all_bets))
    
    if all_bets:
        ev_pcts = [b["expected_value_pct"] for b in all_bets]
        logger.info("EV range: min=%.2f%%, max=%.2f%%, avg=%.2f%%", 
                   min(ev_pcts)*100, max(ev_pcts)*100, sum(ev_pcts)/len(ev_pcts)*100)
    
    value_bets = calculator.find_value_bets(min_ev_pct=0.02, min_confidence=0.5)
    
    print(f"=== Found {len(value_bets)} Value Bets ===")
    for bet in value_bets[:10]:
        print(f"\n{bet['home_team']} vs {bet['away_team']} ({bet['league']})")
        print(f"  Market: {bet['market']}, Selection: {bet['selection']}")
        print(f"  Book: {bet['bookmaker']}, Odds: {bet['odds']:.2f}")
        print(f"  True Prob: {bet['true_probability']:.1%}, EV: {bet['expected_value_pct']:.1%}")
        print(f"  Confidence: {bet['confidence']:.1%}")


if __name__ == "__main__":
    main()
