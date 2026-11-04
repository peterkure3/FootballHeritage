"""Refresh active-model forecasts from fresh quotes while preserving history."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import text
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from api.db import get_db_connection
from api.prediction_dashboard import fixtures, OUTCOMES
from config import MODEL_DIR, MODEL_VERSION
from etl.utils import save_json
from models.features import FEATURE_NAMES
from models.predict_v2 import (load_model_artifacts, get_team_elo_ratings,
                              load_feature_history, build_feature_vector)


def main() -> None:
    before = fixtures(1, 50)
    if before['total_count'] > 50:
        raise ValueError('Pagination required before refreshing all forecasts')
    paths = [MODEL_DIR / f'{name}_v{MODEL_VERSION}.pkl'
             for name in ['model', 'label_encoder', 'features', 'scaler']]
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.exists()}
    model, encoder, names, scaler = load_model_artifacts()
    engine = get_db_connection()
    cutoff = pd.Timestamp.now(tz='UTC')
    elo = get_team_elo_ratings(engine) if names != FEATURE_NAMES else {}
    history = load_feature_history(engine, cutoff) if names == FEATURE_NAMES else None
    forecasts, inputs = [], []
    with threadpool_limits(limits=1):
        for fixture in before['items']:
            quotes = [q for q in fixture['market']['quotes'] if q['fresh']]
            if not quotes:
                continue
            prices = {key: sum(q['prices'][key] for q in quotes) / len(quotes) for key in OUTCOMES}
            features = build_feature_vector(fixture['home_team'], fixture['away_team'], engine,
                elo, prices, names, cutoff=cutoff, history=history)
            if scaler is not None:
                features = pd.DataFrame(scaler.transform(features), columns=features.columns)
            probabilities = dict(zip(encoder.classes_, map(float, model.predict_proba(features)[0])))
            assert abs(sum(probabilities.values()) - 1) < 1e-6
            assert all(0 <= value <= 1 for value in probabilities.values())
            forecasts.append({'match_id': fixture['match_id'], 'model_version': MODEL_VERSION,
                'winner': str(encoder.inverse_transform([model.predict(features)[0]])[0]),
                'home_prob': probabilities['home_win'], 'draw_prob': probabilities['draw'],
                'away_prob': probabilities['away_win']})
            inputs.append({'match_id': fixture['match_id'], 'averaged_prices': prices, 'quotes': quotes})
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    generated = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as connection:
        for forecast in forecasts:
            identifier = connection.execute(text('''INSERT INTO predictions
                (match_id,model_version,winner,home_prob,draw_prob,away_prob,created_at)
                SELECT :match_id,:model_version,:winner,:home_prob,:draw_prob,:away_prob,:created_at
                WHERE EXISTS (SELECT 1 FROM matches WHERE match_id=:match_id AND date>:created_at
                    AND result IS NULL AND UPPER(COALESCE(status,'')) NOT IN
                    ('FINISHED','CANCELLED','CANCELED','POSTPONED','LIVE','IN_PLAY','PAUSED'))
                RETURNING id'''), forecast | {'created_at': generated}).scalar_one()
            forecast['prediction_id'] = identifier
    refreshed = fixtures(1, 50)
    updated_ids = {row['match_id'] for row in forecasts}
    rows = []
    for fixture in refreshed['items']:
        if fixture['match_id'] not in updated_ids:
            continue
        prediction = fixture['prediction']
        probabilities = prediction['probabilities']
        assert prediction['generated_at'] == generated.isoformat() + '+00:00'
        for comparison in fixture['market']['comparisons']:
            p = probabilities[comparison['outcome']]
            assert abs(comparison['estimated_ev_units'] - (p * comparison['decimal_odds'] - 1)) < 1e-12
        rows.append({key: fixture[key] for key in ['match_id', 'home_team', 'away_team', 'kickoff', 'competition']} |
                    {'probabilities': probabilities, 'market_consensus': fixture['market']['consensus'],
                     'outcome_comparisons': fixture['market']['comparisons']})
    assert len(rows) == len(forecasts) and all(len(row['outcome_comparisons']) == 3 for row in rows)
    report = {'generated_at': generated.isoformat() + 'Z', 'feature_cutoff': cutoff.isoformat(),
        'model_version': MODEL_VERSION, 'active_model_changed': False,
        'artifact_sha256': {path.name: digest for path, digest in hashes.items()},
        'forecasts_refreshed': len(rows), 'outcome_comparisons': 3 * len(rows),
        'without_fresh_quotes': len(before['items']) - len(rows),
        'previous_forecasts_preserved': True, 'inputs': inputs, 'fixtures': rows}
    save_json(report, ROOT / 'stages/03-build/output/probability-ev-outcomes-20261015.json')
    print(json.dumps({key: value for key, value in report.items() if key not in {'inputs', 'fixtures'}}, indent=2))
    print(json.dumps(rows[:2], indent=2))


if __name__ == '__main__':
    main()
