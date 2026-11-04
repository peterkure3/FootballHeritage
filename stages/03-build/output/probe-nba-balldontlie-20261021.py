"""Credential-safe, bounded NBA entitlement checks; never persist headers."""
from datetime import datetime,timezone,timedelta
import hashlib,json,time
from pathlib import Path
from dotenv import dotenv_values
import requests

ROOT=Path(__file__).resolve().parents[3]
key=dotenv_values(ROOT/'pipeline/.env').get('BALLDONTLIE_API_KEY')
if not key: raise SystemExit('BALLDONTLIE_API_KEY is not configured')
now=datetime.now(timezone.utc)
directory=ROOT/'pipeline/data/raw/balldontlie'/now.strftime('%Y%m%dT%H%M%S%fZ')
directory.mkdir(parents=True)
checks=[]
start=(now-timedelta(days=1)).date().isoformat(); end=(now+timedelta(days=2)).date().isoformat()
for name,path,params in [
 ('games','/v1/games',{'start_date':start,'end_date':end,'per_page':100}),
 ('odds','/nba/v2/odds',{'dates[]':now.date().isoformat(),'per_page':100}),
 ('odds-documented','/v2/odds',{'dates[]':now.date().isoformat(),'per_page':100}),
 ('opening','/nba/v2/odds/opening',{'dates[]':now.date().isoformat(),'per_page':1})]:
    row={'name':name,'url':'https://api.balldontlie.io'+path,'params':params}
    try:
        response=requests.get(row['url'],params=params,headers={'Authorization':key},timeout=35)
        row['status']=response.status_code
        raw=response.text.replace(key,'[REDACTED]').encode()
        (directory/(name+'.json')).write_bytes(raw)
        try: data=json.loads(raw)
        except json.JSONDecodeError: data={'error':raw.decode()[:160]}
        row.update(status=response.status_code,records=len(data.get('data',[])),meta=data.get('meta'),
                   error=data.get('error') or data.get('message'),sha256=hashlib.sha256(raw).hexdigest())
    except Exception as exc: row['error']=type(exc).__name__
    checks.append(row); print(json.dumps(row),flush=True)
    if name!='opening': time.sleep(13)
report={'captured_at':now.isoformat(),'directory':str(directory),'checks':checks}
(directory/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(ROOT/'stages/03-build/output/nba-balldontlie-access-20261021.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
