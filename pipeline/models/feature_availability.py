"""Executable prediction-time provenance contract for research datasets.

Retrieval time is deliberately distinct from historical availability. Unknown or
assumed availability cannot pass this contract, even if a backtest scores well.
"""
from dataclasses import dataclass

import pandas as pd


def utc_timestamp(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        raise ValueError("An explicit timezone-aware timestamp is required")
    return timestamp.tz_convert("UTC")


@dataclass(frozen=True)
class ForecastContract:
    game_id: str
    kickoff: object
    cutoff: object
    mode: str = "prematch"

    def validate(self) -> None:
        cutoff, kickoff = utc_timestamp(self.cutoff), utc_timestamp(self.kickoff)
        if self.mode not in {"prematch", "live"}:
            raise ValueError("Forecast mode must be prematch or live")
        if not self.game_id or (self.mode == "prematch" and cutoff >= kickoff):
            raise ValueError("Prematch cutoff must precede kickoff and game ID is required")
        if self.mode == "live" and cutoff < kickoff:
            raise ValueError("Live cutoff cannot precede kickoff")


def validate_feature(contract: ForecastContract, evidence: dict) -> None:
    """Validate one materialized feature and every declared rolling dependency."""
    contract.validate()
    cutoff = utc_timestamp(contract.cutoff)
    for key in ["feature", "definition", "source_url", "snapshot_sha256"]:
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            raise ValueError(f"Missing feature provenance: {key}")
    digest = evidence["snapshot_sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid snapshot SHA256")
    if evidence.get("availability_status") != "verified":
        raise ValueError("Unknown or assumed historical availability is not verified")
    if utc_timestamp(evidence.get("available_at")) > cutoff:
        raise ValueError("Feature was unavailable at the forecast cutoff")
    if utc_timestamp(evidence.get("aggregation_cutoff")) > cutoff:
        raise ValueError("Aggregation extends beyond forecast cutoff")
    if evidence.get("kind") not in {"snapshot", "rolling"}:
        raise ValueError("Feature kind must be snapshot or rolling")
    if evidence["kind"] == "rolling":
        if "dependencies" not in evidence or not isinstance(evidence["dependencies"], list):
            raise ValueError("Rolling features require explicit dependencies (empty for cold starts)")
        for item in evidence["dependencies"]:
            if str(item["game_id"]) == str(contract.game_id):
                raise ValueError("Rolling features cannot include the current game")
            if item.get("availability_status") != "verified":
                raise ValueError("Rolling dependency availability is unknown or assumed")
            if utc_timestamp(item["kickoff"]) >= cutoff:
                raise ValueError("Rolling features cannot include future games")
            if utc_timestamp(item["available_at"]) <= utc_timestamp(item["kickoff"]):
                raise ValueError("Final results cannot be available before or at kickoff")
            if utc_timestamp(item["available_at"]) > utc_timestamp(evidence["aggregation_cutoff"]):
                raise ValueError("Rolling result was unavailable at aggregation time")
