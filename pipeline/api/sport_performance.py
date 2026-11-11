"""Read-only NBA/NCAAB evaluation of retained, genuinely pregame forecasts."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from api.betting_intel import SPORTS, timestamp
from config import PROCESSED_DATA_DIR, RAW_DATA_DIR

ARCHIVE = PROCESSED_DATA_DIR / 'betting_intel' / 'forecast_archive'
SUPPORTED = {'nba', 'ncaab'}


def retain(payload: dict, root: Path = ARCHIVE, recorded_at: datetime | None = None) -> None:
    """Called by the producer, never by HTTP reads. Capture time is never backdated."""
    recorded_at = recorded_at or datetime.now(timezone.utc)
    fixtures = [row for row in payload['fixtures'] if row.get('sport') in SUPPORTED
                and row.get('prediction') and timestamp(row.get('kickoff'))
                and recorded_at < timestamp(row['kickoff'])]
    if not fixtures:
        return
    document = {'schema_version': 1, 'recorded_at': recorded_at.isoformat(),
                'fixtures': [{key: row[key] for key in ('fixture_id', 'sport', 'home_team', 'away_team',
                             'kickoff', 'settlement_rule', 'prediction')} for row in fixtures]}
    data = json.dumps(document, sort_keys=True, allow_nan=False,
                      default=lambda value: value.isoformat() if isinstance(value, datetime) else float(value)).encode()
    root.mkdir(parents=True, exist_ok=True)
    path = root / (hashlib.sha256(data).hexdigest() + '.json')
    if not path.exists():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=root, suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                stream.write(data)
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)


def read_forecasts(sport: str, root: Path = ARCHIVE) -> list[dict]:
    rows = []
    for path in sorted(root.glob('*.json')):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != path.stem:
            raise ValueError('Retained forecast checksum mismatch')
        payload = json.loads(data)
        if payload['schema_version'] != 1:
            raise ValueError('Unsupported forecast archive')
        for fixture in payload['fixtures']:
            if fixture.get('sport') == sport:
                rows.append({**fixture, 'recorded_at': payload['recorded_at'], 'source_sha256': path.stem})
    if sport == 'nba':
        # Import existing prospective research trials without recomputing forecasts.
        for path in sorted((PROCESSED_DATA_DIR / 'nba_model_shadow').glob('*/trial.json')):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != path.with_suffix('.sha256').read_text().strip():
                raise ValueError('NBA frozen trial checksum mismatch')
            trial = json.loads(data)
            if trial['status'] != 'prospective_NBA_model_shadow' or trial['policy']['settlement'] != 'INCLUDING_OVERTIME':
                raise ValueError('Unsupported NBA trial')
            for fixture in trial['fixtures']:
                for arm, values in fixture['probabilities'].items():
                    probabilities = dict(zip(trial['classes'], values, strict=True))
                    rows.append({'fixture_id': 'nba-trial:' + fixture['id'], 'sport': sport,
                        'home_team': fixture['home'], 'away_team': fixture['away'], 'kickoff': fixture['kickoff'],
                        'settlement_rule': 'INCLUDING_OVERTIME', 'recorded_at': trial['created_at'], 'source_sha256': digest,
                        'prediction': {'generated_at': fixture['generated_at'], 'feature_cutoff': fixture['feature_cutoff'],
                            'probabilities': probabilities, 'winner': max(probabilities, key=probabilities.get),
                            'model_version': f"NBA shadow {arm}:{trial['model_hashes'][arm]}", 'status': 'research_shadow'}})
    return rows


def read_results(sport: str) -> tuple[list[dict], dict]:
    from models.sport_data import load_games
    games = load_games(SPORTS[sport]['model_sport'])
    rows = [] if games.empty else games.to_dict('records')
    quality = games.attrs.get('data_quality', {})
    if sport == 'nba':
        for path in sorted((RAW_DATA_DIR / 'research').glob('nba_results_*/reconciliation/manifest.json')):
            manifest = json.loads(path.read_text(encoding='utf-8'))
            data = (path.parent / 'reconciled.jsonl').read_bytes()
            if hashlib.sha256(data).hexdigest() != manifest['normalized_sha256']:
                raise ValueError('NBA reconciled result checksum mismatch')
            rows.extend(json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip())
    return [{**row, 'settlement_rule': row.get('settlement_rule', 'INCLUDING_OVERTIME')} for row in rows], quality


def identity(sport: str, row: dict, date_key: str) -> tuple | None:
    date = timestamp(row.get(date_key))
    if date is None:
        return None
    names = [str(row.get(key, '')).strip().casefold() for key in ('home_team', 'away_team')]
    if sport == 'nba':
        from etl.nba_public_parsers import team
        names = [(team(name) or name).casefold() for name in names]
    if not all(names) or names[0] == names[1]:
        return None
    return sport, *names, date.isoformat()


def evaluate(sport: str, forecasts: list[dict], results: list[dict], now: datetime,
             *, page: int = 1, page_size: int = 10, league: str | None = None,
             model_version: str | None = None, days: int | None = None,
             start_date=None, end_date=None, result_filter: str = 'all') -> dict:
    if sport not in SUPPORTED:
        raise ValueError('Unsupported performance sport')
    excluded = Counter(invalid_forecast=0, pending=0, ambiguous_result=0, invalid_result=0,
                       duplicate_forecast=0, unknown_kickoff=0, unknown_kickoff_outside_date_window=0,
                       no_valid_pre_kickoff=0)
    lower = datetime.combine(start_date, datetime.min.time(), timezone.utc) if start_date else now - timedelta(days=days) if days and not end_date else None
    upper = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), timezone.utc) if end_date else now
    candidates = defaultdict(list)
    for row in forecasts:
        if row.get('sport') != sport:
            continue
        key = identity(sport, row, 'kickoff')
        prediction = row.get('prediction', {})
        generated, recorded = timestamp(prediction.get('generated_at')), timestamp(row.get('recorded_at'))
        kickoff = timestamp(row.get('kickoff'))
        probabilities = prediction.get('probabilities', {})
        values = [probabilities.get(name) for name in ('home_win', 'away_win')]
        cutoff = timestamp(prediction.get('feature_cutoff') or prediction.get('history_through'))
        if (key is None or generated is None or recorded is None or not generated <= recorded < kickoff
                or recorded > now or (cutoff is not None and cutoff > generated)
                or ((prediction.get('feature_cutoff') or prediction.get('history_through')) and cutoff is None)
                or row.get('settlement_rule') != 'INCLUDING_OVERTIME'
                or not prediction.get('model_version') or prediction.get('winner') not in ('home_win', 'away_win')
                or set(probabilities) != {'home_win', 'away_win'}
                or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1 for value in values)
                or abs(sum(values) - 1) > 1e-6):
            excluded['invalid_forecast'] += 1
            continue
        version = str(prediction['model_version'])
        if prediction.get('candidate_id'):
            version = f"{prediction['candidate_id']}:{version}"
        candidates[key].append({**row, 'version': version, 'generated': generated})
    versions = sorted({row['version'] for group in candidates.values() for row in group})
    result_index = defaultdict(list)
    for result in results:
        if (result.get('league') == SPORTS[sport]['league'] and result.get('completed') is True
                and result.get('date_precision') == 'TIMESTAMP'
                and result.get('settlement_rule') == 'INCLUDING_OVERTIME'):
            key = identity(sport, result, 'date')
            available = timestamp(result.get('result_available_at'))
            if key and available and timestamp(result['date']) < available <= now:
                result_index[key].append(result)
    settled = []
    for key, group in candidates.items():
        kickoff = timestamp(group[0]['kickoff'])
        if (lower and kickoff < lower) or kickoff >= upper or (league and league != SPORTS[sport]['label']):
            continue
        group = [row for row in group if not model_version or row['version'] == model_version]
        if not group:
            continue
        # Deterministic latest eligible prediction; version ID breaks equal-time ties.
        group.sort(key=lambda row: (row['generated'], row['version']))
        chosen = group[-1]
        peers = [row for row in group if (row['generated'], row['version']) == (chosen['generated'], chosen['version'])]
        if len({json.dumps(row['prediction'], sort_keys=True) for row in peers}) > 1:
            excluded['invalid_forecast'] += 1
            continue
        excluded['duplicate_forecast'] += len(group) - 1
        matches = result_index[key]
        if not matches:
            excluded['pending'] += 1
            continue
        scores = {(row.get('home_score'), row.get('away_score')) for row in matches}
        if len(scores) != 1:
            excluded['ambiguous_result'] += 1
            continue
        home, away = next(iter(scores))
        if any(not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or score < 0 or score != int(score) for score in (home, away)) or home == away:
            excluded['invalid_result'] += 1
            continue
        prediction = chosen['prediction']
        actual = 'home_win' if home > away else 'away_win'
        settled.append({'match_id': '|'.join(key), 'home_team': chosen['home_team'], 'away_team': chosen['away_team'],
            'competition': SPORTS[sport]['label'], 'match_date': kickoff.isoformat(), 'home_score': home, 'away_score': away,
            'predicted_winner': prediction['winner'], 'home_prob': prediction['probabilities']['home_win'],
            'away_prob': prediction['probabilities']['away_win'], 'draw_prob': None, 'actual_result': actual,
            'is_correct': prediction['winner'] == actual, 'model_version': chosen['version'],
            'prediction_created_at': chosen['generated'].isoformat(), 'model_status': prediction.get('status'),
            'source_sha256': chosen.get('source_sha256'), 'settlement_rule': 'INCLUDING_OVERTIME'})
    settled.sort(key=lambda row: (row['match_date'], row['match_id']), reverse=True)
    count = len(settled)
    correct = sum(row['is_correct'] for row in settled)
    selected = [row for row in settled if result_filter == 'all' or row['is_correct'] == (result_filter == 'correct')]
    summary = {'overall_accuracy': correct / count * 100 if count else None, 'total_predictions': count,
        'correct_predictions': correct, 'log_loss': sum(-math.log(max(1e-15, row['home_prob'] if row['actual_result'] == 'home_win' else row['away_prob'])) for row in settled) / count if count else None,
        'brier_score': sum((row['home_prob'] - (row['actual_result'] == 'home_win')) ** 2 + (row['away_prob'] - (row['actual_result'] == 'away_win')) ** 2 for row in settled) / count if count else None,
        'by_league': [{'league': SPORTS[sport]['label'], 'total': count, 'correct': correct, 'accuracy_pct': correct / count * 100}] if count else [],
        'excluded': dict(excluded), 'sample_start': settled[-1]['match_date'] if count else None,
        'sample_end': settled[0]['match_date'] if count else None,
        'evidence_note': 'Retained forecasts generated and recorded before tipoff; complete final scores include overtime. Pending, ambiguous and invalid results are excluded. Inactive candidates and research shadows are labeled; these metrics do not establish profitability.'}
    return {'sport': sport, 'settlement_rule': 'INCLUDING_OVERTIME', 'generated_at': now.isoformat(),
        'selection_rule': 'latest eligible per exact fixture; equal-time ties use model version ID',
        'summary': summary, 'versions': [{'version': version} for version in versions],
        'competitions': [SPORTS[sport]['label']],
        'history': {'predictions': selected[(page - 1) * page_size:page * page_size], 'total_count': len(selected),
                    'correct_count': sum(row['is_correct'] for row in selected), 'page': page, 'page_size': page_size}}


def feed(sport: str, **filters) -> dict:
    if sport not in SUPPORTED:
        raise ValueError('Unsupported performance sport')
    forecasts = read_forecasts(sport)
    results, quality = read_results(sport) if forecasts else ([], {})
    result = evaluate(sport, forecasts, results, datetime.now(timezone.utc), **filters)
    result['source_quality'] = quality
    return result
