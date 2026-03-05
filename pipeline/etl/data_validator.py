"""
Data Validation Layer

Validates data freshness and accuracy before running predictions.
Catches stale, missing, or inconsistent data that could lead to incorrect predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    message: str
    severity: str  # "error", "warning", "info"
    details: Optional[Dict] = None


@dataclass
class DataQualityReport:
    """Aggregated data quality report."""
    timestamp: datetime
    overall_passed: bool
    checks: List[ValidationResult]
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_passed": self.overall_passed,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "message": c.message,
                    "severity": c.severity,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "recommendations": self.recommendations,
        }


class DataValidator:
    """Validates data quality before running predictions."""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or create_engine(HERITAGE_DATABASE_URI)
        self.max_data_age_hours = 24  # Data older than this is considered stale
        self.min_odds_per_event = 2   # Minimum odds offers per event
        self.min_events_for_prediction = 5  # Minimum events needed
    
    def validate_all(self) -> DataQualityReport:
        """Run all validation checks and return a report."""
        checks = []
        recommendations = []
        
        # Run all checks
        checks.append(self._check_data_freshness())
        checks.append(self._check_odds_coverage())
        checks.append(self._check_event_data_completeness())
        checks.append(self._check_standings_accuracy())
        checks.append(self._check_duplicate_data())
        checks.append(self._check_odds_reasonableness())
        
        # Determine overall pass/fail
        errors = [c for c in checks if not c.passed and c.severity == "error"]
        warnings = [c for c in checks if not c.passed and c.severity == "warning"]
        
        overall_passed = len(errors) == 0
        
        # Generate recommendations
        if errors:
            recommendations.append("Critical data issues detected. Fix before running predictions.")
        if warnings:
            recommendations.append("Some data quality warnings. Results may be less accurate.")
        
        for check in checks:
            if not check.passed:
                if "stale" in check.message.lower():
                    recommendations.append("Run data refresh: python -m etl.fetch_raw_data")
                if "missing" in check.message.lower():
                    recommendations.append("Check data ingestion pipeline for errors")
                if "duplicate" in check.message.lower():
                    recommendations.append("Run deduplication: clean up duplicate records")
        
        return DataQualityReport(
            timestamp=datetime.utcnow(),
            overall_passed=overall_passed,
            checks=checks,
            recommendations=list(set(recommendations)),  # dedupe
        )
    
    def _check_data_freshness(self) -> ValidationResult:
        """Check if odds data is fresh enough."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    MAX(source_updated_at) as latest_update,
                    COUNT(*) as total_offers,
                    COUNT(CASE WHEN source_updated_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_offers
                FROM odds_offers
                WHERE source_updated_at IS NOT NULL
            """)).fetchone()
            
            if result is None or result[0] is None:
                return ValidationResult(
                    check_name="data_freshness",
                    passed=False,
                    message="No odds data found with timestamps",
                    severity="error",
                )
            
            latest_update = result[0]
            total_offers = result[1]
            recent_offers = result[2]
            
            age_hours = (datetime.utcnow() - latest_update.replace(tzinfo=None)).total_seconds() / 3600
            recent_pct = (recent_offers / total_offers * 100) if total_offers > 0 else 0
            
            if age_hours > self.max_data_age_hours:
                return ValidationResult(
                    check_name="data_freshness",
                    passed=False,
                    message=f"Data is stale. Latest update: {age_hours:.1f} hours ago",
                    severity="error",
                    details={"age_hours": age_hours, "latest_update": latest_update.isoformat()},
                )
            
            if recent_pct < 50:
                return ValidationResult(
                    check_name="data_freshness",
                    passed=False,
                    message=f"Only {recent_pct:.1f}% of offers updated in last 24h",
                    severity="warning",
                    details={"recent_pct": recent_pct, "recent_offers": recent_offers},
                )
            
            return ValidationResult(
                check_name="data_freshness",
                passed=True,
                message=f"Data is fresh. Latest update: {age_hours:.1f} hours ago",
                severity="info",
                details={"age_hours": age_hours, "recent_pct": recent_pct},
            )
    
    def _check_odds_coverage(self) -> ValidationResult:
        """Check if we have sufficient odds coverage per event."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT event_id) as total_events,
                    COUNT(DISTINCT CASE WHEN offer_count >= 2 THEN event_id END) as events_with_coverage
                FROM (
                    SELECT event_id, COUNT(*) as offer_count
                    FROM odds_offers
                    WHERE event_id IS NOT NULL
                    GROUP BY event_id
                ) sub
            """)).fetchone()
            
            if result is None:
                return ValidationResult(
                    check_name="odds_coverage",
                    passed=False,
                    message="Could not check odds coverage",
                    severity="error",
                )
            
            total_events = result[0] or 0
            events_with_coverage = result[1] or 0
            
            if total_events == 0:
                return ValidationResult(
                    check_name="odds_coverage",
                    passed=False,
                    message="No events with odds data",
                    severity="error",
                )
            
            coverage_pct = events_with_coverage / total_events * 100
            
            if coverage_pct < 80:
                return ValidationResult(
                    check_name="odds_coverage",
                    passed=False,
                    message=f"Only {coverage_pct:.1f}% of events have sufficient odds coverage",
                    severity="warning",
                    details={"coverage_pct": coverage_pct, "total_events": total_events},
                )
            
            return ValidationResult(
                check_name="odds_coverage",
                passed=True,
                message=f"{coverage_pct:.1f}% of events have sufficient odds coverage",
                severity="info",
                details={"coverage_pct": coverage_pct, "total_events": total_events},
            )
    
    def _check_event_data_completeness(self) -> ValidationResult:
        """Check if events have complete data (home/away teams, dates)."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN home_team IS NULL OR home_team = '' THEN 1 END) as missing_home,
                    COUNT(CASE WHEN away_team IS NULL OR away_team = '' THEN 1 END) as missing_away,
                    COUNT(CASE WHEN event_date IS NULL THEN 1 END) as missing_date,
                    COUNT(CASE WHEN league IS NULL OR league = '' THEN 1 END) as missing_league
                FROM events
            """)).fetchone()
            
            if result is None or result[0] == 0:
                return ValidationResult(
                    check_name="event_completeness",
                    passed=False,
                    message="No events found in database",
                    severity="error",
                )
            
            total = result[0]
            missing_home = result[1]
            missing_away = result[2]
            missing_date = result[3]
            missing_league = result[4]
            
            issues = []
            if missing_home > 0:
                issues.append(f"{missing_home} missing home team")
            if missing_away > 0:
                issues.append(f"{missing_away} missing away team")
            if missing_date > 0:
                issues.append(f"{missing_date} missing date")
            if missing_league > 0:
                issues.append(f"{missing_league} missing league")
            
            if issues:
                return ValidationResult(
                    check_name="event_completeness",
                    passed=False,
                    message=f"Incomplete event data: {', '.join(issues)}",
                    severity="warning",
                    details={
                        "total": total,
                        "missing_home": missing_home,
                        "missing_away": missing_away,
                        "missing_date": missing_date,
                        "missing_league": missing_league,
                    },
                )
            
            return ValidationResult(
                check_name="event_completeness",
                passed=True,
                message=f"All {total} events have complete data",
                severity="info",
            )
    
    def _check_standings_accuracy(self) -> ValidationResult:
        """Check if standings data exists and is recent."""
        with self.engine.connect() as conn:
            # Check if standings table exists and has data
            try:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        MAX(updated_at) as latest_update
                    FROM standings
                """)).fetchone()
            except Exception:
                return ValidationResult(
                    check_name="standings_accuracy",
                    passed=True,  # Not an error if table doesn't exist
                    message="Standings table not found (optional)",
                    severity="info",
                )
            
            if result is None or result[0] == 0:
                return ValidationResult(
                    check_name="standings_accuracy",
                    passed=False,
                    message="No standings data found",
                    severity="warning",
                )
            
            total = result[0]
            latest_update = result[1]
            
            if latest_update:
                age_hours = (datetime.utcnow() - latest_update.replace(tzinfo=None)).total_seconds() / 3600
                if age_hours > 48:
                    return ValidationResult(
                        check_name="standings_accuracy",
                        passed=False,
                        message=f"Standings data is {age_hours:.0f} hours old",
                        severity="warning",
                        details={"age_hours": age_hours},
                    )
            
            return ValidationResult(
                check_name="standings_accuracy",
                passed=True,
                message=f"Standings data present ({total} records)",
                severity="info",
            )
    
    def _check_duplicate_data(self) -> ValidationResult:
        """Check for duplicate odds offers."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as dupe_count
                FROM (
                    SELECT event_id, book_key, market, selection, line, COUNT(*) as cnt
                    FROM odds_offers
                    WHERE event_id IS NOT NULL
                    GROUP BY event_id, book_key, market, selection, line
                    HAVING COUNT(*) > 1
                ) sub
            """)).fetchone()
            
            dupe_count = result[0] if result else 0
            
            if dupe_count > 100:
                return ValidationResult(
                    check_name="duplicate_data",
                    passed=False,
                    message=f"Found {dupe_count} duplicate offer groups",
                    severity="warning",
                    details={"duplicate_groups": dupe_count},
                )
            
            return ValidationResult(
                check_name="duplicate_data",
                passed=True,
                message="No significant duplicate data detected",
                severity="info",
            )
    
    def _check_odds_reasonableness(self) -> ValidationResult:
        """Check if odds values are within reasonable bounds."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN odds_decimal < 1.01 THEN 1 END) as too_low,
                    COUNT(CASE WHEN odds_decimal > 1000 THEN 1 END) as too_high,
                    MIN(odds_decimal) as min_odds,
                    MAX(odds_decimal) as max_odds,
                    AVG(odds_decimal) as avg_odds
                FROM odds_offers
                WHERE odds_decimal IS NOT NULL
            """)).fetchone()
            
            if result is None or result[0] == 0:
                return ValidationResult(
                    check_name="odds_reasonableness",
                    passed=False,
                    message="No odds data to validate",
                    severity="error",
                )
            
            total = result[0]
            too_low = result[1]
            too_high = result[2]
            
            unreasonable_pct = (too_low + too_high) / total * 100
            
            if unreasonable_pct > 5:
                return ValidationResult(
                    check_name="odds_reasonableness",
                    passed=False,
                    message=f"{unreasonable_pct:.1f}% of odds are outside reasonable bounds",
                    severity="warning",
                    details={
                        "too_low": too_low,
                        "too_high": too_high,
                        "min_odds": float(result[3]) if result[3] else None,
                        "max_odds": float(result[4]) if result[4] else None,
                    },
                )
            
            return ValidationResult(
                check_name="odds_reasonableness",
                passed=True,
                message="Odds values are within reasonable bounds",
                severity="info",
                details={
                    "min_odds": float(result[3]) if result[3] else None,
                    "max_odds": float(result[4]) if result[4] else None,
                    "avg_odds": float(result[5]) if result[5] else None,
                },
            )


def validate_data() -> DataQualityReport:
    """Run data validation and return report."""
    validator = DataValidator()
    report = validator.validate_all()
    
    # Log results
    logger.info("Data validation completed: %s", "PASSED" if report.overall_passed else "FAILED")
    for check in report.checks:
        level = logger.info if check.passed else (logger.error if check.severity == "error" else logger.warning)
        level("[%s] %s: %s", check.severity.upper(), check.check_name, check.message)
    
    if report.recommendations:
        logger.info("Recommendations:")
        for rec in report.recommendations:
            logger.info("  - %s", rec)
    
    return report


def main():
    """Run validation and print report."""
    report = validate_data()
    import json
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.overall_passed else 1


if __name__ == "__main__":
    exit(main())
