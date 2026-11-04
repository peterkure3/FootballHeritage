"""Assess frozen accuracy forecasts; never modify the trial or place bets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL
from etl.fetch_raw_data import FootballDataOrgFetcher
from models.league_data import identity
from models.validation import probability_metrics


def assess(trial: dict, results: list[dict], now: pd.Timestamp) -> dict:
    classes=['away_win','draw','home_win']
    if trial['classes']!=classes or trial['status']!='prospective_accuracy_shadow':
        raise ValueError('Unexpected trial contract')
    indexed={}
    for result in results:
        indexed.setdefault(str(result['id']),[]).append(result)
    rows=[];labels=[];probabilities={'original':[],'reviewed':[]};days=set()
    for fixture in trial['fixtures']:
        kickoff=pd.Timestamp(fixture['kickoff']);generated=pd.Timestamp(fixture['generated_at'])
        if generated.tzinfo is None or kickoff.tzinfo is None or not generated<kickoff or generated>now:
            raise ValueError('Trial contains a post-kickoff forecast')
        for model in probabilities:
            p=np.asarray(fixture['probabilities'][model],dtype=float)
            if p.shape!=(3,) or not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(),1):
                raise ValueError('Invalid frozen probabilities')
        matches=indexed.get(str(fixture['id']),[])
        row={'id':fixture['id'],'kickoff':fixture['kickoff'],'status':'pending'}
        if len(matches)>1:
            row['status']='ambiguous_result'
        elif len(matches)==1:
            result=matches[0];score=result.get('score',{});ft=score.get('fullTime',{})
            h,a=ft.get('home'),ft.get('away')
            names=all(identity(result[side+'Team']['name'],trial['alias_map'])==identity(fixture[side],trial['alias_map']) for side in ['home','away'])
            if pd.Timestamp(result['utcDate'])!=kickoff or not names:
                row['status']='fixture_mismatch'
            elif (result.get('status')=='FINISHED' and score.get('duration')=='REGULAR'
                    and type(h) is int and type(a) is int and min(h,a)>=0 and kickoff<now):
                winner='home_win' if h>a else 'away_win' if a>h else 'draw'
                labels.append(classes.index(winner));days.add(kickoff.date())
                for model in probabilities:
                    probabilities[model].append(fixture['probabilities'][model])
                row.update(status='settled',result=winner,home_score=h,away_score=a)
        rows.append(row)
    metrics={model:probability_metrics(np.array(labels),np.array(values),classes)
             for model,values in probabilities.items()} if labels else {}
    policy=trial['policy'];enough=len(labels)>=policy['minimum_settled_for_assessment'] and len(days)>=policy['minimum_distinct_match_days']
    return {'assessed_at':now.isoformat(),'fixtures':rows,'settled':len(labels),
        'pending':sum(r['status']=='pending' for r in rows),'distinct_settled_days':len(days),
        'metrics':metrics,'status':'minimum_sample_reached_requires_review' if enough else 'collecting_evidence',
        'promotion_authorized':False,'production_changed':False}


def run(directory: Path) -> dict:
    payload=(directory/'trial.json').read_bytes();digest=hashlib.sha256(payload).hexdigest()
    if digest!=(directory/'trial.sha256').read_text().strip():
        raise ValueError('Frozen trial checksum mismatch')
    trial=json.loads(payload)
    for source in trial['sources']:
        if hashlib.sha256((directory/source['path']).read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Fixture source checksum mismatch')
    now=pd.Timestamp.now(tz='UTC');stamp=now.strftime('%Y%m%dT%H%M%S%fZ')
    output=directory/'assessments'/stamp;output.mkdir(parents=True,exist_ok=False)
    fetcher=FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY,FOOTBALL_DATA_ORG_BASE_URL)
    results=[];sources=[];errors=[]
    for competition in sorted({r['competition'] for r in trial['fixtures']}):
        dates=[pd.Timestamp(r['kickoff']).date() for r in trial['fixtures'] if r['competition']==competition and pd.Timestamp(r['kickoff'])<now]
        if not dates:
            continue
        try:
            response=fetcher.fetch_matches(competition,str(min(dates)),str(max(dates)))
            path=output/f'{competition}.json';path.write_text(json.dumps(response))
            sources.append({'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'observed_at':datetime.now(timezone.utc).isoformat()})
            results.extend(response.get('matches',[]))
        except Exception as exc:
            errors.append({'competition':competition,'error':type(exc).__name__})
        time.sleep(7)
    report=assess(trial,results,pd.Timestamp.now(tz='UTC'))
    report.update(trial_sha256=digest,result_sources=sources,source_errors=errors)
    (output/'assessment.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['status','settled','pending','distinct_settled_days','source_errors']},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',type=Path,required=True)
    args=parser.parse_args();run(args.trial)
