"""Reproduce saved model metrics and export dated upcoming form with previews."""
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline'))
from models.features import FEATURE_NAMES, FeatureState, build_feature_frame
from models.validation import chronological_split, probability_metrics

directory=ROOT/'pipeline/models/model_store/candidates/team_form_20261019'
metrics=json.loads((directory/'metrics_v2.1.0.json').read_text(encoding='utf-8'))
data=pd.read_parquet(directory/'dataset.parquet')
model=joblib.load(directory/'model_v2.1.0.pkl')
encoder=joblib.load(directory/'label_encoder_v2.1.0.pkl')
X,fixtures=build_feature_frame(data)
test=chronological_split(fixtures.date)['test']
with threadpool_limits(limits=2):
    reproduced=probability_metrics(encoder.transform(fixtures.iloc[test].result),model.predict_proba(X.iloc[test]),list(encoder.classes_))
for key in ['accuracy','log_loss','brier_score']:
    assert np.isclose(reproduced[key],metrics['test'][key]),key
report=json.loads((ROOT/'pipeline/data/raw/team_form/20261019/form.json').read_text(encoding='utf-8'))
state=FeatureState()
cutoff=pd.Timestamp(report['observed_at']).normalize()
for match in fixtures[fixtures.date.lt(cutoff)].to_dict('records'):
    state.update(match)
lines=['# Upcoming football form — collected 19 October 2026','',
       'Oldest → newest. Scope: ten provider-covered competitions, through 26 October. Cup/other-league omissions are possible; five records does not establish complete overall form.', '',
       'Candidate previews use the history expert without bookmaker odds. Incomplete-form fixtures are withheld. Active model was not replaced.', '',
       '| Kickoff (UTC) | Competition | Home | Last five | Away | Last five | Coverage |',
       '|---|---|---|---|---|---|---|']
predictions=[]
for f in report['fixtures']:
    complete=f['home_form']['games']==f['away_form']['games']==5
    row=dict(f)
    row['prediction_status']='insufficient_form'
    if complete:
        vector=pd.DataFrame([state.vector(f['home_team'],f['away_team'])],columns=FEATURE_NAMES)
        for side in ['home','away']:
            assert vector.iloc[0][f'{side}_team_wins_last_n']==f[f'{side}_form']['wins'], f
            assert vector.iloc[0][f'{side}_team_losses_last_n']==f[f'{side}_form']['losses'], f
        with threadpool_limits(limits=2):
            probabilities=model.predict_proba(vector)[0]
        assert np.isfinite(probabilities).all() and np.isclose(probabilities.sum(),1)
        row.update(prediction_status='candidate_history_only',probabilities=dict(zip(encoder.classes_,probabilities.tolist())))
    predictions.append(row)
    lines.append('| '+' | '.join([f['kickoff'],f['competition'],f['home_team'],f['home_form']['sequence'] or 'missing',f['away_team'],f['away_form']['sequence'] or 'missing','5 each; limited scope' if complete else 'INCOMPLETE'])+' |')
out=ROOT/'stages/03-build/output'
(out/'upcoming-team-form-20261019.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(out/'upcoming-team-form-20261019.json').write_text(json.dumps(dict(observed_at=report['observed_at'],model=str(directory),test=reproduced,fixtures=predictions),indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(metrics_reproduced=True,fixtures=len(predictions),previews=sum(r['prediction_status']=='candidate_history_only' for r in predictions),accuracy=reproduced['accuracy'],log_loss=reproduced['log_loss'])))
