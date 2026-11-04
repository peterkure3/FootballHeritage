"""Fresh-process source, persisted research model and nflfastR feature verification."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from models.train_gridiron_sources import verify_model
from models.gridiron_sources import summarize_pbp
from models.gridiron_efficiency import build_efficiency_features
from models.train_sports import supervised_splits
from models.validation import probability_metrics


def main():
    evidence = json.loads((ROOT / 'stages/03-build/output/gridiron-training-20261015.json').read_text())
    capture = Path(evidence['capture'])
    manifest = json.loads((capture / 'manifest.json').read_text())
    assert not manifest['failures']
    for name, row in manifest['captures'].items():
        assert hashlib.sha256((capture / name).read_bytes()).hexdigest() == row['sha256']
    verification = {'candidate_id': evidence['candidate_id'], 'source_checksums': len(manifest['captures']),
        'models': {}, 'source_counts': {}}
    with threadpool_limits(limits=2):
        for sport in ['nfl', 'ncaaf']:
            verification['models'][sport] = {}
            for mode, root in [('history', 'candidate_root'), ('archive_odds', 'research_root')]:
                report = evidence['models'][sport][mode]
                verification['models'][sport][mode] = verify_model(Path(evidence[root]) / sport, sport, report)
            path = capture / 'normalized' / f'{sport}_games_odds.parquet'
            frame = pd.read_parquet(path)
            assert len(pd.read_csv(path.with_suffix('.csv'))) == len(frame)
            assert frame.odds_observed_at.isna().all()
            assert not frame.provider_event_id.duplicated().any()
            verification['source_counts'][sport] = {'completed_games': len(frame),
                'odds_pairs': int(frame[['home_win','away_win']].notna().all(axis=1).sum()),
                'date_start': frame.date.min().isoformat(), 'date_end': frame.date.max().isoformat(),
                'ties': int(frame.result.eq('draw').sum())}
        directory = Path(evidence['research_root']) / 'nfl_efficiency'
        report = json.loads((directory / 'metrics.json').read_text())
        for filename, key in [('model.pkl','model_sha256'), ('dataset.parquet','dataset_sha256')]:
            assert hashlib.sha256((directory / filename).read_bytes()).hexdigest() == report[key]
        games = pd.read_parquet(directory / 'dataset.parquet')
        stats = summarize_pbp(capture)
        X = build_efficiency_features(games, stats)
        np.testing.assert_allclose(X, pd.read_parquet(directory / 'features.parquet'))
        test = supervised_splits(games, 'nfl')[0]['test']
        y = games.iloc[test].result.map({'away_win':0,'home_win':1}).to_numpy()
        p = joblib.load(directory / 'model.pkl').predict_proba(X.iloc[test])
        metrics = probability_metrics(y, p, ['away_win','home_win'])
        for key in ['samples','accuracy','log_loss','brier_score']:
            np.testing.assert_allclose(metrics[key], report['test'][key], atol=1e-12, rtol=0)
        verification['models']['nfl']['pbp_efficiency'] = {'raw_features_reproduced': True,
            'artifact_checksums': True, 'held_out_metrics_reproduced': True, 'test': metrics}
    verification['source_counts']['nflfastR'] = {'team_game_aggregates': len(stats),
        'raw_play_rows': {path.name: len(pd.read_parquet(path, columns=['game_id'])) for path in capture.glob('nfl_pbp_*.parquet')}}
    quotes = pd.read_csv(capture / 'normalized/cfbd_quotes.csv')
    verification['source_counts']['cfbd_bookmaker_rows'] = len(quotes)
    verification['source_counts']['cfbd_providers'] = sorted(quotes.provider.unique().tolist())
    verification['source_counts']['cfbd_raw_games'] = sum(len(json.loads(path.read_text())) for path in capture.glob('cfbd_games_*.json'))
    target = ROOT / 'stages/03-build/output/gridiron-verification-20261015.json'
    target.write_text(json.dumps(verification, indent=2), encoding='utf-8')
    print(json.dumps({'source_checksums': verification['source_checksums'],
        'source_counts': verification['source_counts'], 'all_five_models_verified': True}, indent=2))


if __name__ == '__main__':
    main()
