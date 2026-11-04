"""Capture official European results with explicit regulation-time score rules."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL
from etl.fetch_raw_data import FootballDataOrgFetcher
from etl.fetch_football_form import normalize_result
out=ROOT/'pipeline/data/raw/ucl_history_20261020'
fetcher=FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY,FOOTBALL_DATA_ORG_BASE_URL)
rows=[]
sources=[]
now=datetime.now(timezone.utc)
for competition in ['CL','EL','ECL','FAC','DFB','CDR','CIT']:
    for season in [2023,2024,2025,2026]:
        path=out/f'official_{competition}_{season}.json'
        if path.exists():
            payload=json.loads(path.read_text(encoding='utf-8'))
            status=200
        else:
            try:
                r=fetcher.session.get(f'{fetcher.base_url}/competitions/{competition}/matches',headers=fetcher.headers,params={'season':season,'status':'FINISHED'},timeout=25)
                status=r.status_code
                payload=r.json() if r.ok else {}
                if r.ok:
                    path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            except Exception as exc:
                status=type(exc).__name__
                payload={}
            time.sleep(7)
        accepted=0
        for match in payload.get('matches',[]):
            row=normalize_result(match,now)
            if row and pd.Timestamp(row['date']) < pd.Timestamp('2026-10-20',tz='UTC'):
                row['data_source']='football-data.org:official-europe'
                row['score_basis']='explicit_provider_regulation_score'
                rows.append(row)
                accepted+=1
        sources.append(dict(competition=competition,season=season,status=status,matches=len(payload.get('matches',[])),accepted=accepted))
        print(json.dumps(sources[-1]),flush=True)
        (out/'europe_manifest.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
        if status in [400,401,403,404]:
            break
if rows:
    pd.DataFrame(rows).drop_duplicates('provider_match_id').to_csv(out/'europe_results.csv',index=False)
print(json.dumps({'accepted':len(rows)}),flush=True)
