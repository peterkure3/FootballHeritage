"""Validate a licensed historical export before adding it to the training corpus."""

import argparse
from pathlib import Path
import re
import sys

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from config import HISTORICAL_CSV_DIR
from models.data import canonical_matches


def import_historical(source: Path, competition: str, season: str,
                      provider: str, destination_dir: Path = HISTORICAL_CSV_DIR) -> Path:
    if not re.fullmatch(r"\d{4}", season):
        raise ValueError("Season must be four digits, for example 2425")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", competition).strip("_")
    if not slug or not provider.strip():
        raise ValueError("Competition and provider must be nonempty")
    if re.search(r"sample|synthetic", source.stem, re.IGNORECASE):
        raise ValueError("Sample and synthetic files cannot enter the training corpus")
    raw = pd.read_csv(source)
    if "data_source" in raw and raw.data_source.fillna("").str.contains("sample|synthetic", case=False).any():
        raise ValueError("Sample and synthetic records cannot enter the training corpus")
    raw["competition"] = competition
    raw["data_source"] = f"licensed_import:{provider}"
    normalized = canonical_matches([raw])
    if len(normalized) != len(raw) or normalized.result.isna().any():
        raise ValueError("Export contains duplicate, invalid, or unfinished fixtures")
    normalized = normalized.drop(columns=["match_id"], errors="ignore")
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"licensed_{slug}_{season}.csv"
    # Exclusive creation protects an existing import from accidental replacement.
    with destination.open("x", encoding="utf-8", newline="") as stream:
        normalized.to_csv(stream, index=False)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--provider", required=True)
    args = parser.parse_args()
    print(import_historical(args.input, args.competition, args.season, args.provider))


if __name__ == "__main__":
    main()
