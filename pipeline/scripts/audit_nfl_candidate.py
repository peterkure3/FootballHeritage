"""Export verified NFL score history and add untuned prior/calibration diagnostics."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models.gridiron_sources import normalize_nfl
from models.nfl_history import sha, verified_sources
from models.nfl_season_validation import load_data, season_splits, CLASSES
from models.validation import probability_metrics


def training_prior(games, year):
    splits, _ = season_splits(games, year)
    development = np.r_[splits['train'], splits['tune']]
    labels = games.iloc[development].result.map({'away_win': 0, 'home_win': 1}).to_numpy(dtype=int)
    if not len(labels):
        raise ValueError('No non-tied NFL training labels for prior baseline')
    return np.bincount(labels, minlength=2)/len(labels)


def calibration_error(metrics):
    bins = metrics['calibration_bins']['home_win']
    return sum(row['count']*abs(row['mean_probability']-row['observed_frequency']) for row in bins)/metrics['samples']


def run(capture, candidate):
    selection = json.loads((candidate/'selection.json').read_text())
    games, _, data_report = load_data(Path(selection['data_directory']))
    hashes = verified_sources(capture)
    if hashes != data_report['source_sha256']:
        raise ValueError('NFL audit capture differs from prepared dataset')
    raw = pd.read_csv(capture/'nfl_games.csv', low_memory=False)
    full = normalize_nfl(raw, str((capture/'nfl_games.csv').resolve()), now=data_report['created_at'])
    full['week'] = full.provider_event_id.map(raw.set_index('game_id').week).astype(int)
    if not set(games.provider_event_id).issubset(set(full.provider_event_id)):
        raise ValueError('Prepared game missing from full score history')
    test = np.flatnonzero(games.season.eq(2026) & games.result.ne('draw'))
    labels = games.iloc[test].result.map({'away_win': 0, 'home_win': 1}).to_numpy(dtype=int)
    prior = training_prior(games, 2026)
    naive = probability_metrics(labels, np.tile(prior, (len(test), 1)), CLASSES)
    validation = json.loads((candidate/'reference_validation/report.json').read_text())
    development = pd.read_csv(candidate/'development_predictions.csv')
    prior_rows = []
    for year in range(2020, 2026):
        target = development[development.season.eq(year) & development.model.eq('history')]
        values = training_prior(games, year)
        prior_rows.extend([{'actual': int(label), 'away_win': values[0], 'home_win': values[1]} for label in target.actual])
    prior_frame = pd.DataFrame(prior_rows)
    output = candidate/'audit'; output.mkdir(exist_ok=False)
    columns = ['provider_event_id', 'date', 'season', 'week', 'season_type', 'home_team', 'away_team',
               'home_score', 'away_score', 'neutral_site', 'result', 'result_available_at', 'result_availability_precision']
    full[columns].to_csv(output/'nfl_score_history.csv', index=False)
    full[columns].to_parquet(output/'nfl_score_history.parquet', index=False)
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'all_score_games': len(full),
        'score_seasons': [int(full.season.min()), int(full.season.max())],
        'play_by_play_seasons': data_report['seasons'], 'model_games': len(games),
        'games_with_complete_pbp': int(games.pbp_complete.sum()), 'model_ties_retained': int(games.result.eq('draw').sum()),
        'raw_play_rows': {path.name: len(pd.read_parquet(path, columns=['game_id'])) for path in sorted(capture.glob('nfl_pbp_*.parquet'))},
        'raw_source_bytes': sum((capture/name).stat().st_size for name in hashes),
        'cached_aggregate_bytes': (Path(selection['data_directory'])/'cache/team_games.parquet').stat().st_size,
        'development_prior_baseline': probability_metrics(prior_frame.actual.to_numpy(), prior_frame[CLASSES].to_numpy(), CLASSES),
        'heldout_prior_baseline': naive, 'heldout_prior_probabilities': dict(zip(CLASSES, prior.tolist())),
        'home_win_calibration_error_10_bins': {name: calibration_error(value) for name, value in
            {**validation['metrics'], 'prior': naive}.items()},
        'csv_sha256': sha(output/'nfl_score_history.csv'), 'parquet_sha256': sha(output/'nfl_score_history.parquet'),
        'limitations': ['Prior is fitted on train+tune only; calibration/test labels never set its probabilities.',
            'All score-history availability fields are assumptions, not archived observation receipts.',
            'Calibration-bin error is diagnostic, not a selection criterion.'], 'production_changed': False}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'all_score_games': len(full), 'score_seasons': report['score_seasons'],
        'total_play_rows': sum(report['raw_play_rows'].values()), 'heldout_prior_baseline': {key: naive[key]
        for key in ['samples', 'accuracy', 'log_loss', 'brier_score']},
        'calibration_error': report['home_win_calibration_error_10_bins']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args(); run(args.capture, args.candidate)
