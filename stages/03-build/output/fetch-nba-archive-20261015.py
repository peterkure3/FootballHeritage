"""Download public NBA archive data with Scrapling and preserve provenance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.scrapling_transport import ScraplingTransport

output = ROOT / 'pipeline/data/raw/historical/nba/free_archive/20261015'
output.mkdir(parents=True, exist_ok=True)
base = 'https://raw.githubusercontent.com/guydotan/ucla-thesis/master/'
sources = {'nba_adv_complete.csv': base + 'data/nba_adv_complete.csv',
    'LICENSE.txt': base + 'LICENSE', 'README.md': base + 'README.md',
    'data-provenance.md': 'https://raw.githubusercontent.com/jacobburdier05/nba-moneyline-calibration/main/data/README.md'}
transport = ScraplingTransport()
captures = []
for name, url in sources.items():
    path = output / name
    if not path.exists():
        response = transport.get(url, timeout=90)
        response.raise_for_status()
        path.write_bytes(response.content)
    captures.append({'file': name, 'url': url, 'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    print(json.dumps(captures[-1]), flush=True)
(output / 'manifest.json').write_text(json.dumps({'retrieved_at': datetime.now(timezone.utc).isoformat(),
    'transport': 'scrapling', 'captures': captures,
    'odds_observed_at': None, 'line_type': 'UNDOCUMENTED',
    'restriction': 'Retrospective research only; quote timing not verified. Do not synthesize historical observation timestamps.'}, indent=2), encoding='utf-8')
