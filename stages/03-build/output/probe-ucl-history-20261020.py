import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.scrapling_transport import ScraplingTransport

out = ROOT / 'pipeline/data/raw/ucl_history_20261020/probe'
out.mkdir(parents=True, exist_ok=True)
transport = ScraplingTransport()
urls = {
    'espn_bodo': 'https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/2980/schedule?season=2026',
    'glimt': 'https://www.glimt.no/resultater',
    'csv_eng': 'https://www.football-data.co.uk/mmz4281/2627/E0.csv',
    'csv_nor': 'https://www.football-data.co.uk/new/Norway.csv',
    'sofa_bodo': 'https://www.sofascore.com/api/v1/search/all?q=Bodo',
    'terrikon_sabah': 'https://terrikon.com/en/football/teams/2087/gamesarchive',
    'slovan': 'https://www.skslovan.com/vysledky/',
    'sabah': 'https://sabahfc.az/results',
}
for name, url in urls.items():
    try:
        r = transport.get(url, timeout=20)
        (out / (name + '.txt')).write_bytes(r.content)
        summary = {'name': name, 'status': r.status_code, 'bytes': len(r.content), 'url': url}
        try:
            d = r.json()
            summary['keys'] = list(d)[:8]
            summary['events'] = len(d.get('events', []))
            if d.get('events'):
                summary['first_event'] = d['events'][0]
        except (ValueError, AttributeError):
            summary['head'] = r.text[:150]
    except Exception as exc:
        summary = {'name': name, 'url': url, 'error': str(exc)}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
