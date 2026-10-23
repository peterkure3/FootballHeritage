"""Collect fresh official EPL results and settle imported forecasts separately."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests

from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL, RAW_DATA_DIR
from models.paper_trial import TRIAL_ROOT, import_trial, settle_directory


def collect_results(match_date):
    url = FOOTBALL_DATA_ORG_BASE_URL.rstrip('/') + '/competitions/PL/matches'
    response = requests.get(url, params={'dateFrom': match_date, 'dateTo': match_date},
                            headers={'X-Auth-Token': FOOTBALL_DATA_ORG_API_KEY}, timeout=(5, 20))
    if response.status_code != 200:
        raise ValueError(f'Official result provider returned HTTP {response.status_code}')
    observed = datetime.now(timezone.utc).isoformat()
    root = RAW_DATA_DIR / 'trial_results'
    root.mkdir(exist_ok=True)
    path = root / ('epl_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    path.write_bytes(response.content)
    digest = hashlib.sha256(response.content).hexdigest()
    results = []
    for event in response.json().get('matches', []):
        if event.get('status') != 'FINISHED' or event.get('score', {}).get('duration') != 'REGULAR':
            continue
        score = event['score']['fullTime']
        results.append({'provider_event_id': str(event['id']), 'home_team': event['homeTeam']['name'],
            'away_team': event['awayTeam']['name'], 'commence_time': event['utcDate'],
            'home_score': score.get('home'), 'away_score': score.get('away'), 'status': 'FINISHED',
            'settlement_rule': 'REGULATION_TIME', 'observed_at': observed,
            'source_url': url, 'raw_capture_ref': str(path), 'source_sha256': digest})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-trial', type=Path)
    parser.add_argument('--match-date', required=True)
    args = parser.parse_args()
    if args.import_trial:
        import_trial(args.import_trial)
    results = collect_results(args.match_date)
    reports = [settle_directory(path.parent, results) for path in TRIAL_ROOT.glob('*/trial.json')
               if any(row['kickoff'].startswith(args.match_date) for row in json.loads(path.read_text())['fixtures'])]
    print(json.dumps([{'candidate': row['candidate_id'], 'settled_selections': row['settled_selections'],
                       'pending_forecasts': row['pending_forecasts'], 'roi': row['roi']} for row in reports], indent=2))


if __name__ == '__main__':
    main()
