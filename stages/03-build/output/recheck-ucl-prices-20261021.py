"""Refresh five readable books and preserve HTTP cache metadata."""
import sys,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
from etl.scrape_sportsbooks import collect_target
OUT=ROOT/'pipeline/data/raw/ucl_today_20261021_recheck';(OUT/'raw').mkdir(parents=True,exist_ok=True)
old=json.loads((ROOT/'pipeline/data/raw/ucl_today_20261021_all_public/source_report.json').read_text())
targets=[r for r in old['direct_sources'] if r['bookmaker'] in {'bovada','cloudbet','betpawa','ababet','bookmaker'}]
class AuditTransport(ScraplingTransport):
    def __init__(self):super().__init__();self.audit=[]
    def get(self,url,**kwargs):
        r=super().get(url,**kwargs)
        self.audit.append({'url':r.url,'observed_at':datetime.now(timezone.utc).isoformat(),'status':r.status_code,'headers':{k:r.headers.get(k) for k in ['Date','Age','Cache-Control','ETag','Last-Modified']}})
        return r
def run(target):
    http=AuditTransport();r=collect_target(target,OUT,http=http);r['http_audit']=http.audit;return r
rows=list(ThreadPoolExecutor(max_workers=3).map(run,targets))
(OUT/'cache-audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
from etl.scrape_sportsbooks import normalize_saved_run
old['direct_sources']=rows;old['run_id']='ucl-price-recheck-20261021T1436Z'
(OUT/'source_report.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
(OUT/'odds_snapshots.jsonl').write_text('',encoding='utf-8')
normalize_saved_run(OUT)
