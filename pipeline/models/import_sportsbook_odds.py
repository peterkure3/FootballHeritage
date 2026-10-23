"""Import captured prematch prices for later joins to completed training fixtures."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from config import PROCESSED_DATA_DIR
from etl.utils import load_json_object, save_json
from models.data import match_odds_to_fixtures

SPORTSBOOK_ODDS_DIR = PROCESSED_DATA_DIR / "sportsbook_odds"


def normalize_snapshots(records: list[dict]) -> pd.DataFrame:
    """Fail the import on malformed observations rather than inventing values."""
    rows, identities = [], set()
    for record in records:
        identity = record["snapshot_id"]
        if not identity or identity in identities:
            raise ValueError("Duplicate or missing snapshot ID")
        identities.add(identity)
        if (record.get("schema_version") != "1.0" or record.get("sport") != "football"
                or record.get("market") != "h2h" or record.get("period") != "FULL_TIME_90_MIN"
                or record.get("settlement_rule") != "REGULATION_TIME"
                or record.get("is_live") is not False or record.get("event_status") != "SCHEDULED"
                or record.get("market_status") not in {"OPEN", "UNKNOWN"}):
            raise ValueError("Expected scheduled prematch regulation-time football prices")
        observed = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
        kickoff = datetime.fromisoformat(record["commence_time"].replace("Z", "+00:00"))
        if observed.tzinfo is None or kickoff.tzinfo is None or observed >= kickoff:
            raise ValueError("Observation must precede kickoff and include timezone")
        prices = {}
        for outcome in record["outcomes"]:
            selection = outcome["selection"]
            price = float(outcome["odds_decimal"])
            if selection in prices or outcome.get("status") not in {"OPEN", "UNKNOWN"} or not math.isfinite(price) or price <= 1:
                raise ValueError("Invalid, duplicate or suspended selection")
            prices[selection] = price
        if set(prices) != {"HOME", "DRAW", "AWAY"}:
            raise ValueError("Three complete home/draw/away prices are required")
        for field in ["provider", "collection_route", "bookmaker", "provider_event_id", "home_team", "away_team", "raw_capture_ref"]:
            if not record.get(field):
                raise ValueError(f"Missing {field}")
        rows.append({key: record.get(key) for key in ["snapshot_id", "provider", "collection_route", "bookmaker",
            "provider_event_id", "provider_market_id", "provider_competition_id", "competition", "country",
            "home_team", "away_team", "commence_time", "observed_at", "source_updated_at", "source_url",
            "raw_capture_ref", "scrape_run_id", "market_status", "region", "canonical_home_team", "canonical_away_team"]} | {
                # Training joins use actual observation time, never a provider's update time.
                "updated_at": observed.isoformat(), "home_win": prices["HOME"], "draw": prices["DRAW"], "away_win": prices["AWAY"]})
    if not rows:
        raise ValueError("No observations to import")
    return pd.DataFrame(rows)


def import_snapshots(source: Path, destination: Path = SPORTSBOOK_ODDS_DIR) -> dict:
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    frame = normalize_snapshots([json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()])
    directory = destination / digest
    manifest_file = directory / "manifest.json"
    if manifest_file.exists():
        manifest = load_json_object(manifest_file)
        if hashlib.sha256((directory / "odds.parquet").read_bytes()).hexdigest() != manifest["parquet_sha256"]:
            raise ValueError("Imported odds checksum mismatch")
        return manifest | {"already_imported": True}
    directory.mkdir(parents=True, exist_ok=False)
    parquet = directory / "odds.parquet"
    frame.to_parquet(parquet, index=False)
    # The manifest is the commit marker; persist its data before publishing it.
    with parquet.open('r+b') as stream:
        os.fsync(stream.fileno())
    manifest = {"schema_version": "1.0", "source": str(source.resolve()), "source_sha256": digest,
        "parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(), "snapshots": len(frame),
        "bookmakers": frame.bookmaker.nunique(), "by_bookmaker": frame.bookmaker.value_counts().to_dict(),
        "imported_at": datetime.now(timezone.utc).isoformat(), "odds_file": str(parquet.resolve()),
        "requires_final_results": True, "join_policy": "unique_team_pair_and_exact_utc_kickoff",
        "timestamp_policy": "observed_at_before_fixture_kickoff"}
    save_json(manifest, manifest_file)
    return manifest


def load_imported_odds(directory: Path = SPORTSBOOK_ODDS_DIR) -> pd.DataFrame:
    frames = []
    for path in sorted(directory.glob("*/manifest.json")):
        manifest = load_json_object(path)
        parquet = path.parent / "odds.parquet"
        if hashlib.sha256(parquet.read_bytes()).hexdigest() != manifest["parquet_sha256"]:
            raise ValueError(f"Imported odds checksum mismatch: {path.parent.name}")
        frames.append(pd.read_parquet(parquet))
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    if 'canonical_home_team' in merged:
        merged = merged.assign(_mapped=merged.canonical_home_team.notna()).sort_values('_mapped', ascending=False).drop(columns='_mapped')
    return merged.drop_duplicates('snapshot_id')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    report = import_snapshots(args.input)
    from models.train_model_v2 import load_training_data
    fixtures = load_training_data()
    frame = pd.read_parquet(report["odds_file"])
    joined = match_odds_to_fixtures(fixtures[fixtures.result.notna()], frame, exact_kickoff=True)
    report.update(training_matched_snapshots=len(joined), pending_snapshots=len(frame) - len(joined))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
