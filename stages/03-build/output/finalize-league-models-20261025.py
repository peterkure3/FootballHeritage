"""Assemble the eight verified league artifacts into one immutable serving run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline'))
from models.train_football_leagues import DOMESTIC_LEAGUES

store = ROOT/'pipeline/models/model_store/league_models'
parts = [store/'20261025_reviewed', store/'20261025_rest']
reports = [json.loads((part/'report.json').read_text(encoding='utf-8')) for part in parts]
entries = {code: (part, metrics) for part, report in zip(parts,reports) for code,metrics in report['leagues'].items()}
if set(entries) != set(DOMESTIC_LEAGUES):
    raise ValueError('Eight league models must finish before assembly')
identities = (ROOT/'pipeline/models/league_identities.json').read_bytes()
if hashlib.sha256(identities).hexdigest() != reports[1]['identity_sha256']:
    raise ValueError('Identity dictionary changed during training')
for code, (part, metrics) in entries.items():
    for filename in ['model.pkl','dataset.parquet']:
        if hashlib.sha256((part/code/filename).read_bytes()).hexdigest() != metrics[filename.replace('.','_')+'_sha256']:
            raise ValueError('Artifact checksum mismatch')
output = store/'20261025_complete'
output.mkdir(exist_ok=False)
report = {'run_id':output.name,'created_at':datetime.now(timezone.utc).isoformat(),
          'identity_sha256':hashlib.sha256(identities).hexdigest(),'leagues':{}}
for code, (part, metrics) in entries.items():
    shutil.copytree(part/code, output/code)
    report['leagues'][code] = metrics
(output/'league_identities.json').write_bytes(identities)
(output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({code:{'games':metrics['training_games'],'test':metrics['test']['accuracy']}
                  for code,metrics in report['leagues'].items()},indent=2))
