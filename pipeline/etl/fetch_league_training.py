"""Bounded public archive and authenticated official UCL history refresh."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import requests

from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL, RAW_DATA_DIR
from etl.scrapling_transport import ScraplingTransport


def collect(output: Path, extra_seasons: bool = False, portugal_only: bool = False, portugal_open: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'sources': []}
    http = ScraplingTransport()
    urls = [(f'E1_{season}.csv', f'https://www.football-data.co.uk/mmz4281/{season}/E1.csv')
            for season in ['2324', '2425', '2526', '2627']]
    urls.append(('BRA.csv', 'https://www.football-data.co.uk/new/BRA.csv'))
    if extra_seasons:
        urls = [(f'{code}_2223.csv', f'https://www.football-data.co.uk/mmz4281/2223/{code}.csv') for code in ['P1', 'N1']]
    if portugal_only:
        urls = [('P1_2122.csv', 'https://football-data.co.uk/mmz4281/2122/P1.csv')]
    if portugal_open:
        urls = [('PPL_openfootball_2022.json', 'https://raw.githubusercontent.com/openfootball/football.json/master/2022-23/pt.1.json')]
    for filename, url in urls:
        row = {'filename': filename, 'url': url}
        try:
            response = http.get(url, timeout=30)
            response.raise_for_status()
            if portugal_open:
                payload = response.json()
                if payload.get('name') != 'Portuguese Primeira Liga 2022/23' or len(payload.get('matches', [])) != 306:
                    raise ValueError('Unexpected Portuguese season identity or inventory')
                row['format'] = 'openfootball_json'
            elif not response.content.startswith((b'Div,', b'Country,', b'\xef\xbb\xbf')):
                raise ValueError('Archive is not a supported CSV')
            (output/filename).write_bytes(response.content)
            row.update(status='collected', sha256=hashlib.sha256(response.content).hexdigest())
        except (requests.RequestException, ValueError) as exc:
            row.update(status='unavailable', error=type(exc).__name__)
        report['sources'].append(row)
        time.sleep(1)
    (output/'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for season in ([] if extra_seasons or portugal_only or portugal_open else [2020, 2021, 2022]):
        row = {'filename': f'CL_{season}.json', 'competition': 'CL', 'season': season}
        try:
            response = requests.get(FOOTBALL_DATA_ORG_BASE_URL + '/competitions/CL/matches',
                params={'season': season}, headers={'X-Auth-Token': FOOTBALL_DATA_ORG_API_KEY}, timeout=30)
            row['http_status'] = response.status_code
            response.raise_for_status()
            payload = response.json()
            if not payload.get('matches'):
                raise ValueError('Empty official season')
            (output/row['filename']).write_bytes(response.content)
            row.update(status='collected', matches=len(payload['matches']),
                       sha256=hashlib.sha256(response.content).hexdigest())
        except (requests.RequestException, ValueError) as exc:
            row.update(status='unavailable', error=type(exc).__name__)
        report['sources'].append(row)
        (output/'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        if row.get('http_status') in {401, 403, 429}:
            break
        time.sleep(7)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=RAW_DATA_DIR/'league_training'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    parser.add_argument('--extra-seasons', action='store_true')
    parser.add_argument('--portugal-only', action='store_true')
    parser.add_argument('--portugal-open', action='store_true')
    args = parser.parse_args()
    print(json.dumps(collect(args.output_dir, args.extra_seasons, args.portugal_only, args.portugal_open), indent=2))
