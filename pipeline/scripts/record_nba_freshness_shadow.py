"""Paired future NBA forecasts: same weights, stale versus reconciled observed history."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
import requests

from etl.nba_public_parsers import team
from models.sport_data import canonical_games
from models.sport_features import SportState, FEATURES
from models.training_resources import training_threads


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observed_features(history: pd.DataFrame, game: dict, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Exact observation cutoff, experimental only; no midnight/backdating shortcut."""
    if cutoff.tzinfo is None or cutoff >= pd.Timestamp(game['date']):
        raise ValueError('Feature cutoff must be timezone-aware and before kickoff')
    eligible = history[history.date.lt(cutoff) & history.result_available_at.le(cutoff)]
    state = SportState('basketball')
    for row in eligible.sort_values(['result_available_at','date','home_key','away_key']).to_dict('records'):
        state.update(row)
    return pd.DataFrame([state.vector(game)], columns=FEATURES)


def run(bundle: Path, fresh: Path, output: Path) -> dict:
    metadata = json.loads((bundle/'metrics.json').read_text())
    if sha(bundle/'model.pkl') != metadata['model_sha256'] or sha(bundle/'dataset.parquet') != metadata['dataset_sha256']:
        raise ValueError('Frozen NBA model changed')
    reconciliation = json.loads((fresh/'manifest.json').read_text())
    if sha(fresh/'reconciled.jsonl') != reconciliation['normalized_sha256']:
        raise ValueError('Reconciled scores changed')
    for source in reconciliation['sources']:
        if sha(fresh/source['file']) != source['sha256']:
            raise ValueError('Independent source changed')
    old = pd.read_parquet(bundle/'dataset.parquet')
    if set(old.league) != {'basketball_nba'}:
        raise ValueError('NBA-only baseline required')
    added = [json.loads(line) for line in (fresh/'reconciled.jsonl').read_text().splitlines()]
    updated = canonical_games(old.to_dict('records')+added, 'basketball')
    now = pd.Timestamp.now(tz='UTC')
    if any(pd.Timestamp(row['result_available_at']) > now for row in added):
        raise ValueError('Score evidence is not available yet')
    output.mkdir(parents=True, exist_ok=False)
    key = os.getenv('BALLDONTLIE_API_KEY')
    if not key:
        raise ValueError('Independent NBA schedule access unavailable')
    cursor = None; seen = set(); fixtures = []; sources = []
    for page in range(3):
        params = {'start_date': now.date().isoformat(), 'end_date': (now+timedelta(days=7)).date().isoformat(), 'per_page':100}
        if cursor is not None:
            params['cursor'] = cursor
        response = requests.get('https://api.balldontlie.io/v1/games', params=params, headers={'Authorization':key}, timeout=35)
        payload = response.text.replace(key,'[REDACTED]').encode('utf-8')
        path = output/f'schedule-{page+1}.json'; path.write_bytes(payload)
        sources.append({'file':path.name,'sha256':sha(path),'observed_at':datetime.now(timezone.utc).isoformat(),'params':params})
        response.raise_for_status(); data = json.loads(payload); fixtures.extend(data.get('data',[]))
        cursor = data.get('meta',{}).get('next_cursor')
        if cursor is None:
            break
        if cursor in seen:
            raise ValueError('Repeated schedule cursor')
        seen.add(cursor); time.sleep(13)
    else:
        raise ValueError('Schedule pagination budget exceeded')
    model = joblib.load(bundle/'model.pkl')
    cutoff = pd.Timestamp.now(tz='UTC'); rows = []; excluded = []; ids = set()
    known = set(old.home_key)|set(old.away_key)
    for fixture in fixtures:
        if fixture['id'] in ids:
            raise ValueError('Duplicate scheduled game ID')
        ids.add(fixture['id'])
        kickoff = pd.to_datetime(fixture.get('datetime'),utc=True,errors='coerce')
        if (pd.isna(kickoff) or kickoff <= cutoff or fixture.get('status_state')!='scheduled'
                or fixture.get('period')!=0 or fixture.get('postponed') or fixture.get('postseason') is not False):
            excluded.append({'id':fixture['id'],'reason':'not_future_scheduled_regular_game'}); continue
        home,away = team(fixture['home_team']['full_name']),team(fixture['visitor_team']['full_name'])
        if not home or not away or home.casefold() not in known or away.casefold() not in known:
            excluded.append({'id':fixture['id'],'reason':'unknown_NBA_history'}); continue
        game = {'home_team':home,'away_team':away,'date':kickoff,'league':'basketball_nba'}
        inputs = {'stale':observed_features(old,game,cutoff),'fresh':observed_features(updated,game,cutoff)}
        probabilities = {}
        for arm,features in inputs.items():
            with training_threads(2):
                p = model.predict_proba(features)[0]
            if not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(),1):
                raise ValueError('Invalid NBA probabilities')
            probabilities[arm] = p.tolist()
        generated = pd.Timestamp.now(tz='UTC')
        if generated >= kickoff:
            excluded.append({'id':fixture['id'],'reason':'started_during_forecast'}); continue
        rows.append({'id':str(fixture['id']),'home':home,'away':away,'kickoff':kickoff.isoformat(),
            'generated_at':generated.isoformat(),'feature_cutoff':cutoff.isoformat(),
            'probabilities':probabilities,'features':{arm:frame.iloc[0].to_dict() for arm,frame in inputs.items()}})
    report = {'created_at':datetime.now(timezone.utc).isoformat(),'status':'prospective_NBA_freshness_shadow',
        'production_changed':False,'active':False,'classes':metadata['classes'],'same_model_for_both_arms':True,
        'model_sha256':metadata['model_sha256'],'baseline_history_sha256':metadata['dataset_sha256'],
        'reconciled_history_sha256':reconciliation['normalized_sha256'],'additional_games':len(added),
        'schedule_sources':sources,'fixtures':rows,'excluded':excluded,
        'policy':{'settlement':'INCLUDING_OVERTIME','minimum_settled':200,'minimum_match_days':20,
                  'selection':'earliest prospective forecast per provider ID','no_odds_or_bets':True},
        'limitations':['Small first batch; no accuracy improvement established.',
                      'Exact observed-time research path differs from production midnight cutoff.',
                      'Forecast horizon spans seven days; future intervening results are unknown.']}
    encoded = json.dumps(report,indent=2,allow_nan=False).encode('utf-8')
    (output/'trial.json').write_bytes(encoded); (output/'trial.sha256').write_text(hashlib.sha256(encoded).hexdigest()+'\n')
    print(json.dumps({'recorded':len(rows),'excluded':len(excluded),'additional_history_games':len(added)},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--fresh',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.bundle,args.fresh,args.output)
