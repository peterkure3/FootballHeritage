"""Freeze paired pregame accuracy forecasts; no bets or production writes."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd

from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL
from etl.fetch_raw_data import FootballDataOrgFetcher
from models.data import canonical_matches, team_key
from models.features import FeatureState, FEATURE_NAMES
from models.league_data import identity
from models.training_resources import training_threads


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_from(history: pd.DataFrame, cutoff: pd.Timestamp) -> FeatureState:
    state = FeatureState()
    for row in canonical_matches([history]).to_dict('records'):
        if row['date'] < cutoff.normalize() and pd.notna(row['result']):
            state.update(row)
    return state


def forecast_pair(history: pd.DataFrame, baseline: Any, corrected: Any,
                  aliases: dict[str, str], fixtures: list[dict],
                  now: pd.Timestamp) -> tuple[list[dict], list[dict]]:
    original_state = state_from(history, now)
    reviewed = history.copy()
    for side in ['home', 'away']:
        reviewed[side+'_team'] = reviewed[side+'_team'].map(lambda name: identity(name, aliases))
    corrected_state = state_from(reviewed, now)
    known = set(history.home_key) | set(history.away_key)
    corrected_known = {identity(name, aliases) for name in pd.concat([history.home_team, history.away_team])}
    rows, exclusions, seen = [], [], set()
    for fixture in fixtures:
        match_id = str(fixture['id'])
        if match_id in seen:
            raise ValueError('Duplicate provider fixture ID')
        seen.add(match_id)
        kickoff = pd.Timestamp(fixture['utcDate'])
        home, away = fixture['homeTeam']['name'], fixture['awayTeam']['name']
        if kickoff.tzinfo is None or kickoff <= now or fixture['status'] not in {'SCHEDULED', 'TIMED'}:
            exclusions.append({'id': match_id, 'reason': 'not_future_scheduled'})
            continue
        old_home, old_away = team_key(home), team_key(away)
        new_home, new_away = identity(home, aliases), identity(away, aliases)
        if old_home not in known or old_away not in known or new_home not in corrected_known or new_away not in corrected_known:
            exclusions.append({'id': match_id, 'reason': 'unmatched_history_in_one_or_both_arms', 'home': home, 'away': away})
            continue
        features = {'original': original_state.vector(old_home, old_away),
                    'reviewed': corrected_state.vector(new_home, new_away)}
        probabilities = {}
        for name, model in [('original', baseline), ('reviewed', corrected)]:
            with training_threads(2):
                p = model.predict_proba(pd.DataFrame([features[name]], columns=FEATURE_NAMES))[0]
            if not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1):
                raise ValueError('Invalid probability vector')
            probabilities[name] = p.tolist()
        generated = pd.Timestamp.now(tz='UTC')
        if generated >= kickoff:
            exclusions.append({'id': match_id, 'reason': 'started_during_inference'})
            continue
        rows.append({'id': match_id, 'home': home, 'away': away, 'kickoff': kickoff.isoformat(),
                     'competition': fixture['competition']['code'], 'generated_at': generated.isoformat(),
                     'feature_cutoff': now.isoformat(), 'probabilities': probabilities, 'features': features})
    return rows, exclusions


def run(candidate: Path, output: Path, competitions: list[str], days: int) -> dict:
    if not 1 <= days <= 7:
        raise ValueError('Use a bounded one-to-seven day window')
    output.mkdir(parents=True, exist_ok=False)
    report = json.loads((candidate/'report.json').read_text())
    bundle = Path(report['source_bundle'])
    dataset = bundle/'dataset.parquet'
    model_path = bundle/'model_v2.1.0.pkl'
    if checksum(dataset) != report['source_dataset_sha256'] or checksum(model_path) != report['source_model_sha256']:
        raise ValueError('Original candidate changed')
    if checksum(candidate/'history_model.pkl') != report['model_sha256']:
        raise ValueError('Reviewed candidate changed')
    now = pd.Timestamp.now(tz='UTC')
    history = pd.read_parquet(dataset)
    fetcher = FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL)
    sources, fixtures, errors = [], [], []
    for code in competitions:
        try:
            payload = fetcher.fetch_matches(code, now.date().isoformat(), (now+timedelta(days=days)).date().isoformat())
            observed = datetime.now(timezone.utc).isoformat()
            path = output/f'{code}.json'
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            sources.append({'path': path.name, 'sha256': checksum(path), 'observed_at': observed,
                            'url': FOOTBALL_DATA_ORG_BASE_URL+f'/competitions/{code}/matches'})
            fixtures.extend(payload.get('matches', []))
        except Exception as exc:
            errors.append({'competition': code, 'error': type(exc).__name__})
        time.sleep(7)
    baseline = joblib.load(model_path).history_
    corrected = joblib.load(candidate/'history_model.pkl')
    rows, exclusions = forecast_pair(history, baseline, corrected, report['alias_map'], fixtures, now)
    trial = {'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'prospective_accuracy_shadow',
        'active': False, 'production_changed': False, 'classes': report['classes'], 'sources': sources,
        'model_hashes': {'original': checksum(model_path), 'reviewed': checksum(candidate/'history_model.pkl')},
        'history_sha256': checksum(dataset), 'alias_map': report['alias_map'],
        'policy': {'selection': 'all_future_scheduled_with_history_in_both_arms', 'no_odds_or_bets': True,
            'score_policy': 'REGULATION_TIME', 'minimum_settled_for_assessment': 200,
            'minimum_distinct_match_days': 20, 'no_threshold_tuning': True,
            'history_rule': 'Only frozen snapshot results dated before current UTC day'},
        'fixtures': rows, 'exclusions': exclusions, 'source_errors': errors}
    encoded = json.dumps(trial, indent=2, allow_nan=False).encode('utf-8')
    with (output/'trial.json').open('xb') as stream:
        stream.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    (output/'trial.sha256').write_text(digest+'\n')
    print(json.dumps({'output': str(output), 'trial_sha256': digest, 'recorded': len(rows),
                      'excluded': len(exclusions), 'source_errors': errors}, indent=2))
    return trial


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--competitions', nargs='+', default=['PL','PD','BL1','SA','FL1'])
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    run(args.candidate, args.output, args.competitions, args.days)
