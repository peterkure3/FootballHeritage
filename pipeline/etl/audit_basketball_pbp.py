"""Snapshot and audit explicit basketball PBP/schedule assets before possessions.

The adapter mapping is explicit: canonical -> provider column. Canonical events:
game_id, event_id, sequence, period, clock_seconds, home_score, away_score.
Canonical schedules: game_id, date, completed, home_score, away_score.
Never sort before auditing: sorting would hide source ordering defects.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests


def snapshot(url: str, directory: Path, name: str) -> tuple[Path, dict]:
    response = requests.get(url, timeout=(10, 120))
    response.raise_for_status()
    path = directory / name
    with path.open("xb") as stream:
        stream.write(response.content)
    return path, {"path": name, "source_url": url, "resolved_url": response.url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(response.content).hexdigest(), "bytes": len(response.content),
        "last_modified": response.headers.get("Last-Modified"), "etag": response.headers.get("ETag")}


def normalize(frame: pd.DataFrame, mapping: dict, columns: list[str]) -> pd.DataFrame:
    if set(mapping) != set(columns) or len(set(mapping.values())) != len(mapping):
        raise ValueError("Mapping must cover every canonical field exactly once")
    # Select first: provider frames may already contain a different column named
    # period or clock_seconds, which must not collide with mapped canonical names.
    result = frame[list(mapping.values())].rename(columns={value: key for key, value in mapping.items()})[columns].copy()
    for name in ["game_id", "event_id"]:
        if name in result:
            if result[name].isna().any():
                raise ValueError(f"Missing {name}")
            result[name] = result[name].astype(str).str.strip()
            if result[name].eq("").any():
                raise ValueError(f"Empty {name}")
    return result


def audit(events: pd.DataFrame, schedule: pd.DataFrame) -> dict:
    issues = []
    if schedule.game_id.duplicated().any():
        raise ValueError("Schedule game IDs are not unique")
    if schedule.game_id.isna().any() or events.game_id.isna().any():
        raise ValueError("Missing game IDs")
    if not schedule.completed.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise ValueError("Schedule completed flags must be booleans")
    expected = schedule[schedule.completed]
    expected_ids, event_ids = set(expected.game_id), set(events.game_id)
    games = []
    for game_id, block in events.groupby("game_id", sort=False):
        errors = []
        numeric = block[["sequence", "period", "clock_seconds", "home_score", "away_score"]].apply(pd.to_numeric, errors="coerce")
        if not np.isfinite(numeric.to_numpy()).all():
            errors.append("missing_or_nonfinite_event_fields")
        else:
            if block.event_id.duplicated().any() or numeric.sequence.duplicated().any():
                errors.append("duplicate_events_or_sequence")
            if (numeric.sequence.diff().dropna() <= 0).any() or (numeric.period.diff().dropna() < 0).any():
                errors.append("event_order")
            if ((numeric.period < 1) | (numeric.period != np.floor(numeric.period))).any():
                errors.append("invalid_period")
            if (numeric.sequence != np.floor(numeric.sequence)).any():
                errors.append("invalid_sequence")
            for _, period in numeric.groupby("period", sort=False):
                limit = 720 if period.period.iloc[0] <= 4 else 300
                if ((period.clock_seconds < 0) | (period.clock_seconds > limit)).any() or (period.clock_seconds.diff().dropna() > 0).any():
                    errors.append("invalid_or_increasing_clock")
            scores = numeric[["home_score", "away_score"]]
            if (scores < 0).any().any() or (scores != np.floor(scores)).any().any() or (scores.diff().dropna() < 0).any().any():
                errors.append("invalid_or_decreasing_score")
            if numeric.period.iloc[-1] < 4 or numeric.clock_seconds.iloc[-1] != 0:
                errors.append("missing_terminal_event")
            if numeric.period.iloc[0] != 1 or numeric.clock_seconds.iloc[0] != 720:
                errors.append("missing_opening_event")
            if game_id in expected_ids:
                final = expected.set_index("game_id").loc[game_id, ["home_score", "away_score"]].to_numpy(dtype=float)
                if not np.isfinite(final).all() or not np.array_equal(scores.iloc[-1].to_numpy(), final):
                    errors.append("final_score_mismatch")
        games.append({"game_id": game_id, "events": len(block), "issues": sorted(set(errors))})
    missing = sorted(expected_ids - event_ids)
    unexpected = sorted(event_ids - expected_ids)
    if missing:
        issues.append("missing_completed_games")
    if unexpected:
        issues.append("events_without_completed_schedule_game")
    dates = pd.to_datetime(expected.date, utc=True, errors="raise")
    return {"scheduled_completed_games": len(expected), "event_games": len(event_ids), "events": len(events),
        "first_scheduled_game": dates.min().isoformat() if len(dates) else None,
        "last_scheduled_game": dates.max().isoformat() if len(dates) else None,
        "missing_games": missing, "unexpected_games": unexpected, "issues": issues, "games": games,
        "structural_checks_passed": bool(len(expected) and len(events) and not issues and not any(game["issues"] for game in games)),
        "possession_reconstruction_approved": False,
        "limitations": ["NBA clock rules only: four 12-minute quarters and 5-minute overtime.",
            "Coverage is relative to the supplied schedule snapshot, not independently established league completeness.",
            "Score corrections are flagged for manual review rather than silently repaired.",
            "Structural checks do not prove event semantics, lineup validity, or possession boundaries."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-url", required=True)
    parser.add_argument("--schedule-url", required=True)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    captures = []
    # Persist metadata after each download even if decoding or a later request fails.
    try:
        events_path, capture = snapshot(args.events_url, args.output_dir, "events.parquet")
        captures.append(capture)
        schedule_path, capture = snapshot(args.schedule_url, args.output_dir, "schedule.parquet")
        captures.append(capture)
        events = normalize(pd.read_parquet(events_path), mapping["events"],
            ["game_id", "event_id", "sequence", "period", "clock_seconds", "home_score", "away_score"])
        schedule = normalize(pd.read_parquet(schedule_path), mapping["schedule"],
            ["game_id", "date", "completed", "home_score", "away_score"])
        report = audit(events, schedule)
        (args.output_dir / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    finally:
        manifest = {"captures": captures, "mapping": mapping,
            "mapping_sha256": hashlib.sha256(args.mapping.read_bytes()).hexdigest()}
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
