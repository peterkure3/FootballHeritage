"""Replay the immutable 25 October forecast and its saved training history."""
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from models.league_data import identity,identity_aliases
from models.predict_football_leagues import league_state
from models.features import FEATURE_NAMES
from models.training_resources import training_threads

run=ROOT/'pipeline/models/model_store/league_models/20261025T165351114106Z'
report=json.loads((run/'report.json').read_text(encoding='utf-8'))
metrics=report['leagues']['PD']
for filename in ['model.pkl','dataset.parquet']:
    assert hashlib.sha256((run/'PD'/filename).read_bytes()).hexdigest()==metrics[filename.replace('.','_')+'_sha256']
saved=json.loads(next(run.glob('forecasts_*.json')).read_text(encoding='utf-8'))
forecast=next(row for row in saved['predictions'] if row['home_team']=='FC Barcelona' and row['away_team']=='Real Madrid CF')
history=pd.read_parquet(run/'PD/dataset.parquet')
cutoff=pd.Timestamp(forecast['feature_cutoff'])
aliases=identity_aliases(run/'league_identities.json')
home,away=[identity(forecast[side+'_team'],aliases) for side in ['home','away']]
state=league_state(history,cutoff)
vector=state.vector(home,away)
with training_threads(2):
    probabilities=joblib.load(run/'PD/model.pkl').predict_proba(pd.DataFrame([vector],columns=FEATURE_NAMES))[0]
replay=dict(zip(metrics['classes'],probabilities.tolist()))
np.testing.assert_allclose(list(replay.values()),[forecast['probabilities'][key] for key in replay],atol=1e-12)
form={}
for side,team in [('home',home),('away',away)]:
    rows=history[(history.home_key.eq(team)|history.away_key.eq(team)) & history.date.lt(cutoff.normalize())].tail(5)
    matches=[]
    for row in rows.to_dict('records'):
        is_home=row['home_key']==team
        result=row['result']
        outcome='D' if result=='draw' else 'W' if (result=='home_win')==is_home else 'L'
        matches.append({'date':row['date'].isoformat(),'opponent':row['away_team'] if is_home else row['home_team'],
                       'venue':'home' if is_home else 'away','result':outcome,
                       'goals_for':int(row['home_score'] if is_home else row['away_score']),
                       'goals_against':int(row['away_score'] if is_home else row['home_score'])})
    form[side]={'sequence_oldest_first':''.join(row['result'] for row in matches),'matches':matches}
payload={'forecast':forecast,'replayed_probabilities':replay,'replay_matches':True,
         'scope':'Saved league history; not all-competition form. Same-day results excluded.',
         'form':form,'used_features':metrics['used_features'],
         'feature_vector':{key:float(value) for key,value in vector.items()}}
output=Path(__file__).parent/'clasico-form-audit-20261026.json'
output.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'replay_matches':True,'probabilities':replay,
    'home_form':form['home']['sequence_oldest_first'],'away_form':form['away']['sequence_oldest_first']},indent=2))
