"""Reproduce the audit from the captured current-season assets, without network."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from etl.audit_basketball_pbp import audit, normalize


def main() -> None:
    source = ROOT / "pipeline/data/raw/historical/nba/pbp_research_20261030"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    for capture in manifest["captures"]:
        if hashlib.sha256((source / capture["path"]).read_bytes()).hexdigest() != capture["sha256"]:
            raise ValueError("Snapshot hash mismatch")
    raw_events, raw_schedule = pd.read_parquet(source / "events.parquet"), pd.read_parquet(source / "schedule.parquet")
    mapping = {"events": {"game_id": "game_id", "event_id": "id", "sequence": "game_play_number", "period": "period_number",
                          "clock_seconds": "start_quarter_seconds_remaining", "home_score": "home_score", "away_score": "away_score"},
               "schedule": {"game_id": "game_id", "date": "date", "completed": "status_type_completed", "home_score": "home_score", "away_score": "away_score"}}
    report = audit(normalize(raw_events, mapping["events"], list(mapping["events"])),
                   normalize(raw_schedule, mapping["schedule"], list(mapping["schedule"])))
    provider_mapping = dict(mapping["events"], sequence="sequence_number")
    provider_audit = audit(normalize(raw_events, provider_mapping, list(provider_mapping)),
                           normalize(raw_schedule, mapping["schedule"], list(mapping["schedule"])))
    report["provider_sequence_diagnostic"] = {
        "column": "sequence_number", "issue_counts": dict(Counter(issue for game in provider_audit["games"] for issue in game["issues"])),
        "note": "No rows sorted or repaired. Main audit uses game_play_number; raw sequence_number is retained and its regressions require semantic review."}
    report.update(input_manifest=manifest, mapping=mapping, input_directory=str(source.relative_to(ROOT)),
        issue_counts=dict(Counter(issue for game in report["games"] for issue in game["issues"])),
        season_type_counts={str(k): int(v) for k, v in raw_events.season_type.value_counts().items()},
        team_ids={"home": sorted(raw_events.home_team_id.dropna().astype(str).unique().tolist()),
                  "away": sorted(raw_events.away_team_id.dropna().astype(str).unique().tolist())},
        identity_namespace="sportsdataverse:espn:nba; provider IDs retained as strings; player identity crosswalk not validated",
        event_dates={"min": str(raw_events.game_date_time.min()), "max": str(raw_events.game_date_time.max())},
        provider_score_sources={str(k): int(v) for k, v in raw_events.score_source.value_counts(dropna=False).items()})
    output = ROOT / "stages/03-build/output/nba-pbp-audit-20261030.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["scheduled_completed_games", "event_games", "events", "missing_games", "unexpected_games", "issue_counts", "structural_checks_passed", "possession_reconstruction_approved"]}, indent=2))


if __name__ == "__main__":
    main()
