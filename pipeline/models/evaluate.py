"""
Evaluate model performance on test data.
Generate detailed metrics and reports.
"""

import sys
from pathlib import Path
from typing import Dict

import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    MODEL_DIR,
    MODEL_VERSION,
    PROCESSED_DATA_DIR,
    LOG_LEVEL,
)
from etl.utils import setup_logger, save_json

logger = setup_logger(__name__, LOG_LEVEL)


def load_model_artifacts():
    """Load trained model and artifacts."""
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    
    model = joblib.load(model_path)
    label_encoder = joblib.load(encoder_path)
    feature_names = joblib.load(features_path)
    
    return model, label_encoder, feature_names


def load_test_data() -> pd.DataFrame:
    """Load processed data for evaluation."""
    parquet_files = list(PROCESSED_DATA_DIR.glob("matches_*.parquet"))
    
    if not parquet_files:
        raise ValueError("No processed data files found")
    
    # Load most recent file
    latest_file = sorted(parquet_files)[-1]
    df = pd.read_parquet(latest_file)
    
    logger.info(f"Loaded {len(df)} matches from {latest_file}")
    return df


def evaluate_model() -> Dict:
    """
    Evaluate model and generate metrics.
    
    Returns:
        Dictionary with evaluation metrics
    """
    logger.info("Starting model evaluation")
    
    # Load model and data
    model, label_encoder, feature_names = load_model_artifacts()
    df = load_test_data()
    
    # Filter to matches with results
    df = df[df["result"].notna()].copy()
    
    # Prepare features
    X = df[feature_names].fillna(0)
    y = df["result"]
    
    # Encode labels
    y_encoded = label_encoder.transform(y)
    
    # Predict
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)
    
    # Calculate metrics
    accuracy = accuracy_score(y_encoded, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_encoded, y_pred, average='weighted'
    )
    
    # Confusion matrix
    cm = confusion_matrix(y_encoded, y_pred)
    
    # Classification report
    report = classification_report(
        y_encoded,
        y_pred,
        target_names=label_encoder.classes_,
        output_dict=True
    )
    
    metrics = {
        "model_version": MODEL_VERSION,
        "test_samples": len(X),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "class_distribution": y.value_counts().to_dict(),
    }
    
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall: {recall:.4f}")
    logger.info(f"F1 Score: {f1:.4f}")
    
    # Save evaluation results
    eval_path = MODEL_DIR / f"evaluation_v{MODEL_VERSION}.json"
    save_json(metrics, eval_path)
    logger.info(f"Saved evaluation results to {eval_path}")
    
    # Save confusion matrix as CSV
    cm_df = pd.DataFrame(
        cm,
        index=label_encoder.classes_,
        columns=label_encoder.classes_
    )
    cm_path = MODEL_DIR / f"confusion_matrix_v{MODEL_VERSION}.csv"
    cm_df.to_csv(cm_path)
    logger.info(f"Saved confusion matrix to {cm_path}")
    
    return metrics


def main() -> None:
    """Main entry point."""
    try:
        evaluate_model()
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
