"""Recheck UEFA lineup payloads and their corresponding match metadata."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
OUT=ROOT/'pipeline/data/raw'/('ucl_confirmed_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));OUT.mkdir(parents=True)
http=ScraplingTransport()
def fetch(item):
    mid,kind=item;url=f'https://match.uefa.com/v5/matches/{mid}'+('/lineups' if kind=='lineups' else '')
    try:
        r=http.get(url,timeout=20);path=OUT/f'{mid}_{kind}.json';path.write_bytes(r.content)
        row={'match_id':mid,'kind':kind,'url':url,'status':r.status_code,'observed_at':datetime.now(timezone.utc).isoformat(),'headers':{k.lower():v for k,v in r.headers.items()},'sha256':hashlib.sha256(r.content).hexdigest(),'file':str(path)}
        data=r.json();row['keys']=list(data)[:40] if isinstance(data,dict) else type(data).__name__
    except Exception as e:row={'match_id':mid,'kind':kind,'url':url,'error':str(e)[:150]}
    print(json.dumps({k:v for k,v in row.items() if k not in ['headers','keys']}),flush=True);return row
rows=list(ThreadPoolExecutor(max_workers=5).map(fetch,[(mid,kind) for mid in range(2049598,2049605) for kind in ['lineups','metadata']]))
(OUT/'audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
(ROOT/'stages/03-build/output/ucl-confirmed-inputs-20261021.json').write_text(json.dumps({'capture':str(OUT),'generated_at':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
print(json.dumps({'capture':str(OUT)}),flush=True)
