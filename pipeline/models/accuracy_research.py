"""Bounded history-only accuracy experiments; no production or registry writes."""
import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from models.features import FEATURE_NAMES, FeatureState, build_feature_frame
from models.league_data import COMPETITION_CODES
from models.league_data import identity_aliases, identity
from models.training_resources import training_threads
from models.validation import forward_folds, probability_metrics


def context_features(fixtures: pd.DataFrame) -> pd.DataFrame:
    """One day's results never enter another fixture on that day."""
    history = defaultdict(lambda: deque(maxlen=30))
    league_results = defaultdict(lambda: np.ones(3))
    state = FeatureState()
    records = []
    for _, group in fixtures.groupby('fixture_day', sort=True):
        rows = group.to_dict('records')
        for row in rows:
            competition = COMPETITION_CODES.get(str(row.get('competition')), str(row.get('competition')))
            counts = league_results[competition]
            features = {'competition_code': competition}
            features.update(dict(zip(['league_away_rate', 'league_draw_rate', 'league_home_rate'], counts/counts.sum())))
            for side in ['home', 'away']:
                team = row[side+'_key']
                games = list(history[team])
                features[side+'_history_games'] = len(games)
                features[side+'_rest_days'] = min(60, (row['date']-games[-1][3]).total_seconds()/86400) if games else 60
                for window in [5, 30]:
                    previous = games[-window:]
                    for index, name, default in [(0,'goals_for',1.5),(1,'goals_against',1.5),(2,'opponent_elo',1500.)]:
                        features[f'{side}_{name}_{window}'] = float(np.mean([r[index] for r in previous])) if previous else default
            records.append(features)
        for row in rows:
            home, away = row['home_key'], row['away_key']
            he, ae = state.elo[home], state.elo[away]
            history[home].append((row['home_score'],row['away_score'],ae,row['date']))
            history[away].append((row['away_score'],row['home_score'],he,row['date']))
            competition = COMPETITION_CODES.get(str(row.get('competition')), str(row.get('competition')))
            league_results[competition][['away_win','draw','home_win'].index(row['result'])] += 1
            state.update(row)
    return pd.DataFrame(records)


def estimator(name: str, base: list[str], extra: list[str]):
    columns = base if name == 'baseline' else base+extra
    transforms = [('numbers', StandardScaler() if name != 'context_gradient' else 'passthrough', columns)]
    if name != 'baseline':
        transforms.append(('league',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['competition_code']))
    learner = (HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=15,min_samples_leaf=30,
        l2_regularization=10,early_stopping=False,random_state=42) if name=='context_gradient' else
        LogisticRegression(C=.01,max_iter=2000,random_state=42))
    return make_pipeline(ColumnTransformer(transforms),learner)


def run(bundle: Path, output: Path) -> dict:
    manifest=json.loads((bundle/'metrics_v2.1.0.json').read_text())
    dataset=bundle/'dataset.parquet'
    if hashlib.sha256(dataset.read_bytes()).hexdigest()!=manifest['dataset_sha256']:
        raise ValueError('Candidate dataset checksum mismatch')
    data=pd.read_parquet(dataset)
    boundary=pd.to_datetime(manifest['data_report']['splits']['test']['start'],utc=True)
    data=data[data.date.lt(boundary) & data.result.notna()].copy()
    X,fixtures=build_feature_frame(data)
    context=context_features(fixtures)
    X=pd.concat([X,context],axis=1)
    base=FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    extra=[c for c in context if c!='competition_code']
    classes=['away_win','draw','home_win']
    y=pd.Categorical(fixtures.result,categories=classes).codes
    predictions=[]; fold_reports=[]
    configurations=['baseline','context_logistic','context_gradient']
    for fold,(development,test) in enumerate(forward_folds(fixtures.date,3)):
        days=np.sort(fixtures.iloc[development].date.dt.normalize().unique())
        calibration_start=days[int(len(days)*.8)]
        calibrate=development[fixtures.iloc[development].date.dt.normalize().ge(calibration_start).to_numpy()]
        train=development[fixtures.iloc[development].date.dt.normalize().lt(calibration_start).to_numpy()]
        summary={'fold':fold,'train_samples':len(train),'calibration_samples':len(calibrate),'test_samples':len(test),
                 'train_end':fixtures.iloc[train].date.max().isoformat(),'test_start':fixtures.iloc[test].date.min().isoformat(),'models':{}}
        for name in configurations:
            print(f'Fold {fold+1}/3: {name}',flush=True)
            with training_threads(2):
                fitted=estimator(name,base,extra).fit(X.iloc[train],y[train])
                calibrated=CalibratedClassifierCV(FrozenEstimator(fitted),method='sigmoid')
                calibrated.fit(X.iloc[calibrate],y[calibrate])
                p=calibrated.predict_proba(X.iloc[test])
            summary['models'][name]=probability_metrics(y[test],p,classes)
            for idx,probability in zip(test,p):
                predictions.append({'row':int(idx),'fold':fold,'model':name,'date':fixtures.iloc[idx].date.isoformat(),
                    'home':fixtures.iloc[idx].home_team,'away':fixtures.iloc[idx].away_team,'actual':int(y[idx]),
                    **dict(zip(classes,probability.tolist()))})
        fold_reports.append(summary)
    replay=pd.DataFrame(predictions)
    aggregate={}
    for name in configurations:
        rows=replay[replay.model.eq(name)]
        aggregate[name]=probability_metrics(rows.actual.to_numpy(),rows[classes].to_numpy(),classes)
    baseline=aggregate['baseline']
    report={'created_at':datetime.now(timezone.utc).isoformat(),'bundle':str(bundle),'dataset_sha256':manifest['dataset_sha256'],
        'excluded_test_start':boundary.isoformat(),'evaluation':'three expanding development-only folds',
        'availability_policy':'ASSUMED_NEXT_UTC_DAY_NOT_VERIFIED','production_changed':False,
        'seed':42,'configurations':configurations,'folds':fold_reports,'aggregate':aggregate,
        'promising':{name:aggregate[name]['accuracy']>baseline['accuracy'] and aggregate[name]['log_loss']<baseline['log_loss']
                    and aggregate[name]['brier_score']<baseline['brier_score'] and
                    sum(f['models'][name]['accuracy']>f['models']['baseline']['accuracy'] for f in fold_reports)>=2
                    for name in configurations[1:]},
        'limitations':['Development-fold evidence only; no fresh final-holdout or prospective validation.',
            'Historical final-result availability is assumed next day, not source-verified.',
            'No archived market odds used. No active artifact overwritten.']}
    output.mkdir(parents=True,exist_ok=False)
    replay.to_csv(output/'predictions.csv',index=False)
    (output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({name:{k:v[k] for k in ['samples','accuracy','log_loss','brier_score']} for name,v in aggregate.items()},indent=2))
    return report


def run_identities(bundle: Path, output: Path) -> dict:
    manifest=json.loads((bundle/'metrics_v2.1.0.json').read_text())
    dataset=bundle/'dataset.parquet'
    if hashlib.sha256(dataset.read_bytes()).hexdigest()!=manifest['dataset_sha256']:
        raise ValueError('Candidate dataset checksum mismatch')
    data=pd.read_parquet(dataset)
    boundary=pd.to_datetime(manifest['data_report']['splits']['test']['start'],utc=True)
    data=data[data.date.lt(boundary) & data.result.notna()].copy()
    aliases=identity_aliases()
    data['_reviewed_home']=data.home_team.map(lambda n:identity(n,aliases))
    data['_reviewed_away']=data.away_team.map(lambda n:identity(n,aliases))
    keys=['fixture_day','_reviewed_home','_reviewed_away']
    if data.groupby(keys)[['home_score','away_score']].nunique().gt(1).any().any():
        raise ValueError('Reviewed identities expose conflicting scores; audit before fitting')
    initial=len(data)
    data=data.drop_duplicates(keys,keep='last').reset_index(drop=True)
    data['_paired_id']=np.arange(len(data))
    matrices={}
    aligned=None
    for name in ['original','reviewed']:
        arm=data.copy()
        if name=='reviewed':
            arm['home_team']=arm['_reviewed_home']
            arm['away_team']=arm['_reviewed_away']
        features,fixtures=build_feature_frame(arm)
        order=np.argsort(fixtures['_paired_id'].to_numpy())
        matrices[name]=features.iloc[order].reset_index(drop=True)
        ordered=fixtures.iloc[order].reset_index(drop=True)
        if aligned is not None:
            if not ordered['_paired_id'].equals(aligned['_paired_id']) or not ordered.result.equals(aligned.result):
                raise ValueError('Identity arms have different fixture membership or outcomes')
        else:
            aligned=ordered
    base=FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    classes=['away_win','draw','home_win'];y=pd.Categorical(aligned.result,categories=classes).codes
    predictions=[];folds=[]
    for fold,(development,test) in enumerate(forward_folds(aligned.date,3)):
        days=np.sort(aligned.iloc[development].date.dt.normalize().unique());edge=days[int(len(days)*.8)]
        train=development[aligned.iloc[development].date.dt.normalize().lt(edge).to_numpy()]
        calibration=development[aligned.iloc[development].date.dt.normalize().ge(edge).to_numpy()]
        report={'fold':fold,'models':{}}
        for name,X in matrices.items():
            print(f'Identity fold {fold+1}/3: {name}',flush=True)
            with training_threads(2):
                fitted=estimator('baseline',base,[]).fit(X.iloc[train],y[train])
                model=CalibratedClassifierCV(FrozenEstimator(fitted),method='sigmoid')
                model.fit(X.iloc[calibration],y[calibration]);p=model.predict_proba(X.iloc[test])
            report['models'][name]=probability_metrics(y[test],p,classes)
            for idx,probability in zip(test,p):
                predictions.append({'row':int(idx),'fold':fold,'model':name,'date':aligned.iloc[idx].date.isoformat(),
                    'home':aligned.iloc[idx].home_team,'away':aligned.iloc[idx].away_team,'actual':int(y[idx]),
                    **dict(zip(classes,probability.tolist()))})
        folds.append(report)
    rows=pd.DataFrame(predictions);aggregate={}
    for name in matrices:
        subset=rows[rows.model.eq(name)]
        aggregate[name]=probability_metrics(subset.actual.to_numpy(),subset[classes].to_numpy(),classes)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'experiment':'reviewed identities only',
        'dataset_sha256':manifest['dataset_sha256'],'excluded_test_start':boundary.isoformat(),
        'alias_sha256':hashlib.sha256((Path(__file__).parent/'league_identities.json').read_bytes()).hexdigest(),
        'duplicate_fixtures_removed_from_both_arms':initial-len(data),'aggregate':aggregate,'folds':folds,
        'availability_policy':'ASSUMED_NEXT_UTC_DAY_NOT_VERIFIED','production_changed':False}
    output.mkdir(parents=True,exist_ok=False)
    rows.to_csv(output/'predictions.csv',index=False)
    (output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({name:{k:v[k] for k in ['samples','accuracy','log_loss','brier_score']} for name,v in aggregate.items()},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--identities',action='store_true')
    args=parser.parse_args()
    (run_identities if args.identities else run)(args.bundle,args.output)
