import json,sys,time
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'pipeline'))
from etl.fetch_raw_data import FootballDataOrgFetcher
from etl.fetch_football_form import normalize_result
from config import FOOTBALL_DATA_ORG_API_KEY,FOOTBALL_DATA_ORG_BASE_URL
root=Path(__file__).resolve().parents[3]/'pipeline/data/raw/team_form/20261019'
report=json.loads((root/'form.json').read_text(encoding='utf-8'))
names={f[s+'_team'] for f in report['fixtures'] for s in ['home','away'] if f[s+'_form']['games']<5} | {'FC Porto'}
teams={m[s]['name']:m[s]['id'] for p in root.glob('*.json') if p.stem not in ['form','team_probe'] for m in json.loads(p.read_text(encoding='utf-8')).get('matches',[]) for s in ['homeTeam','awayTeam'] if m[s]['name'] in names}
f=FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY,FOOTBALL_DATA_ORG_BASE_URL)
summary=[]
for name,tid in teams.items():
    r=f.session.get(f'{f.base_url}/teams/{tid}/matches',headers=f.headers,params={'status':'FINISHED','limit':20},timeout=30)
    row=dict(team=name,status=r.status_code)
    if r.ok:
        d=r.json()
        (root/f'team_{tid}.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
        row['matches']=len(d.get('matches',[]))
        row['competitions']=sorted({m['competition']['code'] for m in d.get('matches',[])})
    summary.append(row)
    print(json.dumps(row),flush=True)
    (root/'team_probe.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    time.sleep(7)
