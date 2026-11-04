"""Check BALLDONTLIE football entitlements without exposing credentials."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from dotenv import dotenv_values
import requests

ROOT = Path(__file__).resolve().parents[3]
key = dotenv_values(ROOT / 'pipeline/.env').get('BALLDONTLIE_API_KEY')
if not key:
    raise SystemExit('BALLDONTLIE_API_KEY is not configured')
output = ROOT / 'pipeline/data/raw/balldontlie' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
output.mkdir(parents=True, exist_ok=False)
checks = []
for sport in ['nfl', 'ncaaf']:
    for endpoint in ['games', 'odds', 'odds/opening']:
        url = f'https://api.balldontlie.io/{sport}/v1/{endpoint}'
        params = {'season': 2025, 'week': 10, 'per_page': 1}
        if endpoint == 'games':
            params = {'seasons[]': 2025, 'weeks[]': 10, 'per_page': 1} if sport == 'nfl' else {'season': 2025, 'week': 10, 'per_page': 1}
        name = f'{sport}-{endpoint.replace("/", "-")}'
        try:
            response = requests.get(url, params=params, headers={'Authorization': key}, timeout=40)
            text = response.text.replace(key, '[REDACTED]')
            path = output / f'{name}.json'
            path.write_text(text, encoding='utf-8')
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {}
            rows = payload.get('data', []) if isinstance(payload, dict) else []
            check = {'sport': sport, 'endpoint': endpoint, 'url': url, 'params': params,
                'http_status': response.status_code, 'records': len(rows),
                'sample_fields': list(rows[0]) if rows else [],
                'sample': rows[:1], 'meta': payload.get('meta') if isinstance(payload, dict) else None,
                'error': (payload.get('message') or payload.get('error')) if isinstance(payload, dict) else None,
                'file': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        except requests.RequestException as exc:
            check = {'sport': sport, 'endpoint': endpoint, 'error': type(exc).__name__}
        checks.append(check)
        evidence = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'capture_dir': str(output.resolve()), 'checks': checks}
        (ROOT / 'stages/03-build/output/balldontlie-access-20261016.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in check.items() if k not in ['sample','file','sha256','sample_fields','meta']}), flush=True)
        # Stay below the documented free-plan five-request/minute rate.
        time.sleep(13)
print(json.dumps({'capture_dir': str(output.resolve()), 'checks': len(checks)}), flush=True)
