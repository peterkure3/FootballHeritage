from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport,USER_AGENT
output=ROOT/'pipeline/data/raw/nba_public'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');output.mkdir(parents=True)
http=ScraplingTransport()
sources={
 'cloudbet-markets':('https://www.cloudbet.com/sports-api/c/v6/sports/competitions/basketball-usa-nba/events',{'params':{'from':str(int(datetime.now(timezone.utc).timestamp())),'limit':100,'locale':'en','markets':'basketball.moneyline','sports':'basketball','include-all-event-types':'false','include-pretrading':'false'}}),
 'pawa-nba':('https://www.betpawa.ug/api/sportsbook/v4/events/lists/by-queries',{'params':{'q':json.dumps({'queries':[{'query':{'eventType':'UPCOMING','categories':['3'],'zones':{'competitions':['11971']},'hasOdds':True},'sort':{'startTime':'ASC'},'take':100}]})}}),
 'betika-sports':('https://api-ug.betika.com/v1/uo/sports',{}),
 'betika-nba':('https://api-ug.betika.com/v1/uo/matches',{'params':{'page':1,'limit':100,'sport_id':'30','competition_id':'9207','sort_id':2,'esports':'false'}}),
}
def run(item):
    name,(url,kwargs)=item;row={'name':name,'url':url}
    try:
        response=http.get(url,timeout=25,headers={'User-Agent':USER_AGENT,'X-Pawa-Brand':'betpawa-uganda','X-Pawa-Language':'en','x-cloudbet-version':'v1.2.27','Accept':'application/json'},**kwargs)
        path=output/(name+'.raw');path.write_bytes(response.content)
        row.update(status=response.status_code,file=str(path),captured_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(response.content).hexdigest())
        data=response.json()
        if name=='pawa-nba': row['data']={'sample':[e for batch in data.get('responses',[]) for e in batch.get('responses',[])][:1]}
        elif name=='betika-sports': row['data']={'basketball':[r for r in data.get('data',[]) if 'basket' in str(r).lower()]}
        elif name=='betika-nba': row['data']={'meta':data.get('meta'),'sample':data.get('data',[])[:1]}
        else:
            row['data']={'events':len(data.get('events',[])),'sample':next((e for e in data.get('events',[]) if e.get('status')=='TRADING' and e.get('type')=='EVENT_TYPE_EVENT'),{})}
    except Exception as exc: row['error']=type(exc).__name__
    print(json.dumps(row),flush=True);return row
with ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(run,sources.items()))
(output/'manifest.json').write_text(json.dumps({'sources':[{k:v for k,v in r.items() if k!='data'} for r in rows]},indent=2))
(ROOT/'stages/03-build/output/nba-market-probe-20261021.json').write_text(json.dumps({'output':str(output),'sources':rows},indent=2))
