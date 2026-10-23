"""Inspect user-supplied fixture endpoints without persisting browser credentials."""
import argparse
import getpass
from datetime import datetime, timezone
import json
import sys

import requests

from config import RAW_DATA_DIR

CAESARS_URL = 'https://api.americanwagering.com/regions/us/locations/nj/brands/czr/sb/v4/sports/football/competitions/9749ba20-1aa4-4f10-8014-af726d2c6fc5/quick-picks'
CLOUDBET_URL = 'https://www.cloudbet.com/sports-api/c/v6/sports/competitions/soccer-international-clubs-uefa-champions-league/events'
ONEXBET_URL = 'https://1xbet.com/service-api/main-line-feed/v3/games1x2'


def fetch(book, url, headers, output, params=None, secret=None):
    row = {'bookmaker': book, 'source_url': url, 'observed_at': datetime.now(timezone.utc).isoformat(),
           'browser_cookies_used': False, 'waf_token_used': secret is not None}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=(5, 20), allow_redirects=False)
        row.update(http_status=response.status_code, content_type=response.headers.get('Content-Type', ''))
        payload = response.content
        if secret:
            payload = payload.replace(secret.encode(), b'<redacted>')
        suffix = '.json' if 'json' in row['content_type'].lower() else '.html'
        name = book + ('_session' if secret else '_anonymous') + suffix
        (output / name).write_bytes(payload)
        row['capture'] = name
        try:
            value = json.loads(payload)
            row['shape'] = list(value)[:20] if isinstance(value, dict) else type(value).__name__
        except (ValueError, UnicodeError):
            row['shape'] = 'non_JSON'
    except requests.RequestException as error:
        row['error_type'] = type(error).__name__
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-stdin', action='store_true', help='Read ephemeral Caesars session headers from stdin if anonymous access fails')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = RAW_DATA_DIR / 'sportsbooks' / ('supplied_' + stamp)
    output.mkdir()
    headers = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36'}
    caesars_headers = headers | {'Origin': 'https://sportsbook.caesars.com', 'Referer': 'https://sportsbook.caesars.com/',
        'x-app-version': '7.57.0', 'x-platform': 'cordova-desktop'}
    rows = [fetch('caesars', CAESARS_URL, caesars_headers, output)]
    cloud_headers = headers | {'Referer': 'https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events', 'x-cloudbet-version': 'v1.2.27'}
    params = [('from', str(int(datetime.now(timezone.utc).timestamp()))), ('include-all-event-types', 'false'),
        ('include-pretrading', 'false'), ('limit', '25'), ('locale', 'en'), ('markets', 'soccer.match_odds'),
        ('markets', 'soccer.asian_handicap'), ('markets', 'soccer.total_goals'), ('sports', 'soccer')]
    rows.append(fetch('cloudbet', CLOUDBET_URL, cloud_headers, output, params))
    onex_headers = headers | {'Referer': 'https://1xbet.com/en/line/football/118587-uefa-champions-league',
        'is-srv': 'false', 'x-app-n': '__BETTING_APP__', 'x-requested-with': 'XMLHttpRequest',
        'x-svc-source': '__BETTING_APP__'}
    onex_params = {'cfView': 3, 'count': 40, 'fcountry': 191, 'gr': 285, 'grMode': 4,
                   'lng': 'en', 'ref': 1, 'selectedMs': '1.1.118587,2.1.118587'}
    rows.append(fetch('1xbet', ONEXBET_URL, onex_headers, output, onex_params))
    (output / 'report.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    if args.session_stdin and rows[0].get('http_status') != 200:
        print('Awaiting ephemeral Caesars session headers on stdin.', flush=True)
        value = getpass.getpass('Session headers: ') if sys.stdin.isatty() else sys.stdin.readline()
        if not value:
            print(json.dumps({'capture': str(output), 'session_replay': 'headers_not_received'}), flush=True)
            return
        session = json.loads(value)
        token = session['waf_token']
        authenticated = caesars_headers | {'x-aws-waf-token': token, 'x-unique-device-id': session['device_id']}
        rows.append(fetch('caesars', CAESARS_URL, authenticated, output, secret=token))
    (output / 'report.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(json.dumps({'capture': str(output), 'sources': rows}), flush=True)


if __name__ == '__main__':
    main()
