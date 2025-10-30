"""
Train XGBoost model for match outcome prediction.
Save model artifacts and metrics to model_store/.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    MODEL_DIR,
    MODEL_VERSION,
    XGBOOST_PARAMS,
    MIN_MATCHES_FOR_TRAINING,
    PROCESSED_DATA_DIR,
    LOG_LEVEL,
)
from etl.utils import setup_logger, ensure_dir, save_json

logger = setup_logger(__name__, LOG_LEVEL)


def load_training_data() -> pd.DataFrame:
    """
    Load processed data for training.
    
    Returns:
        Combined DataFrame from all processed files
    """
    parquet_files = list(PROCESSED_DATA_DIR.glob("matches_*.parquet"))
    
    if not parquet_files:
        raise ValueError("No processed data files found for training")
    
    dfs = []
    for file in parquet_files:
        df = pd.read_parquet(file)
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(combined)} matches from {len(dfs)} files")
    
    return combined


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features and target for training.
    
    Args:
        df: Raw DataFrame
    
    Returns:
        Tuple of (features DataFrame, target Series)
    """
    # Filter to matches with results
    df = df[df["result"].notna()].copy()
    
    if len(df) < MIN_MATCHES_FOR_TRAINING:
        raise ValueError(
            f"Insufficient data for training: {len(df)} matches "
            f"(minimum {MIN_MATCHES_FOR_TRAINING} required)"
        )
    
    # Define feature columns
    feature_cols = [
        "home_team_wins_last_n",
        "home_team_draws_last_n",
        "home_team_losses_last_n",
        "away_team_wins_last_n",
        "away_team_draws_last_n",
        "away_team_losses_last_n",
        "home_team_avg_gd_last_n",
        "away_team_avg_gd_last_n",
        "home_win",  # odds
        "draw",      # odds
        "away_win",  # odds
        "odds_spread",
    ]
    
    # Filter to available features
    available_features = [col for col in feature_cols if col in df.columns]
    
    if not available_features:
        raise ValueError("No features available for training")
    
    # Create feature matrix
    X = df[available_features].copy()
    
    # Fill missing values
    X = X.fillna(0)
    
    # Create target
    y = df["result"].copy()
    
    logger.info(f"Prepared {len(X)} samples with {len(available_features)} features")
    logger.info(f"Features: {available_features}")
    logger.info(f"Target distribution:\n{y.value_counts()}")
    
    return X, y


def train_xgboost_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series
) -> Tuple[xgb.XGBClassifier, LabelEncoder, Dict]:
    """
    Train XGBoost classifier.
    
    Args:
        X_train: Training features
        y_train: Training target
        X_val: Validation features
        y_val: Validation target
    
    Returns:
        Tuple of (trained model, label encoder, metrics dict)
    """
    # Encode labels
    le = LabelEncoder()
    y_train_encoded = le.fit_transform(y_train)
    y_val_encoded = le.transform(y_val)
    
    logger.info(f"Label encoding: {dict(zip(le.classes_, range(len(le.classes_))))}")
    
    # Train model
    model = xgb.XGBClassifier(**XGBOOST_PARAMS)
    
    logger.info("Training XGBoost model...")
    model.fit(
        X_train,
        y_train_encoded,
        eval_set=[(X_val, y_val_encoded)],
        verbose=False
    )
    
    # Evaluate
    train_acc = model.score(X_train, y_train_encoded)
    val_acc = model.score(X_val, y_val_encoded)
    
    # Get predictions for detailed metrics
    y_pred = model.predict(X_val)
    y_pred_proba = model.predict_proba(X_val)
    
    metrics = {
        "model_version": MODEL_VERSION,
        "train_accuracy": float(train_acc),
        "val_accuracy": float(val_acc),
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "features": list(X_train.columns),
        "classes": list(le.classes_),
        "trained_at": datetime.now().isoformat(),
    }
    
    logger.info(f"Training accuracy: {train_acc:.4f}")
    logger.info(f"Validation accuracy: {val_acc:.4f}")
    
    return model, le, metrics


def save_model_artifacts(
    model: xgb.XGBClassifier,
    label_encoder: LabelEncoder,
    metrics: Dict,
    feature_names: list
) -> None:
    """
    Save model, encoder, and metrics to disk.
    
    Args:
        model: Trained XGBoost model
        label_encoder: Label encoder
        metrics: Training metrics
        feature_names: List of feature names
    """
    ensure_dir(MODEL_DIR)
    
    # Save model
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    joblib.dump(model, model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save label encoder
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    joblib.dump(label_encoder, encoder_path)
    logger.info(f"Saved label encoder to {encoder_path}")
    
    # Save feature names
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    joblib.dump(feature_names, features_path)
    logger.info(f"Saved feature names to {features_path}")
    
    # Save metrics
    metrics_path = MODEL_DIR / f"metrics_v{MODEL_VERSION}.json"
    save_json(metrics, metrics_path)
    logger.info(f"Saved metrics to {metrics_path}")
    
    # Save feature importance
    feature_importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    importance_path = MODEL_DIR / f"feature_importance_v{MODEL_VERSION}.csv"
    feature_importance.to_csv(importance_path, index=False)
    logger.info(f"Saved feature importance to {importance_path}")


def train_model() -> None:
    """Main training pipeline."""
    logger.info("Starting model training")
    
    # Load data
    df = load_training_data()
    
    # Prepare features
    X, y = prepare_features(df)
    
    # Split data
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"Train set: {len(X_train)} samples")
    logger.info(f"Validation set: {len(X_val)} samples")
    
    # Train model
    model, label_encoder, metrics = train_xgboost_model(
        X_train, y_train, X_val, y_val
    )
    
    # Save artifacts
    save_model_artifacts(model, label_encoder, metrics, list(X.columns))
    
    logger.info("Model training completed successfully")


def main() -> None:
    """Main entry point."""
    try:
        train_model()
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
