"""
Backtesting Framework for Prediction Accuracy Validation

Evaluates prediction models using historical data with metrics:
- Brier Score: Measures probability calibration
- Log Loss: Penalizes confident wrong predictions
- ROI: Return on investment for betting strategies
- Calibration curves: Visual check of probability accuracy
- Top-N accuracy: How often top picks are correct
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
from etl.elo_model import EloModel
from etl.true_probability import TrueProbabilityCalculator

logger = setup_logger(__name__, LOG_LEVEL)


@dataclass
class PredictionRecord:
    """A single prediction with outcome."""
    event_id: str
    home_team: str
    away_team: str
    event_date: datetime
    league: str
    predicted_home_prob: float
    predicted_draw_prob: float
    predicted_away_prob: float
    actual_result: str  # "H", "D", "A"
    home_score: int
    away_score: int
    confidence: float = 1.0


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    model_name: str
    start_date: datetime
    end_date: datetime
    total_predictions: int
    
    # Accuracy metrics
    brier_score: float
    log_loss: float
    accuracy: float  # % of correct favorite picks
    
    # Calibration
    calibration_buckets: Dict[str, Dict]
    
    # ROI simulation
    roi_flat_stake: float
    roi_kelly: float
    
    # By league breakdown
    by_league: Dict[str, Dict]
    
    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_predictions": self.total_predictions,
            "brier_score": round(self.brier_score, 5),
            "log_loss": round(self.log_loss, 5),
            "accuracy": round(self.accuracy, 4),
            "calibration_buckets": self.calibration_buckets,
            "roi_flat_stake": round(self.roi_flat_stake, 4),
            "roi_kelly": round(self.roi_kelly, 4),
            "by_league": self.by_league,
        }


class Backtester:
    """Backtests prediction models against historical data."""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or create_engine(HERITAGE_DATABASE_URI)
    
    def load_historical_matches(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        league: Optional[str] = None,
    ) -> List[Dict]:
        """Load completed matches with results."""
        with self.engine.connect() as conn:
            query = """
                SELECT 
                    id, home_team, away_team, home_score, away_score,
                    event_date, league
                FROM events
                WHERE home_score IS NOT NULL 
                  AND away_score IS NOT NULL
            """
            params = {}
            
            if start_date:
                query += " AND event_date >= :start_date::timestamp"
                params["start_date"] = start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date)
            
            if end_date:
                query += " AND event_date <= :end_date::timestamp"
                params["end_date"] = end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            
            if league:
                query += " AND league = :league"
                params["league"] = league
            
            query += " ORDER BY event_date ASC"
            
            results = conn.execute(text(query), params).fetchall()
            
            matches = []
            for row in results:
                home_score = int(row[3])
                away_score = int(row[4])
                
                if home_score > away_score:
                    result = "H"
                elif home_score < away_score:
                    result = "A"
                else:
                    result = "D"
                
                matches.append({
                    "event_id": str(row[0]),
                    "home_team": row[1],
                    "away_team": row[2],
                    "home_score": home_score,
                    "away_score": away_score,
                    "event_date": row[5],
                    "league": row[6],
                    "result": result,
                })
            
            return matches
    
    def calculate_brier_score(self, predictions: List[PredictionRecord]) -> float:
        """
        Calculate Brier score (lower is better).
        
        Brier = (1/N) * sum((predicted_prob - actual)^2)
        """
        if not predictions:
            return 1.0
        
        total = 0.0
        for pred in predictions:
            if pred.actual_result == "H":
                actual = [1, 0, 0]
            elif pred.actual_result == "D":
                actual = [0, 1, 0]
            else:
                actual = [0, 0, 1]
            
            predicted = [pred.predicted_home_prob, pred.predicted_draw_prob, pred.predicted_away_prob]
            
            for p, a in zip(predicted, actual):
                total += (p - a) ** 2
        
        return total / (len(predictions) * 3)
    
    def calculate_log_loss(self, predictions: List[PredictionRecord]) -> float:
        """
        Calculate log loss (lower is better).
        
        Penalizes confident wrong predictions heavily.
        """
        if not predictions:
            return float('inf')
        
        epsilon = 1e-15  # Avoid log(0)
        total = 0.0
        
        for pred in predictions:
            if pred.actual_result == "H":
                prob = max(epsilon, min(1 - epsilon, pred.predicted_home_prob))
            elif pred.actual_result == "D":
                prob = max(epsilon, min(1 - epsilon, pred.predicted_draw_prob))
            else:
                prob = max(epsilon, min(1 - epsilon, pred.predicted_away_prob))
            
            total -= math.log(prob)
        
        return total / len(predictions)
    
    def calculate_accuracy(self, predictions: List[PredictionRecord]) -> float:
        """Calculate % of times the favorite (highest prob) won."""
        if not predictions:
            return 0.0
        
        correct = 0
        for pred in predictions:
            probs = {
                "H": pred.predicted_home_prob,
                "D": pred.predicted_draw_prob,
                "A": pred.predicted_away_prob,
            }
            favorite = max(probs, key=probs.get)
            if favorite == pred.actual_result:
                correct += 1
        
        return correct / len(predictions)
    
    def calculate_calibration(self, predictions: List[PredictionRecord]) -> Dict[str, Dict]:
        """
        Calculate calibration buckets.
        
        Groups predictions by probability range and checks actual win rate.
        Perfect calibration: 70% predictions should win ~70% of the time.
        """
        buckets = {
            "0-10%": {"count": 0, "wins": 0},
            "10-20%": {"count": 0, "wins": 0},
            "20-30%": {"count": 0, "wins": 0},
            "30-40%": {"count": 0, "wins": 0},
            "40-50%": {"count": 0, "wins": 0},
            "50-60%": {"count": 0, "wins": 0},
            "60-70%": {"count": 0, "wins": 0},
            "70-80%": {"count": 0, "wins": 0},
            "80-90%": {"count": 0, "wins": 0},
            "90-100%": {"count": 0, "wins": 0},
        }
        
        def get_bucket(prob: float) -> str:
            if prob < 0.1:
                return "0-10%"
            elif prob < 0.2:
                return "10-20%"
            elif prob < 0.3:
                return "20-30%"
            elif prob < 0.4:
                return "30-40%"
            elif prob < 0.5:
                return "40-50%"
            elif prob < 0.6:
                return "50-60%"
            elif prob < 0.7:
                return "60-70%"
            elif prob < 0.8:
                return "70-80%"
            elif prob < 0.9:
                return "80-90%"
            else:
                return "90-100%"
        
        for pred in predictions:
            # Check each outcome
            for outcome, prob in [
                ("H", pred.predicted_home_prob),
                ("D", pred.predicted_draw_prob),
                ("A", pred.predicted_away_prob),
            ]:
                bucket = get_bucket(prob)
                buckets[bucket]["count"] += 1
                if pred.actual_result == outcome:
                    buckets[bucket]["wins"] += 1
        
        # Calculate actual win rates
        for bucket_name, data in buckets.items():
            if data["count"] > 0:
                data["actual_rate"] = round(data["wins"] / data["count"], 4)
                # Expected rate is midpoint of bucket
                expected = (int(bucket_name.split("-")[0].replace("%", "")) + 
                           int(bucket_name.split("-")[1].replace("%", ""))) / 200
                data["expected_rate"] = expected
                data["calibration_error"] = round(abs(data["actual_rate"] - expected), 4)
            else:
                data["actual_rate"] = None
                data["expected_rate"] = None
                data["calibration_error"] = None
        
        return buckets
    
    def simulate_betting_roi(
        self,
        predictions: List[PredictionRecord],
        odds_data: Dict[str, Dict[str, float]],  # event_id -> {H: odds, D: odds, A: odds}
        stake: float = 100.0,
    ) -> Tuple[float, float]:
        """
        Simulate betting ROI using flat stake and Kelly criterion.
        
        Returns (flat_stake_roi, kelly_roi)
        """
        flat_profit = 0.0
        flat_wagered = 0.0
        kelly_profit = 0.0
        kelly_wagered = 0.0
        bankroll = 10000.0  # Starting bankroll for Kelly
        
        for pred in predictions:
            event_odds = odds_data.get(pred.event_id, {})
            if not event_odds:
                continue
            
            # Find value bets (where our prob > implied prob)
            for outcome, our_prob in [
                ("H", pred.predicted_home_prob),
                ("D", pred.predicted_draw_prob),
                ("A", pred.predicted_away_prob),
            ]:
                odds = event_odds.get(outcome)
                if not odds or odds <= 1.0:
                    continue
                
                implied_prob = 1.0 / odds
                edge = our_prob - implied_prob
                
                if edge > 0.02:  # Only bet if 2%+ edge
                    # Flat stake
                    flat_wagered += stake
                    if pred.actual_result == outcome:
                        flat_profit += stake * (odds - 1)
                    else:
                        flat_profit -= stake
                    
                    # Kelly stake
                    kelly_fraction = edge / (odds - 1) if odds > 1 else 0
                    kelly_fraction = min(kelly_fraction, 0.1)  # Cap at 10% of bankroll
                    kelly_stake = bankroll * kelly_fraction
                    
                    kelly_wagered += kelly_stake
                    if pred.actual_result == outcome:
                        kelly_profit += kelly_stake * (odds - 1)
                        bankroll += kelly_stake * (odds - 1)
                    else:
                        kelly_profit -= kelly_stake
                        bankroll -= kelly_stake
        
        flat_roi = flat_profit / flat_wagered if flat_wagered > 0 else 0.0
        kelly_roi = kelly_profit / kelly_wagered if kelly_wagered > 0 else 0.0
        
        return flat_roi, kelly_roi
    
    def backtest_elo_model(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        league: Optional[str] = None,
        train_days: int = 180,
    ) -> BacktestResult:
        """
        Backtest the Elo model.
        
        Uses walk-forward validation: train on past data, predict next match.
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.utcnow()
        
        matches = self.load_historical_matches(start_date, end_date, league)
        
        if not matches:
            logger.warning("No matches found for backtesting")
            return BacktestResult(
                model_name="elo_model",
                start_date=start_date,
                end_date=end_date,
                total_predictions=0,
                brier_score=1.0,
                log_loss=float('inf'),
                accuracy=0.0,
                calibration_buckets={},
                roi_flat_stake=0.0,
                roi_kelly=0.0,
                by_league={},
            )
        
        logger.info("Backtesting Elo model on %d matches", len(matches))
        
        # Initialize model and train on first portion
        model = EloModel(self.engine)
        predictions: List[PredictionRecord] = []
        by_league: Dict[str, List[PredictionRecord]] = {}
        
        # Walk-forward: for each match, predict then update
        for i, match in enumerate(matches):
            home_team = match["home_team"]
            away_team = match["away_team"]
            match_league = match["league"] or "default"
            
            if not home_team or not away_team:
                continue
            
            # Make prediction before seeing result
            pred = model.predict_match(home_team, away_team, match_league)
            
            # Record prediction
            record = PredictionRecord(
                event_id=match["event_id"],
                home_team=home_team,
                away_team=away_team,
                event_date=match["event_date"],
                league=match_league,
                predicted_home_prob=pred.home_win_prob,
                predicted_draw_prob=pred.draw_prob,
                predicted_away_prob=pred.away_win_prob,
                actual_result=match["result"],
                home_score=match["home_score"],
                away_score=match["away_score"],
                confidence=pred.confidence,
            )
            predictions.append(record)
            
            if match_league not in by_league:
                by_league[match_league] = []
            by_league[match_league].append(record)
            
            # Update model with actual result
            model.update_ratings(
                home_team=home_team,
                away_team=away_team,
                home_goals=match["home_score"],
                away_goals=match["away_score"],
                league=match_league,
            )
        
        # Calculate metrics
        brier = self.calculate_brier_score(predictions)
        log_loss = self.calculate_log_loss(predictions)
        accuracy = self.calculate_accuracy(predictions)
        calibration = self.calculate_calibration(predictions)
        
        # ROI simulation (would need odds data)
        roi_flat, roi_kelly = 0.0, 0.0
        
        # By-league breakdown
        league_results = {}
        for lg, lg_preds in by_league.items():
            league_results[lg] = {
                "count": len(lg_preds),
                "brier_score": round(self.calculate_brier_score(lg_preds), 5),
                "accuracy": round(self.calculate_accuracy(lg_preds), 4),
            }
        
        return BacktestResult(
            model_name="elo_model",
            start_date=start_date,
            end_date=end_date,
            total_predictions=len(predictions),
            brier_score=brier,
            log_loss=log_loss,
            accuracy=accuracy,
            calibration_buckets=calibration,
            roi_flat_stake=roi_flat,
            roi_kelly=roi_kelly,
            by_league=league_results,
        )
    
    def save_backtest_results(self, result: BacktestResult):
        """Save backtest results to database."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(100) NOT NULL,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    total_predictions INT,
                    brier_score FLOAT,
                    log_loss FLOAT,
                    accuracy FLOAT,
                    roi_flat_stake FLOAT,
                    roi_kelly FLOAT,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            import json
            conn.execute(text("""
                INSERT INTO backtest_results (
                    model_name, start_date, end_date, total_predictions,
                    brier_score, log_loss, accuracy, roi_flat_stake, roi_kelly, details
                ) VALUES (
                    :model_name, :start_date, :end_date, :total_predictions,
                    :brier_score, :log_loss, :accuracy, :roi_flat_stake, :roi_kelly, :details
                )
            """), {
                "model_name": result.model_name,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "total_predictions": result.total_predictions,
                "brier_score": result.brier_score,
                "log_loss": result.log_loss,
                "accuracy": result.accuracy,
                "roi_flat_stake": result.roi_flat_stake,
                "roi_kelly": result.roi_kelly,
                "details": json.dumps({
                    "calibration": result.calibration_buckets,
                    "by_league": result.by_league,
                }),
            })
            
            logger.info("Saved backtest results for %s", result.model_name)


def run_backtest(
    model: str = "elo",
    days_back: int = 365,
    league: Optional[str] = None,
    save: bool = True,
) -> BacktestResult:
    """Run a backtest and optionally save results."""
    backtester = Backtester()
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    end_date = datetime.utcnow()
    
    if model == "elo":
        result = backtester.backtest_elo_model(start_date, end_date, league)
    else:
        raise ValueError(f"Unknown model: {model}")
    
    if save:
        backtester.save_backtest_results(result)
    
    return result


def main():
    """Run backtest and display results."""
    import json
    
    logger.info("Running Elo model backtest...")
    result = run_backtest(model="elo", days_back=365, save=True)
    
    print("=== Backtest Results ===")
    print(f"Model: {result.model_name}")
    print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
    print(f"Total Predictions: {result.total_predictions}")
    print(f"\nMetrics:")
    print(f"  Brier Score: {result.brier_score:.5f} (lower is better, random = 0.25)")
    print(f"  Log Loss: {result.log_loss:.5f} (lower is better)")
    print(f"  Accuracy: {result.accuracy:.1%} (favorite wins)")
    
    print(f"\nCalibration (expected vs actual):")
    for bucket, data in result.calibration_buckets.items():
        if data["count"] > 0:
            print(f"  {bucket}: expected {data['expected_rate']:.0%}, actual {data['actual_rate']:.0%} (n={data['count']})")
    
    print(f"\nBy League:")
    for lg, data in sorted(result.by_league.items(), key=lambda x: -x[1]["count"]):
        print(f"  {lg}: {data['count']} matches, accuracy {data['accuracy']:.1%}, brier {data['brier_score']:.4f}")


if __name__ == "__main__":
    main()
