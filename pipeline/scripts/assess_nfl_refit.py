"""Assess frozen NFL refit forecasts against explicit final-score evidence."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from models.nfl_history import sha
from models.gridiron_sources import NFL_NAMES
from models.validation import probability_metrics


def normalize_final(event):
    status = event.get('status', {})
    if (event.get('season', {}).get('type') not in {2, 3}
            or status.get('type', {}).get('completed') is not True
            or type(status.get('period')) is not int or status['period']<4):
        return None
    competitors = event['competitions'][0]['competitors']
    home = [row for row in competitors if row.get('homeAway')=='home']
    away = [row for row in competitors if row.get('homeAway')=='away']
    if len(home)!=1 or len(away)!=1:
        raise ValueError('Ambiguous NFL final orientation')
    h, a = home[0], away[0]
    if any(row['team']['displayName'] not in NFL_NAMES.values() for row in [h, a]):
        raise ValueError('Unknown NFL final identity')
    if any(not str(row.get('score')).isdigit() for row in [h, a]):
        raise ValueError('Invalid NFL final score')
    kickoff = pd.Timestamp(event['date'])
    if kickoff.tzinfo is None:
        raise ValueError('NFL final kickoff requires timezone')
    return {'id': str(event['id']), 'kickoff': kickoff.isoformat(), 'home': h['team']['displayName'],
        'away': a['team']['displayName'], 'home_score': int(h['score']), 'away_score': int(a['score'])}


def assess(trial, events, now):
    if (trial['status']!='prospective_NFL_refit_evaluation' or trial['classes']!=['away_win', 'home_win']
            or trial['settlement']!='INCLUDING_OVERTIME_TIES_VOID' or now.tzinfo is None):
        raise ValueError('Unexpected NFL evaluation contract')
    trained = pd.Timestamp(trial['trained_at'])
    if trained.tzinfo is None:
        raise ValueError('NFL training timestamp requires timezone')
    indexed = {}; seen = set(); rows = []; labels = []; probabilities = []
    for event in events:
        result = normalize_final(event)
        if result:
            key = result['home'], result['away'], pd.Timestamp(result['kickoff'])
            matches = indexed.setdefault(key, [])
            if result not in matches:
                matches.append(result)
    for fixture in trial['fixtures']:
        if str(fixture['id']) in seen:
            raise ValueError('Duplicate frozen NFL fixture ID')
        seen.add(str(fixture['id']))
        kickoff = pd.Timestamp(fixture['kickoff']); generated = pd.Timestamp(fixture['generated_at'])
        feature_cutoff = pd.Timestamp(fixture['feature_cutoff'])
        if (any(t.tzinfo is None for t in [kickoff, generated, feature_cutoff])
                or not trained<=generated<kickoff or generated>now or feature_cutoff>generated):
            raise ValueError('NFL forecast was not prospectively recorded')
        p = np.asarray(fixture['probabilities'], dtype=float)
        if p.shape!=(2,) or not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(), 1):
            raise ValueError('Invalid frozen NFL probabilities')
        matches = indexed.get((fixture['home'], fixture['away'], kickoff), [])
        row = {'id': fixture['id'], 'kickoff': fixture['kickoff'], 'status': 'pending'}
        if len(matches)>1:
            row['status'] = 'ambiguous_result'
        elif len(matches)==1 and kickoff<now:
            result = matches[0]
            if result['home_score']==result['away_score']:
                row.update(status='void_final_tie', **{k: result[k] for k in ['home_score', 'away_score']})
            else:
                label = int(result['home_score']>result['away_score'])
                labels.append(label); probabilities.append(p)
                row.update(status='settled', actual=trial['classes'][label],
                    home_score=result['home_score'], away_score=result['away_score'], result_provider_id=result['id'])
        rows.append(row)
    return {'assessed_at': now.isoformat(), 'settled': len(labels),
        'void_ties': sum(r['status']=='void_final_tie' for r in rows),
        'pending': sum(r['status'] not in {'settled', 'void_final_tie'} for r in rows), 'fixtures': rows,
        'metrics': probability_metrics(np.asarray(labels), np.asarray(probabilities), trial['classes']) if labels else None,
        'production_changed': False, 'promotion_authorized': False}


def run(directory):
    digest = (directory/'trial.sha256').read_text().strip()
    if sha(directory/'trial.json')!=digest:
        raise ValueError('Frozen NFL trial checksum mismatch')
    trial = json.loads((directory/'trial.json').read_text())
    if sha(Path(trial['model_directory'])/'model.pkl')!=trial['model_sha256']:
        raise ValueError('Frozen NFL model changed')
    source = trial['schedule_source']
    if sha(Path(source['directory'])/source['file'])!=source['sha256']:
        raise ValueError('Frozen NFL schedule changed')
    now = pd.Timestamp.now(tz='UTC'); assess(trial, [], now)
    days = {pd.Timestamp(f['kickoff']).normalize() for f in trial['fixtures'] if pd.Timestamp(f['kickoff'])<now}
    days |= {day-pd.Timedelta(days=1) for day in days}
    output = directory/'assessments'/now.strftime('%Y%m%dT%H%M%S%fZ'); output.mkdir(parents=True, exist_ok=False)
    latest = {}; sources = []; errors = []
    for day in sorted(days):
        response = requests.get('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
            params={'dates': day.strftime('%Y%m%d'), 'limit': 100}, timeout=30)
        path = output/f'{day.strftime("%Y%m%d")}.json'; path.write_bytes(response.content)
        sources.append({'file': path.name, 'sha256': sha(path), 'url': response.url,
            'observed_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': response.status_code})
        if response.status_code!=200:
            errors.append({'day': str(day.date()), 'status': response.status_code}); continue
        for event in response.json().get('events', []):
            # Date queries may return the same NFL week; retain the latest capture per event ID.
            latest[str(event['id'])] = event
    report = assess(trial, list(latest.values()), pd.Timestamp.now(tz='UTC'))
    report.update(trial_sha256=digest, result_sources=sources, source_errors=errors)
    (output/'assessment.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: report[key] for key in ['settled', 'void_ties', 'pending', 'metrics', 'source_errors']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    run(parser.parse_args().trial)
