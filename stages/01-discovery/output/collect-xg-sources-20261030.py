"""Capture public xG source evidence without changing production data."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scrapling.fetchers import Fetcher, DynamicFetcher

OUT = Path(__file__).resolve().parent / 'xg-sources-20261030'
OUT.mkdir(exist_ok=True)
SOURCES = [('footystats', 'https://footystats.org/england/premier-league/xg'),
           ('understat', 'https://understat.com/league/EPL/2026'),
           ('xgstat', 'https://www.xgstat.com/competitions/premier-league/2026-2027')]
reports = []
for name, url in SOURCES:
    report = {'source': name, 'url': url}
    try:
        page = Fetcher.get(url, timeout=25)
        body = page.body
        if isinstance(body, str):
            body = body.encode()
        (OUT / (name + '.html')).write_bytes(body)
        text = page.get_all_text(separator='\n')
        (OUT / (name + '.txt')).write_text(text, encoding='utf-8')
        report.update(status=page.status, observed_at=datetime.now(timezone.utc).isoformat(),
                      sha256=hashlib.sha256(body).hexdigest(), text_characters=len(text))
        print(name, report, flush=True)
        if name == 'understat':
            scripts = '\n'.join(page.css('script::text').getall())
            for variable in ['teamsData', 'datesData', 'playersData']:
                match = re.search(variable + r"\s*=\s*JSON.parse\('(.+?)'\)", scripts)
                if match:
                    data = json.loads(match.group(1).encode().decode('unicode_escape'))
                    (OUT / (variable + '.json')).write_text(json.dumps(data, indent=2), encoding='utf-8')
                    report[variable + '_records'] = len(data)
                    if variable == 'teamsData':
                        print('UNDERSTAT_TEAMS', [(v.get('title'), len(v.get('history', []))) for v in data.values()], flush=True)
        if name == 'footystats':
            print('FOOTYSTATS_TABLES', [t.get_all_text(separator=' | ')[:10000] for t in page.css('table')][:3], flush=True)
        if name == 'xgstat':
            print('XGSTAT_TEXT', text[-16000:], flush=True)
    except Exception as exc:
        report['error'] = type(exc).__name__
        print(name, type(exc).__name__, flush=True)
    reports.append(report)
(OUT / 'manifest.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print('SAVED', OUT, flush=True)
