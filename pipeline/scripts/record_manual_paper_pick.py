"""Record a user-selected prematch paper pick separately from frozen model trials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR
from models.paper_trial import TRIAL_ROOT, import_trial
from scripts.record_edge_trial import price_analysis


def build_trial(fixture: dict, selection: str, now: datetime) -> dict:
    kickoff = pd.Timestamp(fixture['kickoff'])
    instant = pd.Timestamp(now)
    if kickoff.tzinfo is None or instant >= kickoff:
        raise ValueError('Manual paper selections must be recorded before kickoff')
    prediction = fixture.get('prediction') or {}
    if prediction.get('status') != 'current':
        raise ValueError('A current model snapshot is required for probability context')
    eligible = []
    for quote in fixture['market']['quotes']:
        observed = pd.Timestamp(quote['observed_at']) if quote.get('observed_at') else None
        if quote.get('fresh') and observed is not None and observed.tzinfo is not None and 0 <= (instant - observed).total_seconds() <= 900:
            price_analysis(prediction['probabilities'], quote['prices'])
            eligible.append(quote)
    if not eligible:
        raise ValueError('No complete bookmaker quote observed within 15 minutes')
    if selection not in prediction['probabilities']:
        raise ValueError('Unknown outcome')
    quote = max(eligible, key=lambda row: row['prices'][selection])
    row = {'home': fixture['home_team'], 'away': fixture['away_team'],
           'kickoff': kickoff.isoformat(), 'bookmaker': quote['bookmaker'],
           'observed_at': quote['observed_at'], 'generated_at': instant.isoformat(),
           'status': 'recorded_pregame', 'selected_outcome': selection,
           'outcomes': price_analysis(prediction['probabilities'], quote['prices']),
           'model_context': prediction, 'match_id': fixture['match_id']}
    return {'status': 'prospective_paper_trial', 'profitable_edge_established': False,
            'candidate_id': 'manual-selection', 'candidate_checksums': {},
            'created_at': instant.isoformat(),
            'policy': {'selection': 'user_selected', 'units_per_selection': 1,
                       'max_selections_per_fixture': 1, 'payout_haircut': .02,
                       'max_quote_age_seconds': 900, 'settlement': 'REGULATION_TIME',
                       'request_id': f"{fixture['match_id']}:{selection}"},
            'limits': ['Manual paper choice; excluded from the frozen model assessment.',
                       'Stored active-model probabilities provide context, not the selection rule.',
                       'Public quoted prices are not confirmed executable prices.'],
            'fixtures': [row]}


def record(fixture: dict, selection: str) -> Path:
    existing = existing_pick(fixture['match_id'], selection)
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    trial = build_trial(fixture, selection, now)
    root = RAW_DATA_DIR / 'manual_paper_choices'
    root.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime('%Y%m%dT%H%M%S%fZ')
    source = root / f'{stamp}_fixture.json'
    payload = json.dumps(fixture, indent=2, allow_nan=False).encode()
    with source.open('xb') as stream:
        stream.write(payload)
    trial.update(source=str(source.resolve()), source_sha256=hashlib.sha256(payload).hexdigest())
    trial['fixtures'][0]['raw_capture_ref'] = str(source.resolve())
    destination = root / f'{stamp}_trial.json'
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(trial, stream, indent=2, allow_nan=False)
    if pd.Timestamp.now(tz='UTC') >= pd.Timestamp(fixture['kickoff']):
        raise ValueError('Kickoff passed before import; no manual selection was imported')
    return import_trial(destination)


def existing_pick(match_id: int, selection: str) -> Path | None:
    for source in TRIAL_ROOT.glob('*/trial.json'):
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != source.parent.name:
            raise ValueError('Trial checksum mismatch')
        trial = json.loads(payload)
        if trial['policy'].get('selection') != 'user_selected':
            continue
        for row in trial['fixtures']:
            if row.get('match_id') == match_id:
                if row['selected_outcome'] != selection:
                    raise ValueError('An immutable manual choice already exists for this fixture')
                return source.parent
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match-id', type=int, required=True)
    parser.add_argument('--selection', choices=['home_win', 'draw', 'away_win'], required=True)
    parser.add_argument('--api-url', default='http://localhost:5555/api/v1')
    args = parser.parse_args()
    page = 1
    while True:
        response = requests.get(args.api_url.rstrip('/') + '/prediction-dashboard/fixtures',
                                params={'page': page, 'page_size': 50}, timeout=(5, 20))
        response.raise_for_status()
        feed = response.json()
        fixture = next((row for row in feed['items'] if row['match_id'] == args.match_id), None)
        if fixture:
            directory = record(fixture, args.selection)
            trial = json.loads((directory / 'trial.json').read_text())
            row = trial['fixtures'][0]
            print(json.dumps({'directory': str(directory), 'fixture': f"{row['home']} vs {row['away']}",
                              'selection': row['selected_outcome'], 'bookmaker': row['bookmaker'],
                              'decimal_odds': row['outcomes'][row['selected_outcome']]['decimal_odds'],
                              'recorded_at': row['generated_at'], 'kickoff': row['kickoff']}, indent=2))
            return
        if page * 50 >= feed['total_count']:
            raise ValueError('Fixture is not present in the upcoming feed')
        page += 1


if __name__ == '__main__':
    main()
