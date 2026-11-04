"""Capture exact public release metadata and a small current-season NBA pilot."""
import json
from pathlib import Path
import sys

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from etl.audit_basketball_pbp import snapshot


def main() -> None:
    output = ROOT / "pipeline/data/raw/historical/nba/pbp_research_20261030"
    output.mkdir(parents=True, exist_ok=False)
    metadata, captures = {}, []
    for kind, tag, filename in [("events", "espn_nba_pbp", "play_by_play_2027.parquet"),
                                ("schedule", "espn_nba_schedules", "nba_schedule_2027.parquet")]:
        path, capture = snapshot(f"https://api.github.com/repos/sportsdataverse/sportsdataverse-data/releases/tags/{tag}", output, f"{kind}-release.json")
        captures.append(capture)
        assets = json.loads(path.read_text(encoding="utf-8"))["assets"]
        metadata[kind] = [{key: asset[key] for key in ["name", "size", "updated_at", "browser_download_url"]} for asset in assets if "2027" in asset["name"]]
        (output / "manifest.json").write_text(json.dumps({"captures": captures, "assets": metadata}, indent=2), encoding="utf-8")
        asset = next((item for item in assets if item["name"] == filename), None)
        if asset is None:
            print(kind, metadata[kind])
            continue
        data_path, capture = snapshot(asset["browser_download_url"], output, f"{kind}.parquet")
        capture["release_asset_updated_at"] = asset["updated_at"]
        captures.append(capture)
        (output / "manifest.json").write_text(json.dumps({"captures": captures, "assets": metadata}, indent=2), encoding="utf-8")
        frame = pd.read_parquet(data_path)
        print(kind, len(frame), frame.columns.tolist())
        print(frame.head(2).to_json(orient="records"))


if __name__ == "__main__":
    main()
