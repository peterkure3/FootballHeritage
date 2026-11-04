import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
bdl=json.loads((ROOT/'stages/03-build/output/nba-balldontlie-access-20261021.json').read_text())
data=json.loads((Path(bdl['directory'])/'games.json').read_text())
print(json.dumps({'games':data.get('data',[])[:3]},indent=2))
p=json.loads((ROOT/'stages/03-build/output/nba-market-probe-20261021.json').read_text())
for source in p['sources']:
    if source['name']=='cloudbet-markets':
        d=json.loads(Path(source['file']).read_text());print(json.dumps({'cloud_counts':{t:sum(e.get('type')==t for e in d.get('events',[])) for t in ['EVENT_TYPE_EVENT','EVENT_TYPE_OUTRIGHT']},'last_game_dates':[e.get('startTime') for e in d['events'][-3:]]}))
first=json.loads((ROOT/'stages/03-build/output/nba-book-probe-20261021.json').read_text())
raw=Path(next(s['file'] for s in first['sources'] if s['name']=='bovada-page')).read_text(encoding='utf-8')
for marker in ['520937909','29468773','1.588235']:
    index=raw.find(marker);print(marker,raw[max(0,index-120):index+160])
