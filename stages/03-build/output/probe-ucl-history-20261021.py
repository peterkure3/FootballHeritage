import sys,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
OUT=ROOT/'pipeline/data/raw/ucl_history_20261021';OUT.mkdir(parents=True,exist_ok=True)
urls={
'viking_official':'https://www.vikingfotball.no/resultater',
'viking_terrikon':'https://terrikon.com/en/football/teams/1682',
'espn_bayern_html':'https://www.espn.com/soccer/team/results/_/id/132/season/2023/league/all',
'espn_bayern_all':'https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/132/schedule?season=2023&limit=1000',
'espn_bayern_league':'https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/teams/132/schedule?season=2023&limit=1000',
'espn_viking_all':'https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/510/schedule?season=2023&limit=1000',
}
def get(item):
    name,url=item;path=OUT/(name+'.raw')
    try:
        if path.exists():body=path.read_bytes();status=200
        else:
            r=ScraplingTransport().get(url,timeout=30);status=r.status_code;body=r.content
            if status==200:path.write_bytes(body)
        info={'name':name,'url':url,'status':status,'bytes':len(body),'captured_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat() if path.exists() else None,'sha256':hashlib.sha256(body).hexdigest()}
        try:
            p=json.loads(body);info['keys']=list(p);info['event_count']=len(p.get('events',[]));info['team']=p.get('team');info['first_events']=[{k:e.get(k) for k in ['id','date','name','season','leagues']} for e in p.get('events',[])[:2]]
        except Exception:pass
        print(json.dumps(info),flush=True);return info
    except Exception as exc:return {'name':name,'url':url,'error':type(exc).__name__}
urls={f'espn_2250_{year}':f'https://www.espn.com/soccer/team/results/_/id/2250/season/{year}/league/all' for year in range(2023,2027)}
urls.update({f'norway_cup_{year}':f'https://www.rsssf.no/{year}/Cup.html' for year in range(2022,2027)})
urls.update({'viking_madla_detail':'https://www.vikingfotball.no/resultater/kamp?id=9233641'})
urls.update({f'rsssf_{country}_{year}':f'https://www.rsssf.org/tables{letter}/{country}{year}.html' for country,letter in [('oost','o'),('belg','b'),('tur','t')] for year in range(2024,2028)})
urls.update({'lask_transfermarkt_current':'https://www.transfermarkt.com/lask/spielplan/verein/413/saison_id/2026'})
urls={f'tm_2282_{year}':f'https://www.transfermarkt.com/club-brugge-kv/spielplan/verein/2282/saison_id/{year}' for year in range(2023,2027)}
urls['tm_239_2022']='https://www.transfermarkt.com/viking-fk/spielplan/verein/239/saison_id/2022'
rows=list(ThreadPoolExecutor(max_workers=3).map(get,urls.items()))
(OUT/'supplement-manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
