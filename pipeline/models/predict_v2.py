"""
Enhanced prediction module for v2 model.
Generates predictions using the calibrated ensemble model with enhanced features.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    DATABASE_URI,
    MODEL_DIR,
    LOG_LEVEL,
)
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

MODEL_VERSION = "2.0.0"

# ELO Configuration (must match training)
ELO_K_FACTOR = 32
ELO_HOME_ADVANTAGE = 100
ELO_INITIAL = 1500


def load_model_artifacts() -> Tuple:
    """
    Load trained model and associated artifacts.
    
    Returns:
        Tuple of (model, label_encoder, feature_names, scaler)
    """
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    scaler_path = MODEL_DIR / f"scaler_v{MODEL_VERSION}.pkl"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    model = joblib.load(model_path)
    label_encoder = joblib.load(encoder_path)
    feature_names = joblib.load(features_path)
    
    scaler = None
    if scaler_path.exists():
        scaler = joblib.load(scaler_path)
    
    logger.info(f"Loaded model v{MODEL_VERSION}")
    logger.info(f"Features: {len(feature_names)} features")
    logger.info(f"Classes: {list(label_encoder.classes_)}")
    
    return model, label_encoder, feature_names, scaler


def get_team_elo_ratings(engine) -> Dict[str, float]:
    """
    Calculate current ELO ratings for all teams from match history.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        Dictionary of team -> ELO rating
    """
    query = text("""
        SELECT 
            home_team,
            away_team,
            result,
            date
        FROM matches
        WHERE result IS NOT NULL
        ORDER BY date ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    elo_ratings: Dict[str, float] = {}
    
    for _, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        result = row["result"]
        
        home_elo = elo_ratings.get(home_team, ELO_INITIAL)
        away_elo = elo_ratings.get(away_team, ELO_INITIAL)
        
        home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - ELO_HOME_ADVANTAGE) / 400))
        
        if result == "home_win":
            home_actual = 1.0
        elif result == "draw":
            home_actual = 0.5
        else:
            home_actual = 0.0
        
        elo_ratings[home_team] = home_elo + ELO_K_FACTOR * (home_actual - home_expected)
        elo_ratings[away_team] = away_elo + ELO_K_FACTOR * ((1 - home_actual) - (1 - home_expected))
    
    logger.info(f"Calculated ELO ratings for {len(elo_ratings)} teams")
    return elo_ratings


def get_team_stats(engine, team_name: str, window: int = 10) -> Dict:
    """
    Get comprehensive stats for a team.
    
    Args:
        engine: SQLAlchemy engine
        team_name: Team name to look up
        window: Number of recent matches
    
    Returns:
        Dictionary with team statistics
    """
    query = text("""
        WITH recent_matches AS (
            SELECT 
                home_team,
                away_team,
                home_score,
                away_score,
                result,
                date,
                CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as team_side
            FROM matches
            WHERE (home_team ILIKE :team OR away_team ILIKE :team)
                AND result IS NOT NULL
                AND home_score IS NOT NULL
                AND away_score IS NOT NULL
            ORDER BY date DESC
            LIMIT :window
        )
        SELECT 
            COUNT(*) as total_matches,
            COUNT(CASE WHEN 
                (team_side = 'home' AND result = 'home_win') OR 
                (team_side = 'away' AND result = 'away_win') 
            THEN 1 END) as wins,
            COUNT(CASE WHEN result = 'draw' THEN 1 END) as draws,
            COUNT(CASE WHEN 
                (team_side = 'home' AND result = 'away_win') OR 
                (team_side = 'away' AND result = 'home_win') 
            THEN 1 END) as losses,
            AVG(CASE WHEN team_side = 'home' THEN home_score - away_score 
                     ELSE away_score - home_score END) as avg_gd,
            AVG(CASE WHEN team_side = 'home' THEN home_score ELSE away_score END) as avg_goals_for,
            AVG(CASE WHEN team_side = 'home' THEN away_score ELSE home_score END) as avg_goals_against
        FROM recent_matches
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
    
    if result and result[0] > 0:
        total = result[0]
        return {
            "wins": result[1] or 0,
            "draws": result[2] or 0,
            "losses": result[3] or 0,
            "avg_gd": float(result[4] or 0.0),
            "avg_goals_for": float(result[5] or 1.5),
            "avg_goals_against": float(result[6] or 1.5),
            "win_rate": (result[1] or 0) / total,
            "form_points": ((result[1] or 0) * 3 + (result[2] or 0)) / (total * 3),
        }
    
    return {
        "wins": 0, "draws": 0, "losses": 0,
        "avg_gd": 0.0, "avg_goals_for": 1.5, "avg_goals_against": 1.5,
        "win_rate": 0.33, "form_points": 0.33,
    }


def get_venue_stats(engine, team_name: str, is_home: bool, window: int = 20) -> Dict:
    """
    Get venue-specific stats for a team.
    
    Args:
        engine: SQLAlchemy engine
        team_name: Team name
        is_home: Whether to get home or away stats
        window: Number of matches to consider
    
    Returns:
        Dictionary with venue-specific statistics
    """
    if is_home:
        query = text("""
            SELECT 
                COUNT(*) as matches,
                COUNT(CASE WHEN result = 'home_win' THEN 1 END) as wins,
                AVG(home_score) as avg_goals
            FROM matches
            WHERE home_team ILIKE :team
                AND result IS NOT NULL
            ORDER BY date DESC
            LIMIT :window
        """)
    else:
        query = text("""
            SELECT 
                COUNT(*) as matches,
                COUNT(CASE WHEN result = 'away_win' THEN 1 END) as wins,
                AVG(away_score) as avg_goals
            FROM matches
            WHERE away_team ILIKE :team
                AND result IS NOT NULL
            ORDER BY date DESC
            LIMIT :window
        """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
    
    if result and result[0] > 0:
        return {
            "win_rate": (result[1] or 0) / result[0],
            "avg_goals": float(result[2] or 1.5),
        }
    
    return {"win_rate": 0.5 if is_home else 0.33, "avg_goals": 1.5}


def get_h2h_stats(engine, home_team: str, away_team: str, window: int = 10) -> Dict:
    """
    Get head-to-head statistics between two teams.
    
    Args:
        engine: SQLAlchemy engine
        home_team: Home team name
        away_team: Away team name
        window: Number of H2H matches to consider
    
    Returns:
        Dictionary with H2H statistics
    """
    query = text("""
        SELECT 
            home_team,
            away_team,
            result,
            home_score,
            away_score
        FROM matches
        WHERE ((home_team ILIKE :home AND away_team ILIKE :away) OR
               (home_team ILIKE :away AND away_team ILIKE :home))
            AND result IS NOT NULL
        ORDER BY date DESC
        LIMIT :window
    """)
    
    with engine.connect() as conn:
        results = conn.execute(query, {
            "home": f"%{home_team}%",
            "away": f"%{away_team}%",
            "window": window
        }).fetchall()
    
    if not results:
        return {
            "home_wins": 0, "draws": 0, "away_wins": 0,
            "home_goals_avg": 1.5, "away_goals_avg": 1.5,
        }
    
    home_wins = 0
    draws = 0
    away_wins = 0
    home_goals = []
    away_goals = []
    
    for row in results:
        match_home = row[0]
        result = row[2]
        h_score = row[3] or 0
        a_score = row[4] or 0
        
        # Determine if current home_team was home in this match
        if home_team.lower() in match_home.lower():
            home_goals.append(h_score)
            away_goals.append(a_score)
            if result == "home_win":
                home_wins += 1
            elif result == "draw":
                draws += 1
            else:
                away_wins += 1
        else:
            home_goals.append(a_score)
            away_goals.append(h_score)
            if result == "away_win":
                home_wins += 1
            elif result == "draw":
                draws += 1
            else:
                away_wins += 1
    
    return {
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_goals_avg": np.mean(home_goals) if home_goals else 1.5,
        "away_goals_avg": np.mean(away_goals) if away_goals else 1.5,
    }


def build_feature_vector(
    home_team: str,
    away_team: str,
    engine,
    elo_ratings: Dict[str, float],
    odds: Optional[Dict] = None,
    feature_names: List[str] = None,
) -> pd.DataFrame:
    """
    Build feature vector for prediction.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        engine: SQLAlchemy engine
        elo_ratings: Dictionary of team ELO ratings
        odds: Optional odds dictionary
        feature_names: List of required feature names
    
    Returns:
        DataFrame with features
    """
    # Get team stats
    home_stats = get_team_stats(engine, home_team)
    away_stats = get_team_stats(engine, away_team)
    
    # Get venue stats
    home_venue = get_venue_stats(engine, home_team, is_home=True)
    away_venue = get_venue_stats(engine, away_team, is_home=False)
    
    # Get H2H stats
    h2h = get_h2h_stats(engine, home_team, away_team)
    
    # Get ELO ratings
    home_elo = elo_ratings.get(home_team, ELO_INITIAL)
    away_elo = elo_ratings.get(away_team, ELO_INITIAL)
    elo_diff = home_elo - away_elo + ELO_HOME_ADVANTAGE
    home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - ELO_HOME_ADVANTAGE) / 400))
    
    # Process odds
    if odds is None:
        # Use average odds as fallback
        odds = {"home_win": 2.5, "draw": 3.2, "away_win": 2.8}
    
    home_odds = odds.get("home_win", 2.5)
    draw_odds = odds.get("draw", 3.2)
    away_odds = odds.get("away_win", 2.8)
    
    # Calculate odds-derived features
    implied_home = 1 / home_odds if home_odds > 0 else 0.4
    implied_draw = 1 / draw_odds if draw_odds > 0 else 0.25
    implied_away = 1 / away_odds if away_odds > 0 else 0.35
    overround = implied_home + implied_draw + implied_away
    
    fair_home = implied_home / overround if overround > 0 else 0.4
    fair_draw = implied_draw / overround if overround > 0 else 0.25
    fair_away = implied_away / overround if overround > 0 else 0.35
    
    # Build feature dictionary
    features = {
        # Odds-derived features (STRONGEST)
        "fair_home_prob": fair_home,
        "fair_draw_prob": fair_draw,
        "fair_away_prob": fair_away,
        "odds_ratio": home_odds / away_odds if away_odds > 0 else 1.0,
        "odds_spread": home_odds - away_odds,
        "log_home_odds": np.log(max(home_odds, 1.01)),
        "log_away_odds": np.log(max(away_odds, 1.01)),
        "log_draw_odds": np.log(max(draw_odds, 1.01)),
        "home_is_favorite": 1 if home_odds < away_odds else 0,
        "favorite_odds": min(home_odds, away_odds),
        "underdog_odds": max(home_odds, away_odds),
        
        # ELO features
        "home_elo": home_elo,
        "away_elo": away_elo,
        "elo_diff": elo_diff,
        "home_expected": home_expected,
        
        # H2H features
        "h2h_home_wins": h2h["home_wins"],
        "h2h_draws": h2h["draws"],
        "h2h_away_wins": h2h["away_wins"],
        "h2h_home_goals_avg": h2h["home_goals_avg"],
        "h2h_away_goals_avg": h2h["away_goals_avg"],
        
        # Weighted form (approximated from stats)
        "home_weighted_form": home_stats["form_points"] * 3,
        "away_weighted_form": away_stats["form_points"] * 3,
        "home_weighted_goals_for": home_stats["avg_goals_for"],
        "home_weighted_goals_against": home_stats["avg_goals_against"],
        "away_weighted_goals_for": away_stats["avg_goals_for"],
        "away_weighted_goals_against": away_stats["avg_goals_against"],
        
        # Venue stats
        "home_team_home_win_rate": home_venue["win_rate"],
        "home_team_home_goals_avg": home_venue["avg_goals"],
        "away_team_away_win_rate": away_venue["win_rate"],
        "away_team_away_goals_avg": away_venue["avg_goals"],
        
        # Original form features
        "home_team_wins_last_n": home_stats["wins"],
        "home_team_draws_last_n": home_stats["draws"],
        "home_team_losses_last_n": home_stats["losses"],
        "away_team_wins_last_n": away_stats["wins"],
        "away_team_draws_last_n": away_stats["draws"],
        "away_team_losses_last_n": away_stats["losses"],
        "home_team_avg_gd_last_n": home_stats["avg_gd"],
        "away_team_avg_gd_last_n": away_stats["avg_gd"],
        
        # Raw odds (for compatibility)
        "home_win": home_odds,
        "draw": draw_odds,
        "away_win": away_odds,
    }
    
    # Create DataFrame with correct feature order
    if feature_names:
        X = pd.DataFrame([{k: features.get(k, 0) for k in feature_names}])
    else:
        X = pd.DataFrame([features])
    
    X = X.fillna(0)
    
    return X


def predict_match(
    home_team: str,
    away_team: str,
    odds: Optional[Dict] = None,
) -> Dict:
    """
    Predict match outcome using enhanced model.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        odds: Optional odds dictionary
    
    Returns:
        Prediction dictionary with probabilities
    """
    # Load model
    model, label_encoder, feature_names, scaler = load_model_artifacts()
    
    # Get database connection
    engine = create_engine(DATABASE_URI)
    
    # Get ELO ratings
    elo_ratings = get_team_elo_ratings(engine)
    
    # Build features
    X = build_feature_vector(
        home_team, away_team, engine, elo_ratings, odds, feature_names
    )
    
    # Apply scaler if available
    if scaler is not None:
        X = pd.DataFrame(scaler.transform(X), columns=X.columns)
    
    # Predict
    probabilities = model.predict_proba(X)[0]
    predicted_class = model.predict(X)[0]
    winner = label_encoder.inverse_transform([predicted_class])[0]
    
    # Map probabilities
    prob_dict = dict(zip(label_encoder.classes_, probabilities))
    
    return {
        "winner": winner,
        "home_prob": float(prob_dict.get("home_win", 0.0)),
        "draw_prob": float(prob_dict.get("draw", 0.0)),
        "away_prob": float(prob_dict.get("away_win", 0.0)),
        "model_version": MODEL_VERSION,
        "confidence": get_confidence_level(max(probabilities)),
    }


def get_confidence_level(max_prob: float) -> str:
    """Determine confidence level from max probability."""
    if max_prob > 0.55:
        return "High"
    elif max_prob > 0.42:
        return "Medium"
    else:
        return "Low"


def generate_predictions(
    model,
    label_encoder,
    X: pd.DataFrame,
    match_ids: pd.Series,
) -> pd.DataFrame:
    """
    Generate predictions for multiple matches.
    
    Args:
        model: Trained model
        label_encoder: Label encoder
        X: Feature matrix
        match_ids: Match IDs
    
    Returns:
        DataFrame with predictions
    """
    # Predict
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)
    
    # Decode predictions
    predicted_outcomes = label_encoder.inverse_transform(y_pred)
    
    # Create predictions DataFrame
    predictions = pd.DataFrame({
        "match_id": match_ids,
        "model_version": MODEL_VERSION,
        "winner": predicted_outcomes,
        "created_at": datetime.now(),
    })
    
    # Add probabilities
    for idx, class_name in enumerate(label_encoder.classes_):
        if class_name == "home_win":
            predictions["home_prob"] = y_pred_proba[:, idx]
        elif class_name == "draw":
            predictions["draw_prob"] = y_pred_proba[:, idx]
        elif class_name == "away_win":
            predictions["away_prob"] = y_pred_proba[:, idx]
    
    logger.info(f"Generated {len(predictions)} predictions")
    logger.info(f"Prediction distribution:\n{predictions['winner'].value_counts()}")
    
    # Log probability statistics
    logger.info(f"Home prob range: {predictions['home_prob'].min():.3f} - {predictions['home_prob'].max():.3f}")
    logger.info(f"Away prob range: {predictions['away_prob'].min():.3f} - {predictions['away_prob'].max():.3f}")
    
    return predictions


def save_predictions_to_db(predictions: pd.DataFrame, engine) -> None:
    """Save predictions to database."""
    try:
        with engine.begin() as conn:
            match_ids = tuple(predictions["match_id"].tolist())
            
            if match_ids:
                delete_query = text(
                    "DELETE FROM predictions WHERE match_id IN :match_ids"
                )
                conn.execute(delete_query, {"match_ids": match_ids})
            
            predictions.to_sql(
                "predictions",
                conn,
                if_exists="append",
                index=False,
                method="multi"
            )
        
        logger.info(f"Saved {len(predictions)} predictions to database")
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to save predictions: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Test prediction
    result = predict_match("Arsenal", "Chelsea")
    print(f"Prediction: {result}")
