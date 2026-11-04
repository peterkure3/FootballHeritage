import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
manifest=json.loads((ROOT/'stages/03-build/output/nba-book-probe-20261021.json').read_text())
raw={r['name']:Path(r['file']) for r in manifest['sources'] if r.get('status')==200}
bov=json.loads(raw['bovada-feed'].read_text())
print('BOVADA',json.dumps([{'path':g.get('path'),'events':len(g.get('events',[])),
 'sample':[{k:v for k,v in e.items() if k not in ['displayGroups','notes','scoreboard','statistics']}
           for e in g.get('events',[])[:2]],
 'markets':[{k:v for k,v in m.items()} for e in g.get('events',[])[:1] for d in e.get('displayGroups',[]) for m in d.get('markets',[])]} for g in bov]))
cloud=json.loads(raw['cloudbet-feed'].read_text())
print('CLOUDBET',json.dumps({**{k:v for k,v in cloud.items() if k!='events'},'events':len(cloud.get('events',[])),
 'sample':cloud.get('events',[])[:1]}))
print('PAWA',raw['betpawa-directory'].read_text())
data=json.loads(raw['betika-sports'].read_text())
print('BETIKA',json.dumps([r for r in data.get('data',[]) if 'basket' in str(r).lower()]))
