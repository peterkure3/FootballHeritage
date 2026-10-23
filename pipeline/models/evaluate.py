"""Reproduce a candidate's untouched test-period metrics from its frozen dataset."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from models.features import FEATURE_SCHEMA_VERSION, FEATURE_NAMES, build_feature_frame
from models.validation import chronological_split, probability_metrics


@dataclass
class CandidateEvaluation:
    model: object
    encoder: object
    features: pd.DataFrame
    fixtures: pd.DataFrame
    test_indices: np.ndarray
    manifest: dict


def load_evaluation_bundle(bundle: Path) -> CandidateEvaluation:
    paths = list(bundle.glob("metrics_v*.json"))
    if len(paths) != 1:
        raise ValueError("Supply a candidate bundle with exactly one metrics manifest")
    manifest = json.loads(paths[0].read_text(encoding="utf-8"))
    if manifest.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("Feature schema does not match this evaluator")
    dataset = bundle / "dataset.parquet"
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != manifest["dataset_sha256"]:
        raise ValueError("Frozen evaluation dataset checksum mismatch")
    X, fixtures = build_feature_frame(pd.read_parquet(dataset))
    if list(X.columns) != manifest["features"] or list(X.columns) != FEATURE_NAMES:
        raise ValueError("Feature columns differ from the training manifest")
    indices = chronological_split(fixtures.date)["test"]
    version = manifest["model_version"]
    model = joblib.load(bundle / f"model_v{version}.pkl")
    encoder = joblib.load(bundle / f"label_encoder_v{version}.pkl")
    if list(encoder.classes_) != manifest["classes"]:
        raise ValueError("Encoder classes differ from the training manifest")
    return CandidateEvaluation(model, encoder, X, fixtures, indices, manifest)


def evaluate_model(bundle: Path) -> dict:
    data = load_evaluation_bundle(bundle)
    return probability_metrics(data.encoder.transform(data.fixtures.iloc[data.test_indices].result),
                               data.model.predict_proba(data.features.iloc[data.test_indices]),
                               list(data.encoder.classes_))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate_model(args.bundle), indent=2))


if __name__ == "__main__":
    main()
