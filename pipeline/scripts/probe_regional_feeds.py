"""Bounded anonymous probes of read-only paths found in published client code."""
from datetime import datetime, timezone
import json
from pathlib import Path
import requests
from config import RAW_DATA_DIR


def main():
    root = RAW_DATA_DIR / 'sportsbooks' / ('feeds_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir()
    jurisdictions = json.loads((RAW_DATA_DIR / 'sportsbooks/feeds_20261010T120443Z/betpawa_jurisdictions.raw').read_text(encoding='utf-8'))
    uganda = next(row for row in jurisdictions['data'] if row.get('countryCode') == 'UG' and row.get('locale') == 'en')
    print('Published Uganda brand:', uganda['brandIdentifier'], uganda.get('hostname'))
    targets = [
        ('betpawa_category_football', 'GET', 'https://www.betpawa.ug/api/sportsbook/v4/categories/list/2', None),
    ]
    report = {}
    for name, method, url, payload in targets:
        try:
            query = {'queries': [{'query': {'eventType': 'UPCOMING', 'categories': ['2'], 'hasOdds': True}, 'sort': {'startTime': 'ASC'}, 'take': 100}]}
            response = requests.request(method, url, json=payload, timeout=(5, 20), headers={'Accept': 'application/json', 'Content-Type':'application/json', 'X-Pawa-Brand': uganda['brandIdentifier'], 'X-Pawa-Language': 'en'})
            (root / (name + '.raw')).write_bytes(response.content)
            row = {'status': response.status_code, 'bytes': len(response.content), 'observed_at': datetime.now(timezone.utc).isoformat(),
                   'content_type': response.headers.get('content-type'), 'source_url': url}
            try:
                data = response.json()
                row['shape'] = list(data)[:12] if isinstance(data, dict) else type(data).__name__
                if isinstance(data, dict):
                    row['sample'] = str(data)[:1200]
            except ValueError:
                row['format'] = 'not_json'
            report[name] = row
        except requests.RequestException as exc:
            report[name] = {'error': type(exc).__name__}
    (root / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(root), **report}, indent=2))


if __name__ == '__main__':
    main()
