import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import requests

root = Path(__file__).resolve().parent
for name, url in [('epl-results-2627.csv', 'https://www.football-data.co.uk/mmz4281/2627/E0.csv'),
                  ('understat-epl-2026.html', 'https://understat.com/league/EPL/2026')]:
    try:
        response = requests.get(url, timeout=30)
        print(name, response.status_code, len(response.content))
        if response.ok:
            (root / name).write_bytes(response.content)
            (root / (name + '.provenance.json')).write_text(json.dumps({'url': url,
                'observed_at': datetime.now(timezone.utc).isoformat(),
                'sha256': hashlib.sha256(response.content).hexdigest()}, indent=2))
            if name.endswith('.csv'):
                f = pd.read_csv(io.BytesIO(response.content))
                print('COLUMNS', f.columns.tolist())
                print('ROWS', len(f), 'TAIL', f.tail(12).to_json(orient='records')[:3000])
            else:
                print('TEAMS_DATA', 'teamsData' in response.text, 'DATES', response.text[:80])
    except requests.RequestException as exc:
        print(name, type(exc).__name__)
