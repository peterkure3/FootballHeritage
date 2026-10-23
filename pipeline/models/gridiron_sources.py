"""Validated native-ID adapters for nflverse and CollegeFootballData archives."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from etl.fetch_americanfootball_history import canonical_team_names
from models.sport_data import canonical_games

NFL_NAMES = dict(zip(
    'ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split(),
    ['Arizona Cardinals', 'Atlanta Falcons', 'Baltimore Ravens', 'Buffalo Bills', 'Carolina Panthers',
     'Chicago Bears', 'Cincinnati Bengals', 'Cleveland Browns', 'Dallas Cowboys', 'Denver Broncos',
     'Detroit Lions', 'Green Bay Packers', 'Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars',
     'Kansas City Chiefs', 'Los Angeles Rams', 'Los Angeles Chargers', 'Las Vegas Raiders', 'Miami Dolphins',
     'Minnesota Vikings', 'New England Patriots', 'New Orleans Saints', 'New York Giants', 'New York Jets',
     'Philadelphia Eagles', 'Pittsburgh Steelers', 'Seattle Seahawks', 'San Francisco 49ers',
     'Tampa Bay Buccaneers', 'Tennessee Titans', 'Washington Commanders']))
NFL_RENAMES = {'STL': 'LA', 'LAR': 'LA', 'SD': 'LAC', 'OAK': 'LV', 'WSH': 'WAS'}


def american_decimal(value) -> float:
    if value is None or pd.isna(value):
        return np.nan
    price = float(value)
    if not np.isfinite(price) or abs(price) < 100:
        raise ValueError('Invalid American odds')
    return 1 + (price / 100 if price > 0 else 100 / abs(price))


def valid_score(value) -> bool:
    return value is not None and pd.notna(value) and np.isfinite(value) and value >= 0 and value == int(value)


def finalize(rows: list[dict], sport: str, quality: dict) -> pd.DataFrame:
    if not rows:
        raise ValueError(f'No completed {sport} games in scope')
    canonical_team_names(rows)
    frame = canonical_games(rows, sport)
    if len(frame) != len(rows):
        raise ValueError('Unexpected duplicated native game IDs')
    frame.attrs['data_quality'] = quality | {'odds_observation_verified': False}
    return frame


def normalize_nfl(raw: pd.DataFrame, source: str, now=None) -> pd.DataFrame:
    now = pd.Timestamp(now or pd.Timestamp.now(tz='UTC'))
    rows, invalid_prices, excluded = [], 0, 0
    if raw.game_id.duplicated().any():
        raise ValueError('Duplicate nflverse game ID')
    for game in raw.to_dict('records'):
        if game['game_type'] not in {'REG', 'WC', 'DIV', 'CON', 'SB'}:
            continue
        if not all(valid_score(game.get(key)) for key in ['home_score', 'away_score']):
            excluded += 1
            continue
        if pd.isna(game.get('gametime')):
            excluded += 1
            continue
        # nflverse scheduled game times are US Eastern, including DST.
        date = pd.Timestamp(f"{game['gameday']} {game['gametime']}").tz_localize('America/New_York').tz_convert('UTC')
        available = date.normalize() + pd.Timedelta(days=2)
        if date >= now or available > now:
            excluded += 1
            continue
        codes = {side: NFL_RENAMES.get(game[f'{side}_team'], game[f'{side}_team']) for side in ['home', 'away']}
        if any(code not in NFL_NAMES for code in codes.values()):
            raise ValueError('Unknown NFL franchise identity')
        try:
            home_price, away_price = [american_decimal(game.get(f'{side}_moneyline')) for side in ['home', 'away']]
        except ValueError:
            invalid_prices += 1
            home_price = away_price = np.nan
        rows.append({'date': date, 'result_available_at': available, 'league': 'americanfootball_nfl',
            'home_team': NFL_NAMES[codes['home']], 'away_team': NFL_NAMES[codes['away']],
            'home_score': game['home_score'], 'away_score': game['away_score'], 'completed': True,
            'provider_event_id': game['game_id'], 'provider_home_team_id': codes['home'],
            'provider_away_team_id': codes['away'], 'provider': 'nflverse', 'season': game['season'],
            'season_type': game['game_type'], 'neutral_site': game.get('location') == 'Neutral',
            'home_win': home_price, 'away_win': away_price, 'spread_line': game.get('spread_line'),
            'total_line': game.get('total_line'), 'odds_observed_at': None, 'odds_line_type': 'ARCHIVE_UNTIMESTAMPED',
            'pfr_reference_id': game.get('pfr'), 'source_file': source, 'date_precision': 'TIMESTAMP',
            'result_availability_precision': 'CONSERVATIVE_TWO_DAYS'})
    return finalize(rows, 'nfl', {'excluded_unfinished_or_unavailable': excluded, 'invalid_price_pairs': invalid_prices,
        'franchise_renames': NFL_RENAMES, 'source': 'nflverse'})


def normalize_cfbd(games: list[dict], lines: list[dict], source: str, now=None) -> tuple[pd.DataFrame, list[dict]]:
    now = pd.Timestamp(now or pd.Timestamp.now(tz='UTC'))
    lines_by_id = {}
    for item in lines:
        identity = str(item['id'])
        if identity in lines_by_id:
            raise ValueError('Duplicate CFBD betting game ID')
        lines_by_id[identity] = item
    rows, quotes, seen = [], [], set()
    mismatches, invalid_prices = 0, 0
    for game in games:
        identity = str(game['id'])
        if identity in seen:
            raise ValueError('Duplicate CFBD game ID')
        seen.add(identity)
        if game.get('completed') is not True or game.get('seasonType') not in {'regular', 'postseason'}:
            continue
        if 'fbs' not in {game.get('homeClassification'), game.get('awayClassification')}:
            continue
        date = pd.to_datetime(game['startDate'], utc=True, errors='coerce')
        if pd.isna(date) or date >= now or not all(valid_score(game.get(f'{side}Points')) for side in ['home', 'away']):
            continue
        available = date.normalize() + pd.Timedelta(days=2)
        if available > now:
            continue
        if game['homePoints'] == game['awayPoints']:
            raise ValueError('Unexpected tied college final')
        item = lines_by_id.get(identity)
        pairs, providers, spreads, totals = [], set(), [], []
        if item:
            matched = all(item.get(f'{side}Team') == game[f'{side}Team'] for side in ['home', 'away'])
            matched &= pd.to_datetime(item.get('startDate'), utc=True) == date
            for side in ['home', 'away']:
                if item.get(f'{side}TeamId') is not None:
                    matched &= item[f'{side}TeamId'] == game[f'{side}Id']
                if item.get(f'{side}Score') is not None:
                    matched &= item[f'{side}Score'] == game[f'{side}Points']
            if not matched:
                mismatches += 1
            else:
                for line in item.get('lines', []):
                    provider = str(line['provider'])
                    if provider in providers:
                        raise ValueError('Duplicate provider quote for a CFBD game')
                    providers.add(provider)
                    try:
                        hp, ap = american_decimal(line.get('homeMoneyline')), american_decimal(line.get('awayMoneyline'))
                    except (ValueError, TypeError):
                        invalid_prices += 1
                        continue
                    if np.isfinite([hp, ap]).all():
                        pairs.append([hp, ap])
                    if line.get('spread') is not None:
                        spreads.append(float(line['spread']))
                    if line.get('overUnder') is not None:
                        totals.append(float(line['overUnder']))
                    quotes.append({'game_id': identity, 'provider': provider, 'season': game['season'],
                        'kickoff': date.isoformat(), 'home_team': game['homeTeam'], 'away_team': game['awayTeam'],
                        'home_decimal': hp, 'away_decimal': ap, 'home_american': line.get('homeMoneyline'),
                        'away_american': line.get('awayMoneyline'), 'spread': line.get('spread'),
                        'spread_open': line.get('spreadOpen'), 'total': line.get('overUnder'),
                        'total_open': line.get('overUnderOpen'), 'odds_observed_at': None})
        hp, ap = np.median(pairs, axis=0) if pairs else (np.nan, np.nan)
        rows.append({'date': date, 'result_available_at': available, 'league': 'americanfootball_ncaaf',
            'home_team': game['homeTeam'], 'away_team': game['awayTeam'],
            'provider_home_team_id': str(game['homeId']), 'provider_away_team_id': str(game['awayId']),
            'home_score': game['homePoints'], 'away_score': game['awayPoints'], 'completed': True,
            'provider_event_id': identity, 'provider': 'cfbd', 'season': game['season'], 'season_type': game['seasonType'],
            'neutral_site': game.get('neutralSite') is True, 'home_win': hp, 'away_win': ap,
            'odds_provider': 'MEDIAN_AVAILABLE_BOOKS', 'odds_books': len(pairs),
            'spread_line': float(np.median(spreads)) if spreads else None,
            'total_line': float(np.median(totals)) if totals else None,
            'odds_observed_at': None, 'odds_line_type': 'ARCHIVE_UNTIMESTAMPED', 'source_file': source,
            'date_precision': 'DAY' if game.get('startTimeTBD') is True else 'TIMESTAMP',
            'result_availability_precision': 'CONSERVATIVE_TWO_DAYS'})
    return finalize(rows, 'ncaaf', {'source': 'cfbd', 'odds_identity_mismatches': mismatches,
        'invalid_prices': invalid_prices, 'scope': 'AT_LEAST_ONE_FBS_PARTICIPANT'}), quotes


def load_capture(directory: Path, sports: list[str]) -> tuple[dict, dict]:
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, capture in manifest['captures'].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != capture['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
    frames, exports = {}, {}
    if 'nfl' in sports:
        path = directory / 'nfl_games.csv'
        frames['nfl'] = normalize_nfl(pd.read_csv(path), str(path.resolve()))
    if 'ncaaf' in sports:
        game_files, line_files = sorted(directory.glob('cfbd_games_*.json')), sorted(directory.glob('cfbd_lines_*.json'))
        games = [row for path in game_files for row in json.loads(path.read_text())]
        lines = [row for path in line_files for row in json.loads(path.read_text())]
        frames['ncaaf'], exports['cfbd_quotes'] = normalize_cfbd(games, lines, str(directory.resolve()))
    return frames, exports


def summarize_pbp(directory: Path) -> pd.DataFrame:
    """Retain postgame nflfastR efficiency aggregates as a separately dated corpus."""
    chunks = []
    columns = ['game_id', 'posteam', 'defteam', 'epa', 'yards_gained', 'play_type', 'home_team', 'away_team']
    for path in sorted(directory.glob('nfl_pbp_*.parquet')):
        frame = pd.read_parquet(path, columns=columns)
        frame = frame[frame.play_type.isin(['run', 'pass']) & frame.posteam.notna() & frame.epa.notna()]
        frame['success'] = frame.epa.gt(0)
        grouped = frame.groupby(['game_id', 'posteam', 'defteam']).agg(
            plays=('epa', 'size'), epa_per_play=('epa', 'mean'), success_rate=('success', 'mean'),
            yards_per_play=('yards_gained', 'mean')).reset_index()
        grouped['source_file'] = str(path.resolve())
        chunks.append(grouped)
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
