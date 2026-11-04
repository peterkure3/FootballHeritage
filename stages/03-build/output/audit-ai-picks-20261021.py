"""Read-only audit of live AI Picks, saved runs and model/price consistency."""
import sys,json,math,hashlib
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import requests
from sqlalchemy import create_engine,text
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from config import DATABASE_URI,MODEL_VERSION,MODEL_DIR,MODEL_NAME
from api.ai_picks import build_picks
now=datetime.now(timezone.utc)
endpoints={
'pipeline_picks_today':'http://127.0.0.1:5555/api/v1/ai-picks?date=2026-10-21&limit=20',
'pipeline_picks_ucl':'http://127.0.0.1:5555/api/v1/ai-picks?competition=Champions%20League&date=2026-10-21&limit=20',
'football_intelligence':'http://127.0.0.1:5555/api/v1/betting-intel/football',
'intelligence_overview':'http://127.0.0.1:5555/api/v1/betting-intel',
'backend_picks_auth_status':'http://127.0.0.1:8888/api/v1/ai-picks',
'frontend_status':'http://127.0.0.1:5173/ai-picks',
}
def get(item):
    label,url=item
    try:
        r=requests.get(url,timeout=(3,10));result={'url':url,'status':r.status_code,'observed_at':datetime.now(timezone.utc).isoformat()}
        if 'json' in r.headers.get('content-type',''):result['body']=r.json()
        else:result['body_summary']=r.text[:120]
    except requests.RequestException as exc:result={'url':url,'error':type(exc).__name__}
    print(json.dumps({'endpoint':label,'status':result.get('status'),'error':result.get('error')}),flush=True)
    return label,result
http=dict(ThreadPoolExecutor(max_workers=5).map(get,endpoints.items()))
def engine(url):return create_engine(url,connect_args={'options':'-c default_transaction_read_only=on -c statement_timeout=12000','connect_timeout':5})
query="""
SELECT m.match_id,m.home_team,m.away_team,m.competition,m.date AT TIME ZONE 'UTC' AS match_date,m.status,m.result,
 p.home_prob,p.draw_prob,p.away_prob,p.model_version,p.created_at AT TIME ZONE 'UTC' AS prediction_created_at,
 COALESCE(q.quotes,'[]'::json) AS quotes
FROM matches m LEFT JOIN LATERAL (
 SELECT * FROM predictions p WHERE p.match_id=m.match_id AND p.model_version=:version
 ORDER BY p.created_at DESC,p.id DESC LIMIT 1
) p ON TRUE LEFT JOIN LATERAL (
 SELECT json_agg(latest) AS quotes FROM (
 SELECT DISTINCT ON (o.bookmaker) o.bookmaker,o.home_win,o.draw,o.away_win,o.updated_at AT TIME ZONE 'UTC' AS updated_at
 FROM odds o WHERE o.match_id=m.match_id ORDER BY o.bookmaker,o.updated_at DESC,o.id DESC
 ) latest
) q ON TRUE
WHERE m.date>='2026-10-21' AND m.date<'2026-10-22' AND m.sport_type='football'
 AND m.competition ILIKE '%Champions%' ORDER BY m.date,m.home_team
"""
db={}
try:
    eng=engine(DATABASE_URI)
    with eng.connect() as conn:
        db['today_ucl']=[dict(r) for r in conn.execute(text(query),{'version':MODEL_VERSION}).mappings()]
        db['prediction_versions_today']=[dict(r) for r in conn.execute(text("SELECT p.model_version,COUNT(*) AS rows,MAX(p.created_at) AS latest FROM predictions p JOIN matches m ON p.match_id=m.match_id WHERE m.date>='2026-10-21' AND m.date<'2026-10-22' AND m.competition ILIKE '%Champions%' GROUP BY p.model_version")).mappings()]
        db['server_time']=str(conn.execute(text('SELECT NOW()')).scalar())
except Exception as exc:db['error']=type(exc).__name__
backend={}
try:
    values=dotenv_values(ROOT/'backend/.env');url=values.get('DATABASE_URL')
    if not url:backend['error']='DATABASE_URL_not_configured'
    else:
        eng=engine(url)
        with eng.connect() as conn:
            backend['saved_runs']=[dict(r) for r in conn.execute(text("SELECT sport,competition,requested_date,model_version,provenance,results,created_at FROM ai_pick_runs ORDER BY created_at DESC LIMIT 12")).mappings()]
except Exception as exc:backend['error']=type(exc).__name__
checks=[]
def validate_pick(p,context):
    problems=[];prob=p.get('model_prob');odds=p.get('decimal_odds')
    if not isinstance(prob,(int,float)) or not math.isfinite(prob) or not 0<=prob<=1:problems.append('invalid_probability')
    if prob in [0,1]:problems.append('extreme_zero_or_one_probability')
    if odds is not None and isinstance(prob,(int,float)):
        expected=prob*odds-1;edge=prob-1/odds
        if p.get('expected_value') is None or abs(p['expected_value']-expected)>1e-8:problems.append('expected_value_mismatch')
        if p.get('edge_pct') is None or abs(p['edge_pct']-100*edge)>1e-8:problems.append('edge_mismatch')
        if p.get('pick_type')=='value' and edge<.05-1e-9:problems.append('value_threshold_mismatch')
    for field in ['match_date','prediction_created_at','odds_updated_at']:
        value=p.get(field)
        if value:
            try:
                dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
                if dt.tzinfo is None:problems.append(field+'_timezone_missing');dt=dt.replace(tzinfo=timezone.utc)
                if field=='match_date' and dt<=now:problems.append('fixture_already_started')
                if field=='odds_updated_at' and (now-dt).total_seconds()>1800:problems.append('odds_older_than_30_minutes')
            except ValueError:problems.append(field+'_invalid')
    checks.append({'context':context,'match_id':p.get('match_id'),'fixture':f"{p.get('home_team')} – {p.get('away_team')}",'selection':p.get('selection'),'probability':prob,'odds':odds,'model_version':p.get('model_version'),'issues':problems})
for label in ['pipeline_picks_today','pipeline_picks_ucl']:
    for p in http.get(label,{}).get('body',{}).get('picks',[]):validate_pick(p,label)
for i,run in enumerate(backend.get('saved_runs',[])):
    for p in run.get('results') or []:validate_pick(p,'saved_run_'+str(i))
snapshot=ROOT/'pipeline/data/processed/betting_intel/snapshot.json';snapshot_info={}
if snapshot.exists():
    payload=json.loads(snapshot.read_text());snapshot_info={'snapshot_at':payload.get('snapshot_at'),'model_policy':payload.get('model_policy'),'source_errors':payload.get('source_errors'),'fixtures':len(payload.get('fixtures',[])),'football':[f for f in payload.get('fixtures',[]) if f.get('sport')=='football' and str(f.get('kickoff','')).startswith('2026-10-21')]}
result={'audit_at':now.isoformat(),'configured_model_version':MODEL_VERSION,'configured_model_file':str(MODEL_DIR/MODEL_NAME),'http':http,'pipeline_db':db,'backend_db':backend,'pick_checks':checks,'snapshot':snapshot_info,'database_writes':False}
(OUT/'ai-picks-live-audit-20261021.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps({'audit_at':result['audit_at'],'configured_model_version':MODEL_VERSION,'pipeline_db_error':db.get('error'),'backend_db_error':backend.get('error'),'ucl_rows':len(db.get('today_ucl',[])),'versions':db.get('prediction_versions_today'),'saved_runs':len(backend.get('saved_runs',[])),'pick_checks':checks},default=str),flush=True)
