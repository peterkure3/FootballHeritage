"""Train and verify a new NBA-only candidate using the existing sport trainer."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from config import MODEL_DIR
from models import train_sports
from models.sport_data import load_games
from models.sport_predict import predict_candidate


def main():
    games = load_games('basketball')
    nba = games.loc[games.league.eq('basketball_nba')].copy().reset_index(drop=True)
    nba.attrs['data_quality'] = {
        **games.attrs.get('data_quality', {}),
        'scope': 'NBA_ONLY', 'other_league_games_excluded': len(games) - len(nba),
        'scrapling_preseason_excluded': True,
    }
    assert len(nba) >= 500 and nba.league.eq('basketball_nba').all()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = MODEL_DIR / 'candidates/sports' / run_id
    print(json.dumps({'run_id': run_id, 'nba_games': len(nba),
        'history_start': nba.date.min().isoformat(), 'history_end': nba.date.max().isoformat()}), flush=True)
    with patch.object(train_sports, 'load_games', return_value=nba), threadpool_limits(limits=2):
        reports = train_sports.train_all(['basketball'], output)
    report = reports['basketball']
    assert report['status'] == 'candidate', report
    assert report['training_leagues'] == ['basketball_nba']
    assert report['data_by_league'] == {'basketball_nba': len(nba)}
    directory = output / 'basketball'
    for filename, key in [('model.pkl', 'model_sha256'), ('dataset.parquet', 'dataset_sha256')]:
        assert hashlib.sha256((directory / filename).read_bytes()).hexdigest() == report[key]
    # Only reload this run's locally produced artifact.
    model = joblib.load(directory / 'model.pkl')
    assert model.history_model is not None
    kickoff = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    preview = predict_candidate(run_id, 'basketball', 'Boston Celtics', 'Los Angeles Lakers',
        kickoff, 'basketball_nba')
    assert np.isclose(sum(preview['probabilities'].values()), 1)
    assert all(0 <= p <= 1 for p in preview['probabilities'].values())
    evidence = {'candidate_id': run_id, 'directory': str(directory.resolve()),
        'completed_games': len(nba), 'history_start': nba.date.min().isoformat(),
        'history_through': nba.date.max().isoformat(), 'data_quality': nba.attrs['data_quality'],
        'splits': report['splits'], 'test': report['test'],
        'training_prior_baseline': report['training_prior_baseline'],
        'history_selection': report['history_selection'], 'market_selection': report['market_selection'],
        'odds_complete': report['odds_complete'], 'market_model_trained': model.market_model is not None,
        'model_sha256': report['model_sha256'], 'dataset_sha256': report['dataset_sha256'],
        'preview': preview, 'active': False}
    target = ROOT / 'stages/03-build/output/nba-training-20261015.json'
    target.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == '__main__':
    main()
