"""Isolated, retrospective manager-feature ablation on verified Wyscout metadata."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import LabelEncoder

from etl.fetch_soccer_events import DEFAULT_ROOT, file_hash
from models.data import canonical_matches
from models.features import FEATURE_NAMES
from models.manager_features import build_manager_frame, coach_key
from models.selection import expert_candidates
from models.training_resources import training_threads
from models.validation import chronological_split, probability_metrics

LEAGUES = ['England', 'France', 'Germany', 'Italy', 'Spain']


def load_matches(root: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    archive = root/'matches.zip'
    digest = file_hash(archive)
    if digest != manifest['captures']['matches.zip']['sha256']:
        raise ValueError('Raw match archive checksum mismatch')
    rows, exclusions = [], []
    with zipfile.ZipFile(archive) as captured:
        for league in LEAGUES:
            for match in json.loads(captured.read(f'matches_{league}.json')):
                teams = list(match['teamsData'].values())
                home = [team for team in teams if team['side'] == 'home']
                away = [team for team in teams if team['side'] == 'away']
                if match['status'] != 'Played' or match['duration'] != 'Regular' or len(home) != 1 or len(away) != 1:
                    exclusions.append({'match_id':match['wyId'],'reason':'invalid_status_duration_or_orientation'})
                    continue
                home, away = home[0], away[0]
                expected = home['teamId'] if home['score'] > away['score'] else away['teamId'] if away['score'] > home['score'] else 0
                if match['winner'] != expected:
                    exclusions.append({'match_id':match['wyId'],'reason':'score_winner_disagreement'})
                    continue
                if coach_key(home.get('coachId')) is not None and coach_key(home.get('coachId')) == coach_key(away.get('coachId')):
                    exclusions.append({'match_id':match['wyId'],'reason':'same_coach_both_sides'})
                    continue
                rows.append({'date':match['dateutc'],'home_team':f"wyscout:{home['teamId']}",
                    'away_team':f"wyscout:{away['teamId']}", 'home_score':home['score'],'away_score':away['score'],
                    'home_coach_id':coach_key(home.get('coachId')), 'away_coach_id':coach_key(away.get('coachId')),
                    'competition':league, 'provider_match_id':str(match['wyId']),
                    'status':'FINISHED','data_source':'wyscout:match-metadata'})
    frame = canonical_matches([pd.DataFrame(rows)])
    return frame, {'matches_zip_sha256':digest,'retained':len(frame),'exclusions':exclusions,
        'matches_by_league':frame.competition.value_counts().to_dict(),
        'missing_coach_sides':int(frame[['home_coach_id','away_coach_id']].isna().sum().sum()),
        'unique_coaches':len(set(frame.home_coach_id.dropna())|set(frame.away_coach_id.dropna())),
        'provider':'Wyscout / Pappalardo et al. (2019)', 'license':'CC BY 4.0',
        'source':'https://doi.org/10.6084/m9.figshare.c.4415000'}


def evaluate(X: pd.DataFrame, fixtures, splits, y, classes, output: Path) -> tuple[np.ndarray, dict]:
    train,tune,calibration,test=[splits[key] for key in ['train','tune','calibration','test']]
    candidates=expert_candidates(list(X.columns),trees=100)
    scores={}
    with training_threads(2):
        for name,model in candidates.items():
            model.fit(X.iloc[train],y[train])
            scores[name]=probability_metrics(y[tune],model.predict_proba(X.iloc[tune]),classes)
        selected=min(scores,key=lambda name:scores[name]['log_loss'])
        model=clone(candidates[selected]).fit(X.iloc[np.concatenate([train,tune])],y[np.concatenate([train,tune])])
        calibrated=CalibratedClassifierCV(FrozenEstimator(model),method='sigmoid',cv=2)
        calibrated.fit(X.iloc[calibration],y[calibration])
        probabilities=calibrated.predict_proba(X.iloc[test])
    report={'selected':selected,'tuning':scores,'test':probability_metrics(y[test],probabilities,classes),
        'test_by_league':{league:probability_metrics(y[test][mask],probabilities[mask],classes)
                         for league in LEAGUES if (mask:=fixtures.iloc[test].competition.eq(league).to_numpy()).any()}}
    joblib.dump(calibrated,output/'model.pkl')
    with training_threads(2):
        np.testing.assert_allclose(joblib.load(output/'model.pkl').predict_proba(X.iloc[test]),probabilities,atol=1e-12)
    (output/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return probabilities,report


def loss_difference(y, baseline, augmented, dates) -> dict:
    losses=-np.log(np.clip(baseline[np.arange(len(y)),y],1e-15,1)) + np.log(np.clip(augmented[np.arange(len(y)),y],1e-15,1))
    # Resample complete UTC match weeks, preserving within-week dependence.
    weeks=pd.to_datetime(dates,utc=True).dt.strftime('%G-%V').to_numpy()
    blocks=[np.flatnonzero(weeks==week) for week in sorted(set(weeks))]
    rng=np.random.default_rng(42)
    samples=[float(losses[np.concatenate([blocks[index] for index in rng.integers(0,len(blocks),len(blocks))])].mean()) for _ in range(2000)]
    return {'baseline_minus_augmented_log_loss':float(losses.mean()),
            'week_block_bootstrap_95_percent_interval':np.quantile(samples,[.025,.975]).tolist(),
            'bootstrap_draws':2000,'test_week_blocks':len(blocks),
            'interpretation':'Positive favors manager features; association and predictive value, not a causal coaching effect.'}


def run(root: Path, output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False)
    fixtures,source=load_matches(root)
    base,managers,fixtures=build_manager_frame(fixtures)
    history_columns=FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    leagues=pd.get_dummies(fixtures.competition,prefix='league',dtype=float)
    baseline=pd.concat([base[history_columns],leagues],axis=1)
    augmented=pd.concat([baseline,managers],axis=1)
    splits=chronological_split(fixtures.date)
    encoder=LabelEncoder().fit(['away_win','draw','home_win'])
    y=encoder.transform(fixtures.result)
    if any(len(np.unique(y[indices]))!=3 for indices in splits.values()):
        raise ValueError('All chronological periods need three outcome classes')
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':source,
        'observation_policy':'Only prior completed UTC match days identify the last observed coach; no current-match coach input.',
        'limitations':['One 2017/18 season in five leagues; research only.',
            'Appointment announcement times unavailable; first change game cannot be known in advance from this source.',
            'Coach selection, club quality and player availability are confounded; no causal identification.'],
        'splits':{key:{'games':len(indices),'start':fixtures.iloc[indices].date.min().isoformat(),
                      'end':fixtures.iloc[indices].date.max().isoformat()} for key,indices in splits.items()}}
    probabilities={}
    for name,X in [('form_elo',baseline),('form_elo_manager',augmented)]:
        directory=output/name
        directory.mkdir()
        print(f'Evaluating {name}',flush=True)
        probabilities[name],report[name]=evaluate(X,fixtures,splits,y,list(encoder.classes_),directory)
    test=splits['test']
    report['paired_comparison']=loss_difference(y[test],probabilities['form_elo'],probabilities['form_elo_manager'],fixtures.iloc[test].date)
    report['manager_input_coverage']={'home_known':float(managers.home_manager_known.mean()),
        'away_known':float(managers.away_manager_known.mean()),
        'recent_change_sides':int(managers[['home_manager_recent_change_observed','away_manager_recent_change_observed']].sum().sum())}
    fixtures.to_parquet(output/'dataset.parquet',index=False)
    augmented.to_parquet(output/'features.parquet',index=False)
    replay=fixtures.iloc[test][['provider_match_id','date','competition','result']].copy()
    for name,values in probabilities.items():
        for index,label in enumerate(encoder.classes_):
            replay[name+'_'+label]=values[:,index]
    replay.to_csv(output/'holdout_predictions.csv',index=False)
    report['dataset_sha256']=hashlib.sha256((output/'dataset.parquet').read_bytes()).hexdigest()
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({name:report[name]['test'] for name in probabilities},indent=2),flush=True)
    print(json.dumps(report['paired_comparison'],indent=2),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    run(args.root,args.output_dir)
