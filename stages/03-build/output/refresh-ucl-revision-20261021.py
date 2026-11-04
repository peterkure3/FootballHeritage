"""Fresh public prices with cache evidence; preserve every earlier capture."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
from etl.scrape_sportsbooks import collect_target,normalize_saved_run
now=datetime.now(timezone.utc);OUT=ROOT/'pipeline/data/raw'/('ucl_revision_'+now.strftime('%Y%m%dT%H%M%SZ'));(OUT/'raw').mkdir(parents=True)
old=json.loads((ROOT/'pipeline/data/raw/ucl_today_20261021_all_public/source_report.json').read_text())
targets=[r for r in old['direct_sources'] if r['bookmaker'] in {'bovada','cloudbet','betpawa','ababet','bookmaker'}]
class AuditTransport(ScraplingTransport):
    def __init__(self):super().__init__();self.audit=[]
    def get(self,url,**kwargs):
        r=super().get(url,**kwargs)
        self.audit.append({'url':r.url,'observed_at':datetime.now(timezone.utc).isoformat(),'status':r.status_code,'headers':{k:r.headers.get(k) for k in ['Date','Age','Cache-Control','Last-Modified','ETag']},'sha256':hashlib.sha256(r.content).hexdigest()})
        return r
def run(target):
    http=AuditTransport();row=collect_target(target,OUT,http=http);row['http_audit']=http.audit
    print(json.dumps({'bookmaker':row['bookmaker'],'status':row['status'],'observed_at':row.get('observed_at')}),flush=True)
    return row
rows=list(ThreadPoolExecutor(max_workers=3).map(run,targets))
(OUT/'cache-audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
old['direct_sources']=rows;old['run_id']=OUT.name
(OUT/'source_report.json').write_text(json.dumps(old,indent=2),encoding='utf-8');(OUT/'odds_snapshots.jsonl').write_text('',encoding='utf-8')
report=normalize_saved_run(OUT)
pointer={'capture':str(OUT),'generated_at':datetime.now(timezone.utc).isoformat(),'snapshots':report['snapshot_count']}
(ROOT/'stages/03-build/output/ucl-revision-inputs-20261021.json').write_text(json.dumps(pointer,indent=2),encoding='utf-8')
print(json.dumps(pointer),flush=True)
