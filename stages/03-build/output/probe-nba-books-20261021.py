"""Capture public NBA pages/feeds with Scrapling; record access failures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport,USER_AGENT

output=ROOT/'pipeline/data/raw/nba_public'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
output.mkdir(parents=True)
http=ScraplingTransport()
sources={
 'bovada-page':'https://www.bovada.lv/sports/basketball/nba',
 'bovada-feed':'https://www.bovada.lv/services/sports/event/coupon/events/A/description/basketball/nba?marketFilterId=def&preMatchOnly=true',
 'cloudbet-page':'https://www.cloudbet.com/en/sports/basketball',
 'cloudbet-feed':'https://www.cloudbet.com/sports-api/c/v6/sports/competitions/basketball-usa-nba/events?limit=100&locale=en',
 'betpawa-page':'https://www.betpawa.ug/',
 'betpawa-directory':'https://www.betpawa.ug/api/sportsbook/v4/categories/list',
 'betika-page':'https://www.betika.com/en-ug/',
 'betika-sports':'https://api.betika.com/v1/sports',
}
def capture(item):
    name,url=item
    row={'name':name,'url':url,'transport':'scrapling'}
    try:
        headers={'User-Agent':USER_AGENT,'Accept':'application/json,text/html'}
        if name.startswith('cloudbet'): headers['x-cloudbet-version']='v1.2.27'
        if name.startswith('betpawa'): headers.update({'X-Pawa-Brand':'betpawa-uganda','X-Pawa-Language':'en'})
        response=http.get(url,headers=headers,timeout=25)
        raw=output/(name+'.raw'); raw.write_bytes(response.content)
        row.update(status=response.status_code,bytes=len(response.content),captured_at=datetime.now(timezone.utc).isoformat(),
                   file=str(raw),sha256=hashlib.sha256(response.content).hexdigest())
        try:
            data=response.json()
            row['shape']=list(data)[:15] if isinstance(data,dict) else 'list:'+str(len(data))
        except ValueError: pass
    except Exception as exc: row['error']=type(exc).__name__
    print(json.dumps(row),flush=True)
    return row
with ThreadPoolExecutor(max_workers=3) as executor: rows=list(executor.map(capture,sources.items()))
manifest={'output':str(output),'sources':rows}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'stages/03-build/output/nba-book-probe-20261021.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
