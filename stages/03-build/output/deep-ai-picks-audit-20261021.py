"""Reproduce active-model pathology and settle the latest completed saved run."""
import sys,json,hashlib,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from sqlalchemy import create_engine,text
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from config import DATABASE_URI,MODEL_DIR,MODEL_VERSION
from models.predict_v2 import load_model_artifacts,build_feature_vector,get_team_elo_ratings
from etl.fetch_football_form import normalize_result
audit=json.loads((OUT/'ai-picks-live-audit-20261021.json').read_text());now=datetime.now(timezone.utc)
engine=create_engine(DATABASE_URI,connect_args={'options':'-c default_transaction_read_only=on -c statement_timeout=15000','connect_timeout':5})
model,encoder,features,scaler=load_model_artifacts()
elo=get_team_elo_ratings(engine)
test=next(m for m in audit['pipeline_db']['today_ucl'] if m['match_id']==575372)
X=build_feature_vector(test['home_team'],test['away_team'],engine,elo,None,features,cutoff=pd.Timestamp('2026-10-21T15:57:00Z'))
if scaler is not None:X=pd.DataFrame(scaler.transform(X),columns=X.columns)
with threadpool_limits(limits=2):p=model.predict_proba(X)[0]
diagnostic={'class':type(model).__name__,'features':len(features),'classes':list(encoder.classes_),'model_sha256':hashlib.sha256((MODEL_DIR/f'model_v{MODEL_VERSION}.pkl').read_bytes()).hexdigest(),'bayern_reproduced':dict(zip(encoder.classes_,map(float,p))),'bayern_stored':{c:test[c.replace('_win','')+'_prob'] if c!='draw' else test['draw_prob'] for c in []},'feature_vector':X.iloc[0].to_dict()}
diagnostic['bayern_stored']={c:test[k] for c,k in [('home_win','home_prob'),('draw','draw_prob'),('away_win','away_prob')]}
diagnostic['matches_stored']=all(abs(diagnostic['bayern_reproduced'][c]-v)<1e-9 for c,v in diagnostic['bayern_stored'].items())
try:
    calibrated=model.calibrated_classifiers_[0];response=calibrated.estimator.decision_function(X)[0]
    diagnostic['calibrators']=[{'class':str(encoder.classes_[i]),'base_response':float(response[i]),'calibrated_value':float(cal.predict([response[i]])[0]),'input_min':float(cal.X_min_),'input_max':float(cal.X_max_)} for i,cal in enumerate(calibrated.calibrators)]
except (AttributeError,TypeError,IndexError) as exc:diagnostic['calibrator_error']=type(exc).__name__
with engine.connect() as conn:
    diagnostic['date_column_type']=conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name='matches' AND column_name='date'")).scalar()
    diagnostic['timezone']=conn.execute(text('SHOW TIMEZONE')).scalar()
    diagnostic['upcoming_filter_counts']=dict(conn.execute(text("SELECT COUNT(*) FILTER(WHERE date>NOW()) AS legacy_now_count,COUNT(*) FILTER(WHERE date>(NOW() AT TIME ZONE 'UTC')) AS utc_now_count FROM matches WHERE date>='2026-10-21' AND date<'2026-10-22' AND competition ILIKE '%Champions%' AND sport_type='football'")).mappings().one())
    diagnostic['team_history_counts']={t:dict(conn.execute(text("SELECT COUNT(*) AS result_rows,MAX(date) AS latest FROM matches WHERE result IS NOT NULL AND sport_type='football' AND (home_team ILIKE :t OR away_team ILIKE :t)"),{'t':'%'+t+'%'}).mappings().one()) for t in ['Club Brugge KV','Racing Club de Lens','FC Bayern München','FC Internazionale Milano','FK Shakhtar Donetsk']}
payload=json.loads((ROOT/'pipeline/data/raw/team_form/ucl_20261021/CL.json').read_text());results={}
for match in payload.get('matches',[]):
    row=normalize_result(match,now)
    if row:results[str(match['id'])]=row
completed=[]
for run in audit['backend_db'].get('saved_runs',[]):
    picks=run.get('results') or []
    if not picks or not all(str(pick['match_id']) in results for pick in picks):continue
    settled=[]
    for pick in picks:
        result=results[str(pick['match_id'])];selection='draw' if pick['selection']=='Draw' else 'home_win' if '(Home Win)' in pick['selection'] else 'away_win'
        actual='home_win' if result['home_score']>result['away_score'] else 'away_win' if result['home_score']<result['away_score'] else 'draw';won=selection==actual;odds=pick.get('decimal_odds')
        pre_match=pd.Timestamp(pick['prediction_created_at'])<pd.Timestamp(result['date']) and pd.Timestamp(run['created_at'])<pd.Timestamp(result['date'])
        settled.append({'fixture':pick['home_team']+' – '+pick['away_team'],'selection':pick['selection'],'score':f"{result['home_score']}–{result['away_score']}",'won':won,'decimal_odds':odds,'paper_profit_one_unit':odds-1 if won and odds else -1 if odds else None,'pre_match':pre_match})
    quoted=[s for s in settled if s['paper_profit_one_unit'] is not None]
    completed.append({'run_created_at':run['created_at'],'requested_date':run['requested_date'],'model_version':run['model_version'],'wins':sum(s['won'] for s in settled),'picks':len(settled),'paper_quoted_picks':len(quoted),'paper_profit':sum(s['paper_profit_one_unit'] for s in quoted),'settled':settled,'source':'football-data.org completed REGULAR/regularTime scores captured 2026-10-21 before today’s fixtures'})
    break
diagnostic['latest_completed_saved_run']=completed[0] if completed else None
diagnostic['audit_at']=now.isoformat();diagnostic['database_writes']=False
(OUT/'ai-picks-deep-audit-20261021.json').write_text(json.dumps(diagnostic,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in diagnostic.items() if k!='feature_vector'},default=str),flush=True)
