import json
import sys
from pathlib import Path
from lxml import html
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from etl.scrapling_transport import ScraplingTransport
out = ROOT / 'pipeline/data/raw/ucl_history_20261020'
t = ScraplingTransport()
for name, url in [('slovan_2025', 'https://www.skslovan.com/zapasy/?season=202526'), ('slovan_2026', 'https://www.skslovan.com/zapasy/?season=202627'), ('slovan_2024', 'https://www.skslovan.com/zapasy/?season=202425'), ('slovan_2023', 'https://www.skslovan.com/zapasy/?season=202324')]:
    try:
        path = out / (name + '.html')
        if path.exists():
            content, status = path.read_bytes(), 200
        else:
            r = t.get(url, timeout=20)
            content, status = r.content, r.status_code
            if status == 200:
                path.write_bytes(content)
        tree = html.fromstring(content)
        print(json.dumps({'name': name, 'status': status,
                          'selects': [html.tostring(s, encoding='unicode')[:1600] for s in tree.xpath('//select')],
                          'sample_rows': [html.tostring(s, encoding='unicode')[:1800] for s in tree.xpath('//tr[td]') if 2 <= len(s.xpath('./td')) <= 8][:5],
                          'played': [' '.join(s.text_content().split())[:200] for s in tree.xpath('//tr[contains(@class,"played")]')[:2]]}, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({'name': name, 'error': type(e).__name__}), flush=True)
