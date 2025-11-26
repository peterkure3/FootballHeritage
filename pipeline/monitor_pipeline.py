"""Post-run monitoring script for the daily pipeline.

Checks recent logs and database freshness, exiting non-zero if issues are found.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, Dict, List, Tuple

import psycopg2

from config import DATABASE_URI

LOG_ERROR_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("IntegrityError", re.compile(r"psycopg2\.errors", re.IGNORECASE)),
    ("Traceback", re.compile(r"Traceback")),
    ("Critical", re.compile(r"CRITICAL")),
    ("ExplicitError", re.compile(r"\bERROR\b")),
)

LOG_WARNING_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("Warning", re.compile(r"\bWARNING\b")),
)

DB_FRESHNESS_TARGETS: Tuple[Tuple[str, str], ...] = (
    ("matches", "updated_at"),
    ("nba_games", "updated_at"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--loader-log",
        default=Path("logs") / "pipeline_loader.log",
        type=Path,
        help="Path to the loader log file",
    )
    parser.add_argument(
        "--sync-log",
        default=Path("sync_to_backend.log"),
        type=Path,
        help="Path to the backend sync log file",
    )
    parser.add_argument(
        "--max-log-lines",
        type=int,
        default=3000,
        help="Number of trailing log lines to scan",
    )
    parser.add_argument(
        "--max-age-minutes",
        type=int,
        default=180,
        help="Allowed staleness for DB timestamps",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("logs") / "monitor_report.txt",
        help="Destination file for the monitoring summary",
    )
    return parser.parse_args()


def tail_lines(path: Path, max_lines: int) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    buffer: Deque[str] = deque(maxlen=max_lines)
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            buffer.append(line.rstrip())
    return list(buffer)


def analyze_log(path: Path, max_lines: int) -> Dict[str, List[str]]:
    findings: Dict[str, List[str]] = {"errors": [], "warnings": []}

    try:
        lines = tail_lines(path, max_lines)
    except FileNotFoundError as exc:
        findings["errors"].append(str(exc))
        return findings

    for line in lines:
        normalized = line.strip()
        for label, pattern in LOG_ERROR_PATTERNS:
            if pattern.search(normalized):
                findings["errors"].append(f"{label}: {normalized}")
                break
        else:
            for label, pattern in LOG_WARNING_PATTERNS:
                if pattern.search(normalized):
                    findings["warnings"].append(f"{label}: {normalized}")
                    break

    return findings


def check_db_freshness(max_age_minutes: int) -> Dict[str, List[str]]:
    findings: Dict[str, List[str]] = {"errors": [], "warnings": []}
    deadline = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)

    with closing(psycopg2.connect(DATABASE_URI)) as conn:
        with conn.cursor() as cur:
            for table, column in DB_FRESHNESS_TARGETS:
                try:
                    cur.execute(f"SELECT MAX({column}) FROM {table}")
                    result = cur.fetchone()
                    latest = result[0] if result else None
                except Exception as exc:
                    findings["warnings"].append(
                        f"Could not check freshness for {table}.{column}: {exc}"
                    )
                    continue

                if latest is None:
                    findings["errors"].append(
                        f"Table {table} has no data for column {column}"
                    )
                    continue

                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)

                if latest < deadline:
                    findings["errors"].append(
                        f"Table {table} is stale (latest {latest.isoformat()})"
                    )

    return findings


def write_report(path: Path, summary: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary, encoding="utf-8")


def main() -> None:
    args = parse_args()
    overall_errors: List[str] = []
    overall_warnings: List[str] = []

    for log_label, log_path in ("Loader", args.loader_log), ("Backend", args.sync_log):
        findings = analyze_log(log_path, args.max_log_lines)
        overall_errors.extend(f"[{log_label}] {msg}" for msg in findings["errors"])
        overall_warnings.extend(f"[{log_label}] {msg}" for msg in findings["warnings"])

    db_findings = check_db_freshness(args.max_age_minutes)
    overall_errors.extend(db_findings["errors"])
    overall_warnings.extend(db_findings["warnings"])

    status = "PASS" if not overall_errors else "FAIL"
    summary_lines = [
        f"Pipeline monitor status: {status}",
        f"Checked at: {datetime.now(timezone.utc).isoformat()}",
        f"Loader log: {args.loader_log}",
        f"Backend log: {args.sync_log}",
        "",
    ]

    if overall_errors:
        summary_lines.append("Errors:")
        summary_lines.extend(f"  - {msg}" for msg in overall_errors)
        summary_lines.append("")

    if overall_warnings:
        summary_lines.append("Warnings:")
        summary_lines.extend(f"  - {msg}" for msg in overall_warnings)
        summary_lines.append("")

    if not overall_errors and not overall_warnings:
        summary_lines.append("No issues detected.")

    summary_text = "\n".join(summary_lines)
    print(summary_text)

    if args.report:
        write_report(args.report, summary_text)

    sys.exit(0 if not overall_errors else 1)


+if __name__ == "__main__":
+    main()
