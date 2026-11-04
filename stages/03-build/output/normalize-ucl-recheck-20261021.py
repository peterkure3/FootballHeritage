import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrape_sportsbooks import normalize_saved_run
out=ROOT/'pipeline/data/raw/ucl_today_20261021_recheck'
report=json.loads((ROOT/'pipeline/data/raw/ucl_today_20261021_all_public/source_report.json').read_text())
report['direct_sources']=json.loads((out/'cache-audit.json').read_text());report['run_id']='ucl-price-recheck-20261021T1436Z'
(out/'source_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(out/'odds_snapshots.jsonl').write_text('',encoding='utf-8')
r=normalize_saved_run(out);print(r['snapshots_by_bookmaker'])
