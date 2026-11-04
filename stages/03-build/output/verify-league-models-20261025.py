"""Verify published league forecasts through the authenticated HTTP API."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import requests

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from config import MODEL_DIR, PROCESSED_DATA_DIR
from football_competitions import LEAGUES

registry=json.loads((MODEL_DIR/'league_models/serving.json').read_text(encoding='utf-8'))
run=MODEL_DIR/'league_models'/registry['run_directory']
models=json.loads((run/'report.json').read_text(encoding='utf-8'))
published=json.loads((PROCESSED_DATA_DIR/'league_predictions.json').read_text(encoding='utf-8'))
assert len(models['leagues'])==8
headers={'x-internal-token':os.getenv('PIPELINE_INTERNAL_TOKEN','')}
assert published['run_id']==run.name
summary={'verified_at':datetime.now(timezone.utc).isoformat(),'run_id':run.name,'leagues':{},'published_forecasts':len(published['predictions'])}
for code,metrics in models['leagues'].items():
    for filename in ['model.pkl','dataset.parquet']:
        assert hashlib.sha256((run/code/filename).read_bytes()).hexdigest()==metrics[filename.replace('.','_')+'_sha256']
    competition=next(row[1] for row in LEAGUES if row[0]==code)
    response=requests.get('http://127.0.0.1:5567/api/v1/prediction-dashboard/fixtures',
        params={'competition':competition,'page_size':50},headers=headers,timeout=30)
    response.raise_for_status()
    data=response.json()
    assert len(data['competitions'])==10
    assert len(data['items'])==data['total_count']
    for item in data['items']:
        prediction=item['prediction']
        assert prediction['model_version']==f'league-{code}-{run.name}'
        assert prediction['model_kind']=='evaluated_league_candidate' and prediction['status']=='current'
        assert not prediction['active']
        assert abs(sum(prediction['probabilities'].values())-1)<1e-9
        for comparison in item['market']['comparisons']:
            expected=prediction['probabilities'][comparison['outcome']]*comparison['decimal_odds']-1
            assert abs(expected-comparison['estimated_ev_units'])<1e-9
    summary['leagues'][code]={'competition':competition,'http_status':response.status_code,
        'upcoming_forecasts':data['total_count'], 'fixtures_with_fresh_quotes':sum(
            any(quote['fresh'] for quote in item['market']['quotes']) for item in data['items']),
        'history_games':metrics['training_games'],'test':{key:metrics['test'][key] for key in ['samples','accuracy','log_loss','brier_score']},
        'prior_baseline_log_loss':metrics['test_development_prior']['log_loss']}
    if code=='PD':
        (Path(__file__).parent/'league-grid-api-final-20261025.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
output=Path(__file__).parent
assert json.loads((PROCESSED_DATA_DIR/'league_predictions.json').read_text(encoding='utf-8'))['run_id']==run.name
(output/'league-models-verification-20261025.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
with (output/'league-predictions-20261025.csv').open('w',encoding='utf-8',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=['competition','home_team','away_team','kickoff','home_win','draw','away_win','winner','model_version','generated_at'])
    writer.writeheader()
    for row in published['predictions']:
        writer.writerow({key:row[key] for key in writer.fieldnames if key not in row['probabilities']}|row['probabilities'])
print(json.dumps(summary,indent=2))
