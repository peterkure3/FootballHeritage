"""Refresh bounded official EPL fixtures without invoking unrelated odds providers."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api.db import get_db_connection
from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL, RAW_DATA_DIR
from etl.load_to_db import upsert_matches
from etl.transform import normalize_football_data_org_matches


def run() -> dict:
    now = datetime.now(timezone.utc)
    url = FOOTBALL_DATA_ORG_BASE_URL.rstrip('/') + '/competitions/PL/matches'
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=Retry(total=2, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'])))
        response = session.get(url, params={'dateFrom': (now - timedelta(days=2)).date().isoformat(),
            'dateTo': (now + timedelta(days=14)).date().isoformat()},
            headers={'X-Auth-Token': FOOTBALL_DATA_ORG_API_KEY}, timeout=(10, 25))
    if response.status_code != 200:
        raise ValueError(f'EPL fixture provider HTTP {response.status_code}')
    payload = response.json()
    events = payload.get('matches')
    if not isinstance(events, list):
        raise ValueError('EPL fixture provider returned an invalid payload')
    if len({event['id'] for event in events}) != len(events):
        raise ValueError('Duplicate official fixture ID')
    for event in events:
        if event.get('competition', {}).get('code') != 'PL':
            raise ValueError('Non-EPL fixture in trial ingestion')
        instant = pd.Timestamp(event['utcDate'])
        if instant.tzinfo is None or not event['homeTeam']['name'] or not event['awayTeam']['name']:
            raise ValueError('Fixture requires UTC kickoff and both teams')
    root = RAW_DATA_DIR / 'trial_fixtures'
    root.mkdir(exist_ok=True)
    path = root / f'epl_{now:%Y%m%dT%H%M%S%fZ}.json'
    path.write_bytes(response.content)
    frame = normalize_football_data_org_matches([path])
    if not frame.empty:
        unfinished = frame.status.ne('FINISHED')
        frame.loc[unfinished, ['home_score', 'away_score', 'result']] = None
        upsert_matches(frame, get_db_connection())
    return {'fixtures': len(events), 'source_url': url, 'observed_at': now.isoformat(),
            'source_sha256': hashlib.sha256(response.content).hexdigest(), 'raw_capture': str(path)}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
