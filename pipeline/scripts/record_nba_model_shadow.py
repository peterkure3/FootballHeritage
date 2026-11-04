"""Freeze prospective NBA original-versus-inactivity forecasts on common history."""
import argparse
from copy import deepcopy
import hashlib
import heapq
import json
from pathlib import Path
import shutil

import joblib
import numpy as np
import pandas as pd

from models.nba_accuracy_research import InactivityState
from models.sport_data import canonical_games
from models.sport_features import SportState, FEATURES, HISTORY_FEATURES
from models.training_resources import training_threads


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_states(history, cutoff):
    """Replay queries/resolved results, with the training next-day availability floor."""
    if cutoff.tzinfo is None:
        raise ValueError('Timezone-aware history cutoff required')
    states = {'baseline': SportState('basketball'), 'candidate': InactivityState('basketball')}
    pending = []; sequence = 0; effective = 0

    def release(boundary):
        nonlocal effective
        while pending and pending[0][0] <= boundary:
            _, _, game = heapq.heappop(pending)
            for state in states.values():
                state.update(game)
            effective += 1

    for day, block in history[history.date.lt(cutoff)].groupby(history.date.dt.normalize(), sort=True):
        release(day)
        for game in block.to_dict('records'):
            states['candidate'].vector(game)
            available = max(game['result_available_at'], day + pd.Timedelta(days=1))
            heapq.heappush(pending, (available, sequence, game)); sequence += 1
    release(cutoff)
    return states, effective


def forecast_features(states, game):
    # Candidate queries can reset ratings; one future fixture must not mutate another.
    return {arm: pd.DataFrame([deepcopy(state).vector(game)], columns=FEATURES)
            for arm, state in states.items()}


def run(bundle: Path, candidate: Path, fresh: Path, schedule_trial: Path, output: Path):
    metadata = json.loads((bundle/'metrics.json').read_text())
    report = json.loads((candidate/'report.json').read_text())
    if sha(bundle/'dataset.parquet') != metadata['dataset_sha256'] or sha(bundle/'model.pkl') != metadata['model_sha256']:
        raise ValueError('Baseline artifact checksum mismatch')
    if (sha(candidate/'history_model.pkl') != report['candidate_model_sha256']
            or report['dataset_sha256'] != metadata['dataset_sha256']
            or report['baseline_model_sha256'] != metadata['model_sha256']
            or report['feature_contract']['schema'] != 'nba-inactivity-90-50-research-1.0'):
        raise ValueError('Frozen inactivity candidate contract mismatch')
    for file, digest in report['source_sha256'].items():
        if sha(Path(file)) != digest:
            raise ValueError('Frozen candidate feature implementation changed')
    reconciliation = json.loads((fresh/'manifest.json').read_text())
    if sha(fresh/'reconciled.jsonl') != reconciliation['normalized_sha256']:
        raise ValueError('Reconciled history checksum mismatch')
    for source in reconciliation['sources']:
        if sha(fresh/source['file']) != source['sha256']:
            raise ValueError('Reconciled raw source changed')
    schedule = json.loads((schedule_trial/'trial.json').read_text())
    if sha(schedule_trial/'trial.json') != (schedule_trial/'trial.sha256').read_text().strip():
        raise ValueError('Frozen schedule trial changed')
    for source in schedule['schedule_sources']:
        if sha(schedule_trial/source['file']) != source['sha256']:
            raise ValueError('Frozen schedule source changed')
    history = pd.read_parquet(bundle/'dataset.parquet')
    additional = [json.loads(line) for line in (fresh/'reconciled.jsonl').read_text().splitlines()]
    history = canonical_games(history.to_dict('records') + additional, 'basketball')
    if set(history.league) != {'basketball_nba'}:
        raise ValueError('NBA-only history required')
    cutoff = pd.Timestamp.now(tz='UTC')
    states, effective = replay_states(history, cutoff)
    models = {'baseline': joblib.load(bundle/'model.pkl'), 'candidate': joblib.load(candidate/'history_model.pkl')}
    rows = []; excluded = []; seen = set()
    with training_threads(2):
        for fixture in schedule['fixtures']:
            if fixture['id'] in seen:
                raise ValueError('Duplicate scheduled fixture ID')
            seen.add(fixture['id'])
            kickoff = pd.Timestamp(fixture['kickoff'])
            if kickoff <= pd.Timestamp.now(tz='UTC'):
                excluded.append({'id': fixture['id'], 'reason': 'already_started'}); continue
            game = {'date': kickoff, 'league': 'basketball_nba', 'home_team': fixture['home'], 'away_team': fixture['away']}
            inputs = forecast_features(states, game)
            probabilities = {}
            for arm, features in inputs.items():
                X = features if arm == 'baseline' else features[HISTORY_FEATURES]
                p = models[arm].predict_proba(X)[0]
                if p.shape != (2,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1):
                    raise ValueError('Invalid NBA model probability')
                probabilities[arm] = p.tolist()
            generated = pd.Timestamp.now(tz='UTC')
            if generated >= kickoff:
                excluded.append({'id': fixture['id'], 'reason': 'started_during_forecast'}); continue
            rows.append({'id': fixture['id'], 'home': fixture['home'], 'away': fixture['away'],
                'kickoff': kickoff.isoformat(), 'generated_at': generated.isoformat(), 'feature_cutoff': cutoff.isoformat(),
                'probabilities': probabilities, 'features': {arm: X.iloc[0].to_dict() for arm, X in inputs.items()}})
    output.mkdir(parents=True, exist_ok=False)
    sources = schedule['schedule_sources']
    for source in sources:
        shutil.copyfile(schedule_trial/source['file'], output/source['file'])
    trial = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'status': 'prospective_NBA_model_shadow',
        'production_changed': False, 'active': False, 'classes': metadata['classes'],
        'model_hashes': {'baseline': metadata['model_sha256'], 'candidate': report['candidate_model_sha256']},
        'baseline_history_sha256': metadata['dataset_sha256'], 'additional_history_sha256': reconciliation['normalized_sha256'],
        'effective_history_games': effective, 'common_input_history': True, 'schedule_sources': sources,
        'feature_contract': report['feature_contract'], 'source_schedule_trial_sha256': sha(schedule_trial/'trial.json'),
        'input_paths': {'bundle': str(bundle), 'candidate': str(candidate), 'fresh': str(fresh)},
        'recorder_sha256': sha(Path(__file__)), 'fixtures': rows, 'excluded': excluded,
        'policy': {'settlement': 'INCLUDING_OVERTIME', 'minimum_settled': 200, 'minimum_match_days': 20,
            'selection': 'earliest prospective forecast per provider ID', 'no_odds_or_bets': True,
            'availability': 'max(actual observation, next UTC day); never later than feature cutoff'},
        'limitations': ['No prospective accuracy gain established.', 'Schedule reused from verified earlier capture; changes may occur.',
            'Inherited historical availability assumptions and uneven coverage.',
            'Future intervening results are unknown; original freshness trial is a separate hypothesis.']}
    payload = json.dumps(trial, indent=2, allow_nan=False).encode('utf-8')
    (output/'trial.json').write_bytes(payload); (output/'trial.sha256').write_text(hashlib.sha256(payload).hexdigest()+'\n')
    (output/'recorder-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'recorded': len(rows), 'excluded': len(excluded), 'effective_history_games': effective,
        'changed_winner_predictions': sum(int(np.argmax(r['probabilities']['baseline']) != np.argmax(r['probabilities']['candidate'])) for r in rows)}, indent=2))
    return trial


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['bundle', 'candidate', 'fresh', 'schedule-trial', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); run(args.bundle, args.candidate, args.fresh, args.schedule_trial, args.output)
