"""Verified NFL historical datasets and source-keyed offline aggregate caching."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from models.gridiron_sources import normalize_nfl, summarize_pbp, NFL_RENAMES
from models.gridiron_efficiency import build_efficiency_features


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_sources(capture):
    manifest = json.loads((capture/'manifest.json').read_text())
    hashes = {}
    for path in [capture/'nfl_games.csv', *sorted(capture.glob('nfl_pbp_*.parquet'))]:
        expected = manifest['captures'][path.name]['sha256']
        if sha(path) != expected:
            raise ValueError(f'NFL source checksum mismatch: {path.name}')
        hashes[path.name] = expected
    return hashes


def cached_pbp(capture, cache, source_hashes, force_rebuild=False):
    started = perf_counter(); cache.mkdir(parents=True, exist_ok=True)
    path = cache/'team_games.parquet'; receipt = cache/'manifest.json'
    hashes = {name: digest for name, digest in source_hashes.items() if name.startswith('nfl_pbp_')}
    if not hashes:
        raise ValueError('No verified play-by-play inputs')
    if not force_rebuild and path.exists() and receipt.exists():
        metadata = json.loads(receipt.read_text())
        if metadata['raw_sha256'] == hashes:
            if sha(path) != metadata['aggregate_sha256']:
                raise ValueError('NFL aggregate cache checksum mismatch')
            stats = pd.read_parquet(path).astype(
                {name: object for name in ['game_id', 'posteam', 'defteam', 'source_file']})
            return stats, {'cache_hit': True, 'seconds': perf_counter()-started}
    stats = summarize_pbp(capture)
    if stats.empty:
        raise ValueError('Empty NFL play-by-play aggregates')
    stats = stats.astype({name: object for name in ['game_id', 'posteam', 'defteam', 'source_file']})
    stats.to_parquet(path, index=False)
    receipt.write_text(json.dumps({'raw_sha256': hashes, 'aggregate_sha256': sha(path)}, indent=2))
    return stats, {'cache_hit': False, 'seconds': perf_counter()-started}


def prepare(capture, output):
    if output.exists() and any(path.name != 'cache' for path in output.iterdir()):
        raise FileExistsError('NFL prepared artifacts already exist; use a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter(); hashes = verified_sources(capture)
    raw = pd.read_csv(capture/'nfl_games.csv', low_memory=False)
    games = normalize_nfl(raw, str((capture/'nfl_games.csv').resolve()))
    seasons = sorted(int(name.removeprefix('nfl_pbp_').removesuffix('.parquet'))
                     for name in hashes if name.startswith('nfl_pbp_'))
    games = games[games.season.isin(seasons)].reset_index(drop=True)
    games['week'] = games.provider_event_id.map(raw.set_index('game_id').week).astype(int)
    games[['home_win', 'away_win']] = np.nan
    stats, cold = cached_pbp(capture, output/'cache', hashes, force_rebuild=True)
    warm_stats, warm = cached_pbp(capture, output/'cache', hashes)
    pd.testing.assert_frame_equal(stats, warm_stats)
    keys = {(str(r['game_id']), NFL_RENAMES.get(r['posteam'], r['posteam'])) for r in stats.to_dict('records')}
    games['pbp_complete'] = [all((str(r['provider_event_id']), r[f'provider_{side}_team_id']) in keys
                                   for side in ['home', 'away']) for r in games.to_dict('records')]
    build_start = perf_counter(); features = build_efficiency_features(games, stats)
    build_seconds = perf_counter()-build_start
    if not np.isfinite(features.to_numpy()).all():
        raise ValueError('Nonfinite NFL historical features')
    games.to_parquet(output/'dataset.parquet', index=False)
    features.to_parquet(output/'features.parquet', index=False)
    report = {'created_at': pd.Timestamp.now(tz='UTC').isoformat(), 'capture': str(capture),
        'source_sha256': hashes, 'games': len(games), 'ties': int(games.result.eq('draw').sum()),
        'seasons': seasons, 'by_season': {str(season): {'games': len(block),
            'pbp_complete': int(block.pbp_complete.sum()), 'ties': int(block.result.eq('draw').sum()),
            'start': block.date.min().isoformat(), 'end': block.date.max().isoformat()}
            for season, block in games.groupby('season')},
        'dataset_sha256': sha(output/'dataset.parquet'), 'features_sha256': sha(output/'features.parquet'),
        'cache_benchmark': {'cold': cold, 'warm': warm, 'speedup': cold['seconds']/warm['seconds'],
                            'aggregate_frames_equal': True},
        'feature_build_seconds': build_seconds, 'total_seconds': perf_counter()-started,
        'availability_policy': 'ASSUMED_TWO_UTC_DAYS; historical observation/revision receipts unavailable',
        'odds_used': False, 'production_changed': False}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: report[key] for key in ['games', 'ties', 'by_season', 'cache_benchmark', 'feature_build_seconds']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); prepare(args.capture, args.output)
