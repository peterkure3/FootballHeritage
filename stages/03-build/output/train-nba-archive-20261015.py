"""Fit isolated NBA archive research models; undocumented quote times stay null."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from config import MODEL_DIR
from models import train_sports
from models.sport_data import canonical_games
from models.sport_features import build_features, HISTORY_FEATURES, live_features
from models.validation import chronological_split, probability_metrics

ARCHIVE = ROOT / 'pipeline/data/raw/historical/nba/free_archive/20261015'


def decimal_price(value):
    if pd.isna(value):
        return float('nan')
    value = float(value)
    if not np.isfinite(value) or abs(value) < 100:
        raise ValueError('Invalid American moneyline')
    return 1 + (value / 100 if value > 0 else 100 / abs(value))


def normalize_archive(raw):
    rows, excluded = [], []
    for identity, pair in raw.groupby('idGame', sort=True):
        home, away = pair[pair.locationGame.eq('H')], pair[pair.locationGame.eq('A')]
        if len(pair) != 2 or len(home) != 1 or len(away) != 1:
            excluded.append({'id': str(identity), 'reason': 'Expected one home and one away row'})
            continue
        h, a = home.iloc[0], away.iloc[0]
        equal = lambda x,y: (pd.isna(x) and pd.isna(y)) or x == y
        checks = [(h['idTeam'], a['idOpp']), (h['idOpp'], a['idTeam']),
            (h['dateGame'], a['dateGame']), (h['typeSeason'], a['typeSeason']),
            (h['nameTeam.own'], a['nameTeam.opp']), (h['nameTeam.opp'], a['nameTeam.own']),
            (h['ptsTeam.own'], a['ptsTeam.opp']), (h['ptsTeam.opp'], a['ptsTeam.own']),
            (h['teamML'], a['oppML']), (h['oppML'], a['teamML'])]
        if h['slugLeague'] != 'NBA' or a['slugLeague'] != 'NBA' or not all(equal(x,y) for x,y in checks):
            excluded.append({'id': str(identity), 'reason': 'Paired records disagree'})
            continue
        hs, aws = h['ptsTeam.own'], h['ptsTeam.opp']
        if hs == aws or bool(h['isWin']) != (hs > aws) or bool(a['isWin']) != (aws > hs):
            excluded.append({'id': str(identity), 'reason': 'Outcome and score disagree'})
            continue
        if h['typeSeason'] not in {'Regular Season', 'Playoffs'}:
            excluded.append({'id': str(identity), 'reason': 'Unsupported season type'})
            continue
        date = pd.Timestamp(h['dateGame'], tz='UTC')
        try:
            hp, ap = decimal_price(h['teamML']), decimal_price(h['oppML'])
        except ValueError:
            excluded.append({'id': str(identity), 'reason': 'Invalid moneyline'})
            continue
        rows.append({'date': date, 'result_available_at': date + pd.Timedelta(days=2),
            'league': 'basketball_nba', 'home_team': h['nameTeam.own'], 'away_team': h['nameTeam.opp'],
            'home_score': hs, 'away_score': aws, 'completed': True,
            'provider_event_id': str(identity), 'home_win': hp, 'away_win': ap,
            'provider_home_team_id': str(h['idTeam']), 'provider_away_team_id': str(h['idOpp']),
            'season': h['slugSeason'], 'season_type': h['typeSeason'],
            'date_precision': 'DAY', 'odds_observed_at': None, 'odds_line_type': 'UNDOCUMENTED',
            'odds_provider': 'sbr_archive_via_guydotan', 'source_file': str(ARCHIVE / 'nba_adv_complete.csv')})
    games = canonical_games(rows, 'basketball')
    if len(games) != len(rows):
        raise ValueError('Duplicate fixture identities across provider IDs')
    games.attrs['data_quality'] = {'source_team_rows': len(raw), 'paired_games': len(games),
        'excluded': excluded, 'scope': 'NBA_ARCHIVE_RESEARCH_ONLY',
        'odds_observation_verified': False, 'quote_timestamps_synthesized': False}
    return games


def main():
    manifest = json.loads((ARCHIVE / 'manifest.json').read_text())
    for capture in manifest['captures']:
        if hashlib.sha256((ARCHIVE / capture['file']).read_bytes()).hexdigest() != capture['sha256']:
            raise ValueError('Archive checksum mismatch')
    games = normalize_archive(pd.read_csv(ARCHIVE / 'nba_adv_complete.csv'))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = MODEL_DIR / 'research/nba_archive' / run_id
    print(json.dumps({'research_run': run_id, 'games': len(games), 'quality': games.attrs['data_quality']}), flush=True)
    # Research-only inputs: native archive prices, NOT the verified snapshot loader.
    with patch.object(train_sports, 'load_games', return_value=games), \
            patch.object(train_sports, 'attach_moneylines', side_effect=lambda frame, sport: frame.copy()), \
            threadpool_limits(limits=2):
        report = train_sports.train_sport('basketball', directory)
    assert report['status'] == 'candidate', report
    report.update(status='research_candidate', research_only=True, active=False,
        odds_observation_verified=False, odds_line_type='UNDOCUMENTED',
        source_manifest=str(ARCHIVE / 'manifest.json'),
        limitation='Quote time, opening/closing basis and bookmaker are undocumented. Retrospective archive experiment; not a verified point-in-time betting backtest.')
    (directory / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    model = joblib.load(directory / 'model.pkl')
    assert model.history_model is not None and model.market_model is not None
    frame = pd.read_parquet(directory / 'dataset.parquet')
    assert frame.odds_observed_at.isna().all() and frame.league.eq('basketball_nba').all()
    X = build_features(frame, 'basketball')
    splits = chronological_split(frame.date)
    test = splits['test']
    y = frame.result.map({'away_win': 0, 'home_win': 1}).to_numpy()
    missing = X.iloc[test].copy()
    missing['odds_missing'] = 1.
    with threadpool_limits(limits=2):
        history_test = probability_metrics(y[test], model.predict_proba(missing), report['classes'])
        p = model.predict_proba(X.iloc[test])
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    assert not any(report['features'][i] in {'isWin', 'home_score', 'away_score'} for i in range(len(report['features'])))
    coverage = {name: int(X.iloc[index].odds_missing.eq(0).sum()) for name,index in splits.items()}
    assert all(value >= 30 for value in coverage.values())
    for filename,key in [('model.pkl', 'model_sha256'), ('dataset.parquet', 'dataset_sha256')]:
        assert hashlib.sha256((directory / filename).read_bytes()).hexdigest() == report[key]
    evidence = {**report, 'history_only_same_test': history_test, 'odds_coverage_by_partition': coverage,
        'research_run': run_id, 'source_date_start': frame.date.min().isoformat(),
        'source_date_end': frame.date.max().isoformat(),
        'verification': {'saved_model_reloaded': True, 'probability_rows_sum_to_one': True,
            'source_and_artifact_checksums': True, 'quote_timestamps_remain_null': True}}
    target = ROOT / 'stages/03-build/output/nba-archive-training-20261015.json'
    target.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({key:evidence[key] for key in ['directory','research_run','completed_games','odds_complete',
        'odds_coverage_by_partition','test','market_comparison','history_only_same_test','data_quality','limitation']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
