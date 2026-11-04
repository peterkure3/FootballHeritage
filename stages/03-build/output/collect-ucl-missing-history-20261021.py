"""Bounded, resumable public history capture for all 18 UCL clubs."""
import sys,json,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
OUT=ROOT/'pipeline/data/raw/ucl_history_20261021';OUT.mkdir(parents=True,exist_ok=True)
TEAMS={'Como':2572,'Man United':360,'Lille':166,'Galatasaray':432,'Aston Villa':362,'Viking':510,'Club Brugge':570,'Lens':175,'Bayern Munich':132,'Arsenal':359,'Inter':110,'Shakhtar Donetsk':493,'Real Madrid':86,'RB Leipzig':11420,'Betis':244,'Feyenoord':142,'Sp Lisbon':225,'LASK Linz':4411}
TEAMS['Sp Lisbon']=2250
http=ScraplingTransport()
jobs=[{'name':f'espn_{tid}_{season}','team':team,'provider_id':tid,'season':season,'url':f'https://www.espn.com/soccer/team/results/_/id/{tid}/season/{season}/league/all'} for team,tid in TEAMS.items() for season in range(2023,2027)]
jobs += [{'name':f'fd_{season}_{league}','url':f'https://football-data.co.uk/mmz4281/{season}/{league}.csv'} for season in ['2324','2425','2526','2627'] for league in ['A1','B1','I2']]
if '--transfermarkt-only' in sys.argv:
    tmids={'Como':1047,'Man United':985,'Lille':1082,'Galatasaray':141,'Aston Villa':405,'Viking':239,'Club Brugge':228,'Lens':826,'Bayern Munich':27,'Arsenal':11,'Inter':46,'Shakhtar Donetsk':660,'Real Madrid':418,'RB Leipzig':23826,'Betis':150,'Feyenoord':234,'Sp Lisbon':336,'LASK Linz':413}
    jobs=[{'name':f'tm_{tid}_{season}','team':team,'provider_id':tid,'season':season,'url':f'https://www.transfermarkt.com/club/spielplan/verein/{tid}/saison_id/{season}'} for team,tid in tmids.items() for season in range(2023,2027)]
def run(job):
    path=OUT/(job['name']+'.raw');row=job.copy()
    try:
        if path.exists():body=path.read_bytes();status=200;row['cached_local']=True
        else:
            r=http.get(job['url'],timeout=30);body=r.content;status=r.status_code
            if status==200:path.write_bytes(body)
            time.sleep(.35)
        row.update(status=status,bytes=len(body))
        if path.exists():row.update(file=path.name,sha256=hashlib.sha256(body).hexdigest(),captured_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat())
    except Exception as exc:row.update(error=type(exc).__name__)
    print(json.dumps({k:row[k] for k in ['name','status','bytes','error'] if k in row}),flush=True)
    return row
rows=list(ThreadPoolExecutor(max_workers=3).map(run,jobs))
(OUT/('transfermarkt-manifest.json' if '--transfermarkt-only' in sys.argv else 'collection-manifest.json')).write_text(json.dumps({'completed_at':datetime.now(timezone.utc).isoformat(),'teams':TEAMS,'sources':rows},indent=2),encoding='utf-8')
print(json.dumps({'attempted':len(rows),'ok':sum(r.get('status')==200 for r in rows),'output':str(OUT)}),flush=True)
