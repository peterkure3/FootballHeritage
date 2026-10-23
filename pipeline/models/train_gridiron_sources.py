"""Train separate source-backed NFL/college candidates and archival research models."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from config import MODEL_DIR
from etl.fetch_gridiron_sources import DEFAULT_OUTPUT
from models import train_sports
from models.gridiron_sources import load_capture, summarize_pbp
from models.gridiron_efficiency import build_efficiency_features, EFFICIENCY_FEATURES
from models.sport_features import build_features
from models.sport_predict import predict_candidate
from models.validation import probability_metrics


def verify_model(directory: Path, sport: str, report: dict) -> dict:
    for name, key in [('model.pkl', 'model_sha256'), ('dataset.parquet', 'dataset_sha256')]:
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != report[key]:
            raise ValueError('Saved artifact checksum mismatch')
    frame = pd.read_parquet(directory / 'dataset.parquet')
    model = joblib.load(directory / 'model.pkl')
    X = build_features(frame, sport)
    splits, _ = train_sports.supervised_splits(frame, sport)
    test = splits['test']
    classes = report['classes']
    y = np.array([classes.index(value) if value in classes else -1 for value in frame.result])
    probabilities = model.predict_proba(X.iloc[test])
    actual = probability_metrics(y[test], probabilities, classes)
    for key in ['accuracy', 'log_loss', 'brier_score']:
        if not np.isclose(actual[key], report['test'][key]):
            raise ValueError('Held-out metrics failed reproduction')
    return {'checksums': True, 'reload': True, 'held_out_metrics_reproduced': True,
        'odds_by_partition': {name: int(X.iloc[index].odds_missing.eq(0).sum()) for name,index in splits.items()},
        'market_model_present': model.market_model is not None}


def train_efficiency(games: pd.DataFrame, stats: pd.DataFrame, directory: Path) -> dict:
    games = games[games.provider_event_id.isin(set(stats.game_id))].reset_index(drop=True)
    X = build_efficiency_features(games, stats)
    classes = ['away_win', 'home_win']
    y = np.array([classes.index(r) if r in classes else -1 for r in games.result])
    splits, exclusions = train_sports.supervised_splits(games, 'nfl')
    model, selection = train_sports.select_expert(X, y, splits, EFFICIENCY_FEATURES, np.ones(len(games), dtype=bool))
    if model is None:
        return {'status': 'insufficient_data', 'selection': selection}
    test = splits['test']
    metrics = probability_metrics(y[test], model.predict_proba(X.iloc[test]), classes)
    development = np.concatenate([splits['train'], splits['tune']])
    prior = np.bincount(y[development], minlength=2) / len(development)
    baseline = probability_metrics(y[test], np.tile(prior, (len(test), 1)), classes)
    directory.mkdir(parents=True, exist_ok=False)
    games.to_parquet(directory / 'dataset.parquet', index=False)
    X.to_parquet(directory / 'features.parquet', index=False)
    joblib.dump(model, directory / 'model.pkl')
    loaded = joblib.load(directory / 'model.pkl')
    np.testing.assert_allclose(model.predict_proba(X.iloc[test]), loaded.predict_proba(X.iloc[test]))
    report = {'sport': 'nfl', 'status': 'research_candidate', 'model': 'NFLFAST_R_EFFICIENCY',
        'active': False, 'research_only': True, 'uses_odds': False, 'completed_games': len(games),
        'features': EFFICIENCY_FEATURES, 'selection': selection, 'test': metrics,
        'training_prior_baseline': baseline, 'split_exclusions': exclusions,
        'splits': {name: {'samples': len(index), 'start': games.iloc[index].date.min().isoformat(),
            'end': games.iloc[index].date.max().isoformat()} for name,index in splits.items()},
        'model_sha256': hashlib.sha256((directory / 'model.pkl').read_bytes()).hexdigest(),
        'dataset_sha256': hashlib.sha256((directory / 'dataset.parquet').read_bytes()).hexdigest(),
        'limitation': 'Only past completed games enter rolling EPA/success rates. NFL ties excluded from winner labels. Recent-season research estimator; not exposed by the standard sport preview API.'}
    (directory / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def train(directory: Path, sports: list[str]) -> dict:
    frames, exports = load_capture(directory, sports)
    processed = directory / 'normalized'
    processed.mkdir(exist_ok=True)
    for sport, games in frames.items():
        games.to_parquet(processed / f'{sport}_games_odds.parquet', index=False)
        games.to_csv(processed / f'{sport}_games_odds.csv', index=False)
    for name, rows in exports.items():
        pd.DataFrame(rows).to_csv(processed / f'{name}.csv', index=False)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    candidate_root = MODEL_DIR / 'candidates/sports' / run_id
    research_root = MODEL_DIR / 'research/gridiron_sources' / run_id
    results, candidates = {}, {}
    for sport, native in frames.items():
        print(json.dumps({'sport': sport, 'games': len(native), 'archive_moneyline_pairs':
            int(native[['home_win','away_win']].notna().all(axis=1).sum())}), flush=True)
        results[sport] = {}
        for mode, root in [('history', candidate_root), ('archive_odds', research_root)]:
            games = native.copy()
            if mode == 'history':
                games[['home_win', 'away_win']] = np.nan
            with patch.object(train_sports, 'load_games', return_value=games), \
                    patch.object(train_sports, 'attach_moneylines', side_effect=lambda frame, sport: frame.copy()), \
                    threadpool_limits(limits=2):
                report = train_sports.train_sport(sport, root / sport)
                if report['status'] != 'candidate':
                    raise ValueError(f'Training failed: {sport}/{mode}: {report}')
                verified = verify_model(root / sport, sport, report)
            report.update(source_capture=str(directory.resolve()), active=False,
                source_odds_used=mode == 'archive_odds', odds_observation_verified=False)
            if mode == 'archive_odds':
                report.update(status='research_candidate', research_only=True,
                    limitation='Native-ID archival odds without verified quote observation timestamps. Retrospective research only; not a point-in-time betting backtest.')
            else:
                candidates[sport] = report
                candidate_root.mkdir(parents=True, exist_ok=True)
                (candidate_root / 'report.json').write_text(json.dumps(candidates, indent=2), encoding='utf-8')
            (root / sport / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            results[sport][mode] = report | {'verification': verified}
            print(json.dumps({'sport': sport, 'mode': mode, 'test_accuracy': report['test']['accuracy'],
                'market_expert': verified['market_model_present']}), flush=True)
        matchup = ('Kansas City Chiefs', 'Buffalo Bills') if sport == 'nfl' else ('Alabama', 'Georgia')
        preview = predict_candidate(run_id, sport, *matchup,
            (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            'americanfootball_nfl' if sport == 'nfl' else 'americanfootball_ncaaf', neutral_site=sport == 'ncaaf')
        results[sport]['preview'] = preview
    if 'nfl' in frames:
        stats = summarize_pbp(directory)
        if not stats.empty:
            stats.to_parquet(processed / 'nflfastR_team_game_efficiency.parquet', index=False)
            stats.to_csv(processed / 'nflfastR_team_game_efficiency.csv', index=False)
            with threadpool_limits(limits=2):
                results['nfl']['pbp_efficiency'] = train_efficiency(frames['nfl'], stats, research_root / 'nfl_efficiency')
            results['nfl']['pbp_team_game_rows'] = len(stats)
    evidence = {'candidate_id': run_id, 'capture': str(directory.resolve()), 'models': results,
        'candidate_root': str(candidate_root.resolve()), 'research_root': str(research_root.resolve())}
    (candidate_root / 'source_verification.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    target = Path(__file__).resolve().parents[2] / 'stages/03-build/output/gridiron-training-20261015.json'
    target.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({'candidate_id': run_id, 'report': str(target.resolve())}), flush=True)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--sports', nargs='+', choices=['nfl', 'ncaaf'], default=['nfl', 'ncaaf'])
    args = parser.parse_args()
    train(args.capture_dir, list(dict.fromkeys(args.sports)))


if __name__ == '__main__':
    main()
