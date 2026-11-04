"""Export existing pregame forecasts and independently fetched results; no DB writes."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import requests
from sqlalchemy import text
from api.db import get_db_connection
from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL
from models.paper_trial import dashboard, result_key
from models.validation import probability_metrics
import numpy as np

DAY = '2026-10-10'
OUT = Path(__file__).parent / 'today-prediction-evidence-20261010'
OUT.mkdir(exist_ok=True)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def serialize(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    raise TypeError(type(value).__name__)


def main():
    url = FOOTBALL_DATA_ORG_BASE_URL.rstrip('/') + '/matches'
    response = requests.get(url, params={'dateFrom': DAY, 'dateTo': DAY},
        headers={'X-Auth-Token': FOOTBALL_DATA_ORG_API_KEY}, timeout=(5, 25))
    if response.status_code != 200:
        raise ValueError(f'Result provider HTTP {response.status_code}')
    observed = datetime.now(timezone.utc).isoformat()
    raw = OUT / f'{stamp}-official-results.json'
    raw.write_bytes(response.content)
    events = response.json().get('matches', [])
    captures = [{'source_url': url, 'raw_capture': str(raw),
        'source_sha256': hashlib.sha256(response.content).hexdigest(), 'events': len(events)}]
    # The account-wide endpoint can return an empty TIER_ONE scope while PL is accessible.
    league_url = FOOTBALL_DATA_ORG_BASE_URL.rstrip('/') + '/competitions/PL/matches'
    league_response = requests.get(league_url, params={'dateFrom': DAY, 'dateTo': DAY},
        headers={'X-Auth-Token': FOOTBALL_DATA_ORG_API_KEY}, timeout=(5, 25))
    if league_response.status_code != 200:
        raise ValueError(f'EPL result provider HTTP {league_response.status_code}')
    league_raw = OUT / f'{stamp}-official-epl-results.json'
    league_raw.write_bytes(league_response.content)
    league_events = league_response.json().get('matches', [])
    captures.append({'source_url': league_url, 'raw_capture': str(league_raw),
        'source_sha256': hashlib.sha256(league_response.content).hexdigest(), 'events': len(league_events)})
    by_id = {event['id']: event for event in events}
    for event in league_events:
        if event['id'] in by_id and by_id[event['id']]['score'] != event['score']:
            raise ValueError('Official endpoints disagree on a result')
        by_id[event['id']] = event
    events = list(by_id.values())
    results = []
    lookup = defaultdict(list)
    for event in events:
        score = event.get('score', {})
        row = {'provider_event_id': event['id'], 'home': event['homeTeam']['name'],
            'away': event['awayTeam']['name'], 'kickoff': event['utcDate'],
            'competition': event['competition']['name'], 'status': event['status'],
            'duration': score.get('duration'), 'home_score': score.get('fullTime', {}).get('home'),
            'away_score': score.get('fullTime', {}).get('away')}
        results.append(row)
        if row['status'] == 'FINISHED' and row['duration'] == 'REGULAR' and all(
                type(row[k]) is int and row[k] >= 0 for k in ['home_score', 'away_score']):
            row['result'] = ('home_win' if row['home_score'] > row['away_score'] else
                             'away_win' if row['home_score'] < row['away_score'] else 'draw')
            lookup[result_key(row['home'], row['away'], row['kickoff'])].append(row)
    query = '''SELECT m.match_id,m.home_team,m.away_team,m.date,m.competition,m.status,m.result,
        m.home_score,m.away_score,p.id AS prediction_id,p.model_version,p.winner,
        p.home_prob,p.draw_prob,p.away_prob,p.created_at,
        COALESCE(q.quotes,'[]'::json) AS quotes
        FROM matches m LEFT JOIN LATERAL (
            SELECT DISTINCT ON (model_version) * FROM predictions p WHERE p.match_id=m.match_id
                AND p.created_at < m.date AND p.home_prob BETWEEN 0 AND 1
                AND p.draw_prob BETWEEN 0 AND 1 AND p.away_prob BETWEEN 0 AND 1
                AND ABS(p.home_prob+p.draw_prob+p.away_prob-1)<0.000001
                AND p.winner IN ('home_win','draw','away_win')
            ORDER BY model_version,p.created_at DESC,p.id DESC
        ) p ON TRUE LEFT JOIN LATERAL (
            SELECT json_agg(latest) AS quotes FROM (
                SELECT DISTINCT ON (bookmaker) bookmaker,home_win,draw,away_win,updated_at
                FROM odds o WHERE o.match_id=m.match_id AND o.updated_at<=p.created_at
                    AND o.updated_at<m.date AND o.home_win>1 AND o.draw>1 AND o.away_win>1
                ORDER BY bookmaker,updated_at DESC,id DESC
            ) latest
        ) q ON TRUE WHERE m.date::date=CAST(:day AS DATE) ORDER BY m.date,m.match_id,p.model_version'''
    with get_db_connection().connect() as connection:
        rows = [dict(r) for r in connection.execute(text(query), {'day': DAY}).mappings()]
        unknown = connection.execute(text('SELECT COUNT(DISTINCT m.match_id) FROM matches m JOIN predictions p ON p.match_id=m.match_id WHERE m.date IS NULL')).scalar()
    provenance = {}
    for path in (ROOT / 'pipeline/data/processed/regional_audits').glob('*_cycle.json'):
        payload = json.loads(path.read_text(encoding='utf-8'))
        for forecast in payload.get('forecasts', []):
            if forecast.get('prediction_id'):
                provenance[forecast['prediction_id']] = {'audit_file': str(path), **forecast}
    eligible = defaultdict(list)
    for row in rows:
        row['date'] = row['date'].replace(tzinfo=timezone.utc)
        matches = lookup.get(result_key(row['home_team'], row['away_team'], row['date']), [])
        # Require exact provider ID as well as teams and kickoff; ambiguous matches excluded.
        matches = [m for m in matches if m['provider_event_id'] == row['match_id']]
        row['official_result'] = matches[0] if len(matches) == 1 else None
        row['evaluation_status'] = ('missing_pregame_prediction' if row['prediction_id'] is None else
                                    'eligible' if len(matches) == 1 else 'no_exact_official_final_result')
        row['provenance'] = provenance.get(row['prediction_id'])
        if row['evaluation_status'] == 'eligible':
            row['is_correct'] = row['winner'] == matches[0]['result']
            eligible[row['model_version']].append(row)
    classes = ['away_win', 'draw', 'home_win']
    keys = ['away_prob', 'draw_prob', 'home_prob']
    metrics = {}
    for version, group in eligible.items():
        probs = np.array([[row[key] for key in keys] for row in group])
        labels = np.array([classes.index(row['official_result']['result']) for row in group])
        metrics[version] = probability_metrics(labels, probs, classes)
        metrics[version]['stored_winner_correct'] = sum(r['is_correct'] for r in group)
    db_keys = {result_key(r['home_team'], r['away_team'], r['date']) for r in rows}
    uncovered = [r for r in results if result_key(r['home'], r['away'], r['kickoff']) not in db_keys]
    report = {'date': DAY, 'date_basis': 'UTC', 'observed_at': observed,
        'source_url': url, 'raw_capture': str(raw), 'source_sha256': hashlib.sha256(response.content).hexdigest(),
        'source_captures': captures,
        'provider_event_count': len(events), 'official_results': results,
        'database_forecast_rows': rows, 'model_metrics': metrics,
        'provider_events_without_exact_database_fixture': uncovered,
        'unknown_kickoff_predictions_excluded': unknown, 'frozen_trials': dashboard(),
        'profitable_edge_established': False,
        'limits': ['Provider coverage is limited to this account, not every game worldwide.',
            'No predictions were generated after results for this evaluation.',
            'Latest valid pregame forecast per fixture and model version; versions are not pooled.',
            'Existing DB forecast timestamps alone do not prove training/input provenance.',
            'Odds in this export were observed by forecast time; no retrospective policy tuning.',
            'DB match results were not updated; official results are joined only in this report.',
            'Naive pipeline match and forecast timestamps are interpreted as UTC, consistent with ingestion.',
            'Formal frozen trial requires 200 settled selections across 60 fixture days.']}
    path = OUT / f'{stamp}-evaluation.json'
    path.write_text(json.dumps(report, default=serialize, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'report': str(path), 'provider_events': len(events), 'database_rows': len(rows),
        'metrics': metrics, 'uncovered': len(uncovered)}, indent=2))


if __name__ == '__main__':
    main()
