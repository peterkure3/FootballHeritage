"""Refresh read-only prices and forecast all seven late fixtures with reviewed model."""
import hashlib
import importlib.util
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine,text
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from config import DATABASE_URI
from models.features import build_live_features
spec=importlib.util.spec_from_file_location('ucl_repair',OUT/'recalibrate-ucl-20261020.py')
repair=importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
now=datetime.now(timezone.utc)
directory=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020'
metrics=json.loads((directory/'metrics_v2.1.0.json').read_text(encoding='utf-8'))
assert 'calibration_review' in metrics,'Final calibration selection not complete'
assert hashlib.sha256((directory/'model_v2.1.0.pkl').read_bytes()).hexdigest()==metrics['model_sha256']
dataset=directory/'dataset.parquet'
assert hashlib.sha256(dataset.read_bytes()).hexdigest()==metrics['dataset_sha256']
history=pd.read_parquet(dataset)
model=joblib.load(directory/'model_v2.1.0.pkl')
engine=create_engine(DATABASE_URI,connect_args={'options':'-c default_transaction_read_only=on','connect_timeout':10})
classes=metrics['classes']
rows=[]
with engine.connect() as conn:
    fixtures=list(conn.execute(text("SELECT match_id,date,home_team,away_team FROM matches WHERE sport_type='football' AND date >= '2026-10-20 19:00:00' AND date < '2026-10-20 20:00:00' ORDER BY home_team")).mappings())
    for fixture in fixtures:
        row=dict(fixture)
        quotes=list(conn.execute(text("SELECT DISTINCT ON (bookmaker) bookmaker,home_win,draw,away_win,updated_at FROM odds WHERE match_id=:id AND updated_at <= :now AND updated_at < :kickoff AND home_win>1 AND draw>1 AND away_win>1 ORDER BY bookmaker,updated_at DESC,id DESC"),{'id':row['match_id'],'now':now,'kickoff':row['date']}).mappings())
        fresh=[q for q in quotes if (pd.Timestamp(now)-pd.Timestamp(q['updated_at'],tz='UTC')).total_seconds()<=1800]
        # A missing or stale quote uses the independently trained history expert.
        odds={c:float(np.mean([float(q[c]) for q in fresh])) for c in ['home_win','draw','away_win']} if fresh else None
        X=build_live_features(history,repair.reviewed_name(row['home_team']),repair.reviewed_name(row['away_team']),pd.Timestamp(row['date'],tz='UTC'),odds)
        with threadpool_limits(limits=2):
            probabilities=model.predict_proba(X)[0]
        assert np.isfinite(probabilities).all() and np.all(probabilities>0) and np.all(probabilities<1) and abs(probabilities.sum()-1)<1e-10
        row.update(probabilities=dict(zip(classes,map(float,probabilities))),probability_basis='market_and_history' if fresh else 'history_only_no_fresh_odds',
                   input_odds=odds,quotes=[dict(q) for q in quotes],fresh_quote_count=len(fresh),
                   fair_odds={c:1/float(probabilities[i]) for i,c in enumerate(classes)},
                   feature_vector=X.iloc[0].to_dict())
        if fresh:
            row['best_prices']={c:dict(price=max(float(q[c]) for q in fresh),bookmakers=[q['bookmaker'] for q in fresh if float(q[c])==max(float(x[c]) for x in fresh)]) for c in classes}
            row['gross_model_ev']={c:float(probabilities[i])*row['best_prices'][c]['price']-1 for i,c in enumerate(classes)}
        rows.append(row)
assert len(rows)==7,'Unexpected late fixture coverage'
result=dict(generated_at=now.isoformat(),candidate=str(directory),model_sha256=metrics['model_sha256'],active_model_replaced=False,
            quote_freshness_limit_seconds=1800,all_competition_history_complete=False,
            note='Experimental forecasts; all-competition coverage is not proven and market advantage is not established.',matches=rows)
path=OUT/'ucl-reviewed-forecasts-20261020.json'
path.write_text(json.dumps(result,indent=2,default=str,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(output=str(path),generated_at=result['generated_at'],matches=[{k:v for k,v in r.items() if k not in ['feature_vector','quotes']} for r in rows]),default=str,ensure_ascii=False),flush=True)
