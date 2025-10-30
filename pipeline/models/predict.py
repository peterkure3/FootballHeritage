"""
Generate predictions for upcoming matches using trained model.
Save predictions to database.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    DATABASE_URI,
    MODEL_DIR,
    MODEL_VERSION,
    LOG_LEVEL,
)
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


def load_model_artifacts() -> Tuple:
    """
    Load trained model and associated artifacts.
    
    Returns:
        Tuple of (model, label_encoder, feature_names)
    """
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    model = joblib.load(model_path)
    label_encoder = joblib.load(encoder_path)
    feature_names = joblib.load(features_path)
    
    logger.info(f"Loaded model v{MODEL_VERSION}")
    logger.info(f"Features: {feature_names}")
    logger.info(f"Classes: {list(label_encoder.classes_)}")
    
    return model, label_encoder, feature_names


def get_upcoming_matches(engine) -> pd.DataFrame:
    """
    Fetch upcoming matches from database.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        DataFrame with upcoming matches
    """
    query = """
        SELECT 
            m.match_id,
            m.competition,
            m.date,
            m.home_team,
            m.away_team,
            m.home_team_wins_last_n,
            m.home_team_draws_last_n,
            m.home_team_losses_last_n,
            m.away_team_wins_last_n,
            m.away_team_draws_last_n,
            m.away_team_losses_last_n,
            m.home_team_avg_gd_last_n,
            m.away_team_avg_gd_last_n,
            AVG(o.home_win) as home_win,
            AVG(o.draw) as draw,
            AVG(o.away_win) as away_win
        FROM matches m
        LEFT JOIN odds o ON m.match_id = o.match_id
        WHERE m.status IN ('SCHEDULED', 'TIMED')
            AND m.date > NOW()
        GROUP BY 
            m.match_id, m.competition, m.date, m.home_team, m.away_team,
            m.home_team_wins_last_n, m.home_team_draws_last_n, m.home_team_losses_last_n,
            m.away_team_wins_last_n, m.away_team_draws_last_n, m.away_team_losses_last_n,
            m.home_team_avg_gd_last_n, m.away_team_avg_gd_last_n
        ORDER BY m.date
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    logger.info(f"Fetched {len(df)} upcoming matches")
    return df


def prepare_prediction_features(
    df: pd.DataFrame,
    feature_names: List[str]
) -> pd.DataFrame:
    """
    Prepare features for prediction.
    
    Args:
        df: DataFrame with match data
        feature_names: List of required feature names
    
    Returns:
        DataFrame with features in correct order
    """
    # Calculate odds spread if odds are available
    if "home_win" in df.columns and "away_win" in df.columns:
        df["odds_spread"] = df["home_win"] - df["away_win"]
    
    # Select and order features
    X = df[feature_names].copy()
    
    # Fill missing values
    X = X.fillna(0)
    
    return X


def generate_predictions(
    model,
    label_encoder,
    X: pd.DataFrame,
    match_ids: pd.Series
) -> pd.DataFrame:
    """
    Generate predictions for matches.
    
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
    
    # Add probabilities for each class
    for idx, class_name in enumerate(label_encoder.classes_):
        if class_name == "home_win":
            predictions["home_prob"] = y_pred_proba[:, idx]
        elif class_name == "draw":
            predictions["draw_prob"] = y_pred_proba[:, idx]
        elif class_name == "away_win":
            predictions["away_prob"] = y_pred_proba[:, idx]
    
    logger.info(f"Generated {len(predictions)} predictions")
    logger.info(f"Prediction distribution:\n{predictions['winner'].value_counts()}")
    
    return predictions


def save_predictions_to_db(predictions: pd.DataFrame, engine) -> None:
    """
    Save predictions to database.
    
    Args:
        predictions: DataFrame with predictions
        engine: SQLAlchemy engine
    """
    try:
        with engine.begin() as conn:
            # Delete existing predictions for these matches
            match_ids = tuple(predictions["match_id"].tolist())
            
            if match_ids:
                delete_query = text(
                    "DELETE FROM predictions WHERE match_id IN :match_ids"
                )
                conn.execute(delete_query, {"match_ids": match_ids})
            
            # Insert new predictions
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


def predict_upcoming_matches() -> None:
    """Main prediction pipeline."""
    logger.info("Starting prediction generation")
    
    # Load model
    model, label_encoder, feature_names = load_model_artifacts()
    
    # Get database connection
    engine = create_engine(DATABASE_URI)
    
    # Fetch upcoming matches
    matches_df = get_upcoming_matches(engine)
    
    if matches_df.empty:
        logger.warning("No upcoming matches found")
        return
    
    # Prepare features
    X = prepare_prediction_features(matches_df, feature_names)
    
    # Generate predictions
    predictions = generate_predictions(
        model,
        label_encoder,
        X,
        matches_df["match_id"]
    )
    
    # Save to database
    save_predictions_to_db(predictions, engine)
    
    logger.info("Prediction generation completed")


def main() -> None:
    """Main entry point."""
    try:
        predict_upcoming_matches()
    except Exception as e:
        logger.error(f"Prediction generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
