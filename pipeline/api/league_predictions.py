"""Read generated league forecasts without loading pickle artifacts in API requests."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from config import PROCESSED_DATA_DIR


def load_predictions(path: Path = PROCESSED_DATA_DIR/'league_predictions.json') -> dict:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('schema_version') != 1:
            return {}
        rows = payload['predictions']
        if len({row['match_id'] for row in rows}) != len(rows):
            return {}
        return {row['match_id']: row for row in rows}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def fixture_prediction(row, forecasts: dict, now: datetime) -> dict | None:
    candidate = forecasts.get(row['match_id'])
    if candidate is None:
        return None
    try:
        if any(candidate[key] != row[key] for key in ['competition', 'home_team', 'away_team']):
            return None
        kickoff = datetime.fromisoformat(candidate['kickoff'])
        generated = datetime.fromisoformat(candidate['generated_at'])
        trained = datetime.fromisoformat(candidate['trained_at'])
        cutoff = datetime.fromisoformat(candidate['feature_cutoff'])
        if kickoff != row['date'].replace(tzinfo=timezone.utc) or not trained <= cutoff <= generated <= now < kickoff:
            return None
        probabilities = candidate['probabilities']
        if set(probabilities) != {'home_win', 'draw', 'away_win'}:
            return None
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities.values()):
            return None
        if abs(sum(probabilities.values()) - 1) >= .000001 or candidate['winner'] not in probabilities:
            return None
        return {**candidate, 'status': 'current' if (now-generated).total_seconds() <= 86400 else 'stale', 'active': False}
    except (ValueError, KeyError, TypeError):
        return None
