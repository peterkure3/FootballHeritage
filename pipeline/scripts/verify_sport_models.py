"""Reproduce held-out probability metrics from trusted, checksummed candidates."""

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from models.sport_data import SPORTS
from models.sport_features import build_features
from models.sport_predict import candidate_directory
from models.train_sports import supervised_splits
from models.validation import probability_metrics


def verify(candidate_id: str, sports: list[str], capture_dir: Path | None = None) -> dict:
    result = {"candidate_id": candidate_id, "sports": {}}
    if capture_dir:
        manifest = json.loads((capture_dir / "manifest.json").read_text(encoding="utf-8"))
        assert hashlib.sha256((capture_dir / "normalized.jsonl").read_bytes()).hexdigest() == manifest["normalized_sha256"]
        captures = manifest["captures"] + ([manifest["nfl_coverage"]] if manifest.get("nfl_coverage") else [])
        for capture in captures:
            assert hashlib.sha256(Path(capture["source_file"]).read_bytes()).hexdigest() == capture["capture_sha256"]
        result["historical_source_checksums_verified"] = len(captures)
    for sport in sports:
        directory = candidate_directory(candidate_id, sport)
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        for filename, key in [("dataset.parquet", "dataset_sha256"), ("model.pkl", "model_sha256")]:
            assert hashlib.sha256((directory / filename).read_bytes()).hexdigest() == metrics[key]
        games = pd.read_parquet(directory / "dataset.parquet")
        X = build_features(games, sport)
        splits, _ = supervised_splits(games, sport)
        test = splits["test"]
        y = np.array([metrics["classes"].index(value) for value in games.iloc[test].result])
        with threadpool_limits(limits=2):
            probabilities = joblib.load(directory / "model.pkl").predict_proba(X.iloc[test])
        reproduced = probability_metrics(y, probabilities, metrics["classes"])
        for key in ["samples", "accuracy", "log_loss", "brier_score"]:
            np.testing.assert_allclose(reproduced[key], metrics["test"][key], rtol=0, atol=1e-12)
        season_metrics = {}
        if "season" in games:
            for season in games.iloc[test].season.unique():
                selected = games.iloc[test].season.eq(season).to_numpy()
                season_metrics[str(season)] = probability_metrics(y[selected], probabilities[selected], metrics["classes"])
        result["sports"][sport] = {"artifact_checksums_verified": True, "held_out_metrics_reproduced": True,
            "test": reproduced, "test_by_season": season_metrics}
        print(json.dumps({"sport": sport, "samples": reproduced["samples"], "accuracy": reproduced["accuracy"],
                          "log_loss": reproduced["log_loss"], "metrics_reproduced": True}), flush=True)
    (candidate_directory(candidate_id, sports[0]).parent / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--sports", nargs="+", choices=list(SPORTS), required=True)
    parser.add_argument("--capture-dir", type=Path)
    args = parser.parse_args()
    verify(args.candidate_id, args.sports, args.capture_dir)


if __name__ == "__main__":
    main()
