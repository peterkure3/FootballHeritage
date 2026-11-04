"""Frozen identity-only retrospective check; never promotes a model."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from models.accuracy_research import estimator
from models.features import FEATURE_NAMES, build_feature_frame
from models.league_data import identity, identity_aliases
from models.training_resources import training_threads
from models.validation import probability_metrics


def run(bundle: Path, output: Path) -> dict:
    manifest=json.loads((bundle/'metrics_v2.1.0.json').read_text())
    dataset=bundle/'dataset.parquet'
    if hashlib.sha256(dataset.read_bytes()).hexdigest()!=manifest['dataset_sha256']:
        raise ValueError('Dataset checksum mismatch')
    raw=pd.read_parquet(dataset);raw['_paired_id']=np.arange(len(raw))
    X,fixtures=build_feature_frame(raw)
    order=np.argsort(fixtures['_paired_id'].to_numpy())
    X=X.iloc[order].reset_index(drop=True);fixtures=fixtures.iloc[order].reset_index(drop=True)
    aliases=identity_aliases();reviewed=raw.copy()
    for side in ['home','away']:
        reviewed[side+'_team']=reviewed[side+'_team'].map(lambda name:identity(name,aliases))
    reviewed_X,reviewed_fixtures=build_feature_frame(reviewed)
    order=np.argsort(reviewed_fixtures['_paired_id'].to_numpy())
    reviewed_X=reviewed_X.iloc[order].reset_index(drop=True)
    reviewed_fixtures=reviewed_fixtures.iloc[order].reset_index(drop=True)
    if not fixtures['_paired_id'].equals(reviewed_fixtures['_paired_id']) or not fixtures.result.equals(reviewed_fixtures.result):
        raise ValueError('Aliases changed fixture membership; explicit reconciliation required')
    periods=manifest['data_report']['splits']
    def period(name):
        return fixtures.date.between(pd.Timestamp(periods[name]['start']),pd.Timestamp(periods[name]['end'])).to_numpy()
    train=np.flatnonzero(period('train')|period('tune'))
    calibration=np.flatnonzero(period('calibration'));test=np.flatnonzero(period('test'))
    classes=manifest['classes'];y=pd.Categorical(fixtures.result,categories=classes).codes
    base=FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    with training_threads(2):
        incumbent=joblib.load(bundle/'model_v2.1.0.pkl')
        before=incumbent.history_.predict_proba(X.iloc[test])
        fitted=estimator('baseline',base,[]).fit(reviewed_X.iloc[train],y[train])
        model=CalibratedClassifierCV(FrozenEstimator(fitted),method='sigmoid')
        model.fit(reviewed_X.iloc[calibration],y[calibration])
        after=model.predict_proba(reviewed_X.iloc[test])
    original=probability_metrics(y[test],before,classes)
    corrected=probability_metrics(y[test],after,classes)
    promising=corrected['accuracy']>original['accuracy'] and corrected['log_loss']<original['log_loss'] and corrected['brier_score']<original['brier_score']
    output.mkdir(parents=True,exist_ok=False)
    rows=fixtures.iloc[test][['date','home_team','away_team','result']].copy()
    for i,name in enumerate(classes):
        rows['original_'+name]=before[:,i];rows['reviewed_'+name]=after[:,i]
    rows.to_csv(output/'predictions.csv',index=False)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'status':'retrospective_candidate_only',
        'production_changed':False,'fresh_holdout':False,'availability_policy':'ASSUMED_NEXT_UTC_DAY_NOT_VERIFIED',
        'source_bundle':str(bundle),'source_dataset_sha256':manifest['dataset_sha256'],
        'source_model_sha256':hashlib.sha256((bundle/'model_v2.1.0.pkl').read_bytes()).hexdigest(),
        'alias_map':aliases,'features':base,'classes':classes,'original':original,'reviewed':corrected,
        'promising':promising,'fit_samples':len(train),'calibration_samples':len(calibration),
        'test_start':fixtures.iloc[test].date.min().isoformat(),'test_end':fixtures.iloc[test].date.max().isoformat()}
    if promising:
        joblib.dump(model,output/'history_model.pkl')
        report['model_sha256']=hashlib.sha256((output/'history_model.pkl').read_bytes()).hexdigest()
        report['serving_requirement']='Use the exact saved alias map before causal feature construction; no odds features.'
    (output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({name:{k:v[k] for k in ['samples','accuracy','log_loss','brier_score']} for name,v in [('original',original),('reviewed',corrected)]},indent=2))
    print('Promising:',promising)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.bundle,args.output)
