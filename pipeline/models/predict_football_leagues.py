"""Replay evaluated league artifacts and atomically publish upcoming forecasts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from api.db import get_db_connection
from config import MODEL_DIR, PROCESSED_DATA_DIR
from football_competitions import LEAGUES
from models.features import FEATURE_NAMES, FeatureState
from models.league_data import identity_aliases, identity, load_histories
from models.training_resources import training_threads

SNAPSHOT = PROCESSED_DATA_DIR/'league_predictions.json'
REGISTRY = MODEL_DIR/'league_models/serving.json'


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)


def league_state(history: pd.DataFrame, cutoff: pd.Timestamp) -> FeatureState:
    state = FeatureState()
    for row in history[history.date.lt(cutoff.normalize())].sort_values('date').to_dict('records'):
        state.update(row)
    return state


def predict(run: Path, publish: bool = False) -> dict:
    report = json.loads((run/'report.json').read_text(encoding='utf-8'))
    identity_path = run/'league_identities.json'
    if hashlib.sha256(identity_path.read_bytes()).hexdigest() != report['identity_sha256']:
        raise ValueError('Model identity dictionary checksum mismatch')
    aliases = identity_aliases(identity_path)
    current_histories = load_histories(aliases=aliases)
    now = pd.Timestamp.now(tz='UTC')
    with get_db_connection().connect() as connection:
        fixtures = pd.read_sql(text("""SELECT match_id,competition,home_team,away_team,date FROM matches
            WHERE date > (NOW() AT TIME ZONE 'UTC') AND result IS NULL
            AND UPPER(COALESCE(status,'')) IN ('SCHEDULED','TIMED') ORDER BY date,match_id"""), connection)
    predictions, coverage = [], {}
    for code, metrics in report['leagues'].items():
        directory = run/code
        for filename in ['model.pkl', 'dataset.parquet']:
            expected = metrics[filename.replace('.', '_') + '_sha256']
            if hashlib.sha256((directory/filename).read_bytes()).hexdigest() != expected:
                raise ValueError('League model artifact checksum mismatch')
        if pd.Timestamp(metrics['trained_at']) > now:
            raise ValueError('Model training timestamp is in the future')
        history = pd.read_parquet(directory/'dataset.parquet')
        known = set(history.home_key) | set(history.away_key)
        live_history = current_histories.get(code, history)
        state = league_state(live_history, now)
        model = joblib.load(directory/'model.pkl')
        competition = next(row[1] for row in LEAGUES if row[0] == code)
        league_fixtures = fixtures[fixtures.competition.eq(competition)]
        coverage[code] = {'fixtures': len(league_fixtures), 'predictions': 0, 'excluded': []}
        for row in league_fixtures.itertuples():
            home, away = identity(row.home_team, aliases), identity(row.away_team, aliases)
            if home not in known or away not in known:
                coverage[code]['excluded'].append({'match_id': row.match_id, 'reason': 'missing_team_history',
                    'home': home, 'away': away})
                continue
            X = pd.DataFrame([state.vector(home, away)], columns=FEATURE_NAMES)
            with training_threads(2):
                probabilities = model.predict_proba(X)[0]
            if not np.isfinite(probabilities).all() or (probabilities < 0).any() or not np.isclose(probabilities.sum(), 1):
                raise ValueError('Invalid forecast probabilities')
            generated = pd.Timestamp.now(tz='UTC')
            kickoff = pd.Timestamp(row.date).tz_localize('UTC')
            if generated >= kickoff:
                continue
            predictions.append({'match_id': int(row.match_id), 'competition': competition,
                'home_team': row.home_team, 'away_team': row.away_team, 'kickoff': kickoff.isoformat(),
                'model_version': f'league-{code}-{run.name}', 'model_kind': 'evaluated_league_candidate',
                'probabilities': dict(zip(metrics['classes'], probabilities.tolist())),
                'winner': metrics['classes'][int(probabilities.argmax())], 'active': False,
                'status': 'current', 'generated_at': generated.isoformat(), 'feature_cutoff': now.isoformat(),
                'trained_at': metrics['trained_at'], 'history_through': live_history.date.max().isoformat(),
                'input_quality': 'league_history', 'market_features_used': False,
                'test_metrics': {key: metrics['test'][key] for key in ['samples','accuracy','log_loss','brier_score']}})
            coverage[code]['predictions'] += 1
    payload = {'schema_version': 1, 'run_id': run.name,
               'generated_at': datetime.now(timezone.utc).isoformat(), 'coverage': coverage, 'predictions': predictions}
    artifact = run/('forecasts_' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    artifact.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding='utf-8')
    if publish:
        if any(row['excluded'] for row in coverage.values()):
            raise ValueError('League forecast coverage incomplete; saved audit, serving unchanged')
        atomic_json(SNAPSHOT, payload)
        atomic_json(REGISTRY, {'run_directory': run.name})
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    run = args.run_dir
    if run is None:
        run = MODEL_DIR/'league_models'/json.loads(REGISTRY.read_text(encoding='utf-8'))['run_directory']
    payload = predict(run, args.publish)
    print(json.dumps({'run_id': payload['run_id'], 'coverage': payload['coverage'], 'predictions': len(payload['predictions'])}, indent=2))


if __name__ == '__main__':
    main()
