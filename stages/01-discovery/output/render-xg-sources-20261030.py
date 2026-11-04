import json
from pathlib import Path
from datetime import datetime, timezone
from scrapling.fetchers import DynamicFetcher
from lxml import html

out = Path(__file__).resolve().parent / 'xg-sources-20261030'
document = html.fromstring((out / 'footystats.html').read_bytes())
tables = document.xpath('//table')
rows = []
for tr in tables[0].xpath('./tbody/tr|./tr'):
    cells = tr.xpath('./td')
    if len(cells) >= 9:
        values = [' '.join(c.text_content().split()) for c in cells]
        # Team tooltips contain duplicate names; keep the first image alt as identity.
        team = cells[2].xpath('.//a/@title') or cells[2].xpath('.//a/text()')
        rows.append({'cells': values, 'team_label': team})
(out / 'footystats-table-rows.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('FOOTYSTATS_ROWS', len(rows), [(r['cells'][2][:35], r['cells'][-7:]) for r in rows], flush=True)
for name, url in [('understat-rendered', 'https://understat.com/league/EPL'),
                  ('xgstat-rendered', 'https://www.xgstat.com/competitions/premier-league/2026-2027')]:
    try:
        page = DynamicFetcher.fetch(url, headless=True, timeout=45000, wait=6000, disable_resources=True)
        text = page.get_all_text(separator='\n')
        (out / (name + '.txt')).write_text(text, encoding='utf-8')
        body = page.body
        if isinstance(body, str):
            body = body.encode()
        (out / (name + '.html')).write_bytes(body)
        print(name, 'STATUS', page.status, 'TIME', datetime.now(timezone.utc).isoformat(), text[-13000:], flush=True)
    except Exception as exc:
        print(name, type(exc).__name__, str(exc)[:200], flush=True)
