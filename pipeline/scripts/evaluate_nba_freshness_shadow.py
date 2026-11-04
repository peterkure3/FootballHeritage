"""Settle frozen NBA research forecasts against captured ESPN final scores."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from models.validation import probability_metrics
from scripts.reconcile_nba_research_results import normalize_event, capture_days


def assess(trial: dict, results: list[dict], now: pd.Timestamp) -> dict:
    classes = ['away_win', 'home_win']
    arms = {'prospective_NBA_freshness_shadow': ['stale', 'fresh'],
            'prospective_NBA_model_shadow': ['baseline', 'candidate']}
    if (trial['status'] not in arms or trial['classes'] != classes
            or trial['policy']['settlement'] != 'INCLUDING_OVERTIME' or now.tzinfo is None):
        raise ValueError('Unexpected NBA trial contract')
    indexed = {}
    for event in results:
        result = normalize_event(event)
        if result:
            key = result['home_team'], result['away_team'], pd.Timestamp(result['date'])
            indexed.setdefault(key, []).append(result)
    rows = []; labels = []; probabilities = {arm: [] for arm in arms[trial['status']]}; days = set(); ids = set()
    for fixture in trial['fixtures']:
        if str(fixture['id']) in ids:
            raise ValueError('Duplicate frozen NBA fixture ID')
        ids.add(str(fixture['id']))
        kickoff = pd.Timestamp(fixture['kickoff']); generated = pd.Timestamp(fixture['generated_at'])
        cutoff = pd.Timestamp(fixture['feature_cutoff'])
        if (any(t.tzinfo is None for t in [kickoff, generated, cutoff])
                or not cutoff <= generated < kickoff or generated > now):
            raise ValueError('Invalid prospective NBA forecast timing')
        for arm in probabilities:
            p = np.asarray(fixture['probabilities'][arm], dtype=float)
            if p.shape != (2,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1):
                raise ValueError('Invalid frozen NBA probabilities')
        matches = indexed.get((fixture['home'], fixture['away'], kickoff), [])
        row = {'id': fixture['id'], 'kickoff': fixture['kickoff'], 'status': 'pending'}
        if len(matches) > 1:
            row['status'] = 'ambiguous_result'
        elif len(matches) == 1 and kickoff < now:
            result = matches[0]
            winner = 'home_win' if result['home_score'] > result['away_score'] else 'away_win'
            labels.append(classes.index(winner)); days.add(kickoff.date())
            for arm in probabilities:
                probabilities[arm].append(fixture['probabilities'][arm])
            row.update(status='settled', result=winner, home_score=result['home_score'],
                       away_score=result['away_score'], independent_event_id=result['id'])
        rows.append(row)
    metrics = {arm: probability_metrics(np.asarray(labels), np.asarray(values), classes)
               for arm, values in probabilities.items()} if labels else {}
    enough = len(labels) >= trial['policy']['minimum_settled'] and len(days) >= trial['policy']['minimum_match_days']
    return {'assessed_at': now.isoformat(), 'settled': len(labels), 'distinct_settled_days': len(days),
            'pending': sum(row['status'] == 'pending' for row in rows), 'fixtures': rows, 'metrics': metrics,
            'status': 'minimum_sample_reached_requires_review' if enough else 'collecting_evidence',
            'promotion_authorized': False, 'production_changed': False}


def run(directory: Path) -> dict:
    payload = (directory/'trial.json').read_bytes(); digest = hashlib.sha256(payload).hexdigest()
    if digest != (directory/'trial.sha256').read_text().strip():
        raise ValueError('Frozen NBA trial checksum mismatch')
    trial = json.loads(payload)
    for source in trial['schedule_sources']:
        if hashlib.sha256((directory/source['file']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Frozen NBA schedule checksum mismatch')
    now = pd.Timestamp.now(tz='UTC')
    output = directory/'assessments'/now.strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, exist_ok=False)
    started = [{'date': f['kickoff']} for f in trial['fixtures'] if pd.Timestamp(f['kickoff']) < now]
    days = capture_days(started) if started else []
    results = []; sources = []; errors = []
    for day in days:
        response = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                                params={'dates': day.strftime('%Y%m%d'), 'limit': 100}, timeout=30)
        path = output/f'{day.strftime("%Y%m%d")}.json'; path.write_bytes(response.content)
        sources.append({'file': path.name, 'sha256': hashlib.sha256(response.content).hexdigest(),
                        'observed_at': pd.Timestamp.now(tz='UTC').isoformat(), 'url': response.url,
                        'status': response.status_code})
        if response.status_code != 200:
            errors.append({'day': str(day), 'status': response.status_code})
            continue
        results.extend(response.json().get('events', []))
    report = assess(trial, results, pd.Timestamp.now(tz='UTC'))
    report.update(trial_sha256=digest, result_sources=sources, source_errors=errors)
    (output/'assessment.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: report[k] for k in ['status', 'settled', 'pending', 'source_errors']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    run(parser.parse_args().trial)
