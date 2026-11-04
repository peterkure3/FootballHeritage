"""Adversarial contract checks; synthetic results are not sports evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from etl.audit_basketball_pbp import audit, normalize
from models.feature_availability import ForecastContract, validate_feature
from models.research_experiments import candidates, main, run, validate_dataset
from models.simulation_metrics import empirical_crps, paired_score_metrics


def evidence() -> dict:
    return {"feature": "form", "definition": "Prior verified results", "source_url": "https://example.org/results",
        "snapshot_sha256": "a" * 64, "availability_status": "verified", "available_at": "2026-01-01T00:00:00Z",
        "aggregation_cutoff": "2026-01-01T00:00:00Z", "kind": "rolling",
        "dependencies": [{"game_id": "old", "kickoff": "2025-12-28T12:00:00Z",
            "available_at": "2025-12-29T00:00:00Z", "availability_status": "verified"}]}


@pytest.mark.parametrize("change", [
    {"availability_status": "unknown"}, {"availability_status": "assumed"},
    {"available_at": "2026-01-03T00:00:00Z"}, {"aggregation_cutoff": "2026-01-03T00:00:00Z"},
    {"available_at": "2026-01-01"}, {"dependencies": None}, {"snapshot_sha256": "bad"}])
def test_rejects_invalid_availability(change: dict) -> None:
    value = evidence()
    value.update(change)
    with pytest.raises(ValueError):
        validate_feature(ForecastContract("new", "2026-01-02T18:00:00Z", "2026-01-02T17:00:00Z"), value)


@pytest.mark.parametrize("change", [{"game_id": "new"}, {"kickoff": "2026-01-04T12:00:00Z"},
    {"available_at": "2026-01-02T12:00:00Z"}, {"availability_status": "assumed"}])
def test_rejects_leaking_rolling_dependencies(change: dict) -> None:
    value = evidence()
    value["dependencies"][0].update(change)
    with pytest.raises(ValueError):
        validate_feature(ForecastContract("new", "2026-01-02T18:00:00Z", "2026-01-02T17:00:00Z"), value)


def test_forecast_modes_and_valid_evidence() -> None:
    validate_feature(ForecastContract("new", "2026-01-02T18:00:00Z", "2026-01-02T17:00:00Z"), evidence())
    with pytest.raises(ValueError):
        ForecastContract("new", "2026-01-02T18:00:00Z", "2026-01-02T19:00:00Z").validate()
    ForecastContract("new", "2026-01-02T18:00:00Z", "2026-01-02T19:00:00Z", "live").validate()


def test_pairs_preserve_dependence_and_crps_matches_brute_force() -> None:
    scores = np.array([[1, 0], [2, 1], [3, 2], [4, 3]])
    metrics = paired_score_metrics(scores, [2, 1])
    assert metrics["distributions"]["margin"]["crps"] == 0
    assert metrics["distributions"]["margin"]["mean_mc_standard_error"] == 0
    values = np.array([0, 2, 4])
    expected = np.mean(abs(values - 1)) - .5 * np.mean(abs(values[:, None] - values))
    assert empirical_crps(values, 1) == pytest.approx(expected)
    for invalid in [np.array([[1, -1], [2, 3]]), np.array([[1, np.nan], [2, 3]]), np.array([[1.5, 2], [2, 3]])]:
        with pytest.raises(ValueError):
            paired_score_metrics(invalid, [1, 0])


def basketball_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.DataFrame({"game_id": ["g"] * 3, "event_id": ["a", "b", "c"], "sequence": [1, 2, 3],
        "period": [1, 4, 4], "clock_seconds": [720, 10, 0], "home_score": [0, 100, 100], "away_score": [0, 90, 90]})
    schedule = pd.DataFrame({"game_id": ["g"], "date": ["2026-01-01T12:00:00Z"],
        "completed": [True], "home_score": [100], "away_score": [90]})
    return events, schedule


def test_mapping_ignores_colliding_provider_columns() -> None:
    source = pd.DataFrame({"provider_period": [1], "period": [999], "game_id": [12]})
    assert normalize(source, {"period": "provider_period", "game_id": "game_id"}, ["period", "game_id"]).to_dict("records") == [{"period": 1, "game_id": "12"}]


def test_audit_flags_duplicates_disorder_scores_and_missing_games() -> None:
    events, schedule = basketball_frames()
    report = audit(events, schedule)
    assert report["structural_checks_passed"]
    assert report["possession_reconstruction_approved"] is False
    events.loc[2, "event_id"] = "b"
    events.loc[2, "sequence"] = 1
    events.loc[2, "home_score"] = 99
    issues = audit(events, schedule)["games"][0]["issues"]
    assert {"duplicate_events_or_sequence", "event_order", "invalid_or_decreasing_score", "final_score_mismatch"} <= set(issues)
    assert audit(events.iloc[:0], schedule)["missing_games"] == ["g"]


def synthetic_dataset(tmp_path: Path) -> dict:
    path = tmp_path / "raw.txt"
    path.write_text("synthetic verification only", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    data = {"classes": ["away", "home"], "feature_groups": {"basic": ["form"], "schedule": ["rest"]},
        "feature_definitions": {"form": "Prior verified results", "rest": "Prior rest days"},
        "snapshots": [{"path": "raw.txt", "sha256": digest, "source_url": "https://example.org/results",
                       "retrieved_at": "2026-10-30T00:00:00Z"}], "rows": []}
    for i in range(100):
        day = pd.Timestamp("2026-01-03", tz="UTC") + pd.Timedelta(days=i)
        provenance = {}
        for column in ["form", "rest"]:
            value = evidence()
            value.update(feature=column, definition=data["feature_definitions"][column], snapshot_sha256=digest)
            provenance[column] = value
        data["rows"].append({"game_id": str(i), "kickoff": (day + pd.Timedelta(hours=18)).isoformat(),
            "cutoff": day.isoformat(), "competition": "synthetic", "season": "2026", "target": i % 2,
            "target_available_at": (day + pd.Timedelta(hours=22)).isoformat(), "target_availability_status": "verified",
            "features": {"form": float(i % 3), "rest": float(i % 5)}, "provenance": provenance})
    return data


def test_runner_and_snapshot_integrity(tmp_path: Path) -> None:
    data = synthetic_dataset(tmp_path)
    logistic = candidates(42, 2)["logistic"]
    with patch("models.research_experiments.candidates", return_value={"logistic": logistic}):
        report = run(data, tmp_path, trees=2)
    assert report["production_changed"] is False
    output = report["competitions"]["synthetic"]
    assert output["splits"]["test"]["samples"] == 15
    experiment = output["experiments"]["basic+schedule/logistic"]
    assert len(experiment["walk_forward"]) == 3
    assert experiment["test"]["missing/basic"]["samples"] == 15
    assert "('synthetic', '2026')" in experiment["test"]["clean"]["by_competition_season"]
    altered = deepcopy(data)
    altered["rows"][0]["provenance"]["form"]["availability_status"] = "assumed"
    with pytest.raises(ValueError):
        validate_dataset(altered, tmp_path)
    (tmp_path / "raw.txt").write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        validate_dataset(data, tmp_path)


def test_stale_features_need_earlier_verified_snapshots(tmp_path: Path) -> None:
    data = synthetic_dataset(tmp_path)
    for row in data["rows"]:
        row["stale_features"] = row["features"].copy()
        row["stale_provenance"] = deepcopy(row["provenance"])
        for value in row["stale_provenance"].values():
            value["available_at"] = "2025-12-31T00:00:00Z"
            value["aggregation_cutoff"] = "2025-12-31T00:00:00Z"
    validate_dataset(data, tmp_path)
    data["rows"][0]["stale_provenance"]["form"]["available_at"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="earlier"):
        validate_dataset(data, tmp_path)


def test_research_cli_writes_report_and_refuses_overwrite(tmp_path: Path) -> None:
    source, output = tmp_path / "input.json", tmp_path / "report.json"
    source.write_text(json.dumps(synthetic_dataset(tmp_path)), encoding="utf-8")
    logistic = candidates(42, 2)["logistic"]
    args = ["research", "--input", str(source), "--output", str(output), "--trees", "2"]
    with patch("sys.argv", args), patch("models.research_experiments.candidates", return_value={"logistic": logistic}):
        main()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["input_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["competitions"]["synthetic"]["experiments"]["basic/logistic"]["stale_status"].startswith("unavailable")
    with patch("sys.argv", args), pytest.raises(SystemExit):
        main()


def test_soccer_evaluator_persists_pairs_and_aggregates_distribution_scores() -> None:
    from models.run_soccer_simulation import aggregate, evaluate
    from models.soccer_possessions import STAT_NAMES
    model = Mock()
    samples = np.zeros((100, 2, len(STAT_NAMES)), dtype=int)
    samples[:, 0, 0], samples[:, 1, 0] = 2, 1
    model.simulate.return_value = {"samples": samples}
    record = {"match": {"teamsData": {"1": {"side": "home"}, "2": {"side": "away"}}}}
    baseline = {"means": np.array([1.5, 1.0]), "teams": {}}
    with patch("models.run_soccer_simulation.load_match", return_value=record), patch("models.run_soccer_simulation.actual_stats", return_value=samples[0]):
        rows = evaluate(model, Path("unused"), [{"match_id": 1, "date": "2026-01-01"}], baseline, 100, 42)
    assert rows[0]["paired_final_scores"] == [[2, 1]] * 100
    summary = aggregate(rows)
    assert summary["score_distributions"]["margin"]["crps"] == 0
    assert summary["score_distributions"]["total"]["interval_coverage"]["0.8"] == 1


def test_installed_candidates_handle_feature_outage() -> None:
    from models.training_resources import training_threads
    X = pd.DataFrame({"form": np.arange(60, dtype=float), "rest": np.arange(60, dtype=float) % 3})
    y = np.arange(60) % 3
    missing = X.iloc[:4].copy()
    missing.loc[:, "rest"] = np.nan
    with training_threads(1):
        for estimator in candidates(42, 2).values():
            estimator.fit(X, y)
            probability = estimator.predict_proba(missing)
            assert probability.shape == (4, 3)
            assert np.isfinite(probability).all()
            np.testing.assert_allclose(probability.sum(axis=1), 1, atol=1e-6)
