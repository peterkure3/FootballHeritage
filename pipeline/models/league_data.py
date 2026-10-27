"""Competition-scoped, reviewed football histories for independent league models."""
import json
from pathlib import Path

import pandas as pd

from config import RAW_DATA_DIR, HISTORICAL_CSV_DIR, FOOTBALL_DATA_ORG_DIR
from etl.fetch_football_form import normalize_result
from football_competitions import LEAGUES
from grid_team_aliases import TEAM_ALIASES
from models.data import canonical_matches, historical_frames, team_key

ARCHIVE_CODES = {'E0': 'PL', 'E1': 'ELC', 'SP1': 'PD', 'D1': 'BL1', 'I1': 'SA',
                 'F1': 'FL1', 'P1': 'PPL', 'N1': 'DED', 'BRA': 'BSA',
                 'Premier_League': 'PL', 'La_Liga': 'PD', 'Serie_A': 'SA', 'Ligue_1': 'FL1'}
COMPETITION_CODES = {name: code for code, name, *_ in LEAGUES}
COMPETITION_CODES.update({code: code for code, *_ in LEAGUES})
COMPETITION_CODES.update(ARCHIVE_CODES)


def identity_aliases(path: Path | None = None) -> dict[str, str]:
    groups = json.loads((path or Path(__file__).parent/'league_identities.json').read_text(encoding='utf-8'))
    aliases = {team_key(variant): team_key(canonical)
               for canonical, variants in groups.items() for variant in [canonical, *variants]}
    for reviewed in TEAM_ALIASES.values():
        for source, official in reviewed.items():
            aliases[team_key(source)] = aliases.get(team_key(official), team_key(official))
    return aliases


def identity(name: str, aliases: dict[str, str]) -> str:
    return aliases.get(team_key(name), team_key(name))


def openfootball_portugal(payload: dict) -> pd.DataFrame:
    if payload.get('name') != 'Portuguese Primeira Liga 2022/23':
        raise ValueError('Unexpected Portuguese season')
    names = {'SL Benfica':'Sport Lisboa e Benfica', 'GD Estoril':'GD Estoril Praia',
             'Sporting Braga':'Sporting Clube de Braga', 'Vitória Guimarães':'Vitória SC',
             'FC Vizela':'Vizela', 'Portimonense SC':'Portimonense', 'Paços de Ferreira':'Pacos Ferreira', 'GD Chaves':'Chaves'}
    rows = []
    for match in payload['matches']:
        score = match.get('score', {}).get('ft', [])
        if len(score) != 2 or any(isinstance(value,bool) or not isinstance(value,int) or value < 0 for value in score):
            raise ValueError('Invalid regulation league score')
        rows.append({'date':match['date'],'home_team':names.get(match['team1'],match['team1']),
            'away_team':names.get(match['team2'],match['team2']), 'home_score':score[0], 'away_score':score[1],
            'competition':'PPL','status':'FINISHED','data_source':'openfootball:2022-23:date-only'})
    return pd.DataFrame(rows)


def load_histories(root: Path = RAW_DATA_DIR, aliases: dict | None = None) -> dict[str, pd.DataFrame]:
    frames = historical_frames(HISTORICAL_CSV_DIR)
    reviewed = root/'ucl_history_20261020/repaired_dataset.parquet'
    if reviewed.exists():
        frames.append(pd.read_parquet(reviewed))
    now = pd.Timestamp.now(tz='UTC')
    for manifest in sorted((root/'league_training').glob('*/manifest.json')):
        report = json.loads(manifest.read_text(encoding='utf-8'))
        for source in report['sources']:
            if source['status'] != 'collected':
                continue
            path = manifest.parent/source['filename']
            import hashlib
            if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
                raise ValueError('Historical capture checksum mismatch')
            if path.suffix == '.csv':
                frame = pd.read_csv(path, low_memory=False)
                if path.name == 'BRA.csv':
                    frame = frame.rename(columns={'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR'})
                frame = frame.copy()
                frame['competition'] = ARCHIVE_CODES[path.stem.split('_')[0]]
                frame['data_source'] = 'football-data.co.uk:league-training'
                frames.append(frame)
            else:
                payload = json.loads(path.read_text(encoding='utf-8'))
                if source.get('format') == 'openfootball_json':
                    frames.append(openfootball_portugal(payload))
                    continue
                rows = [row for match in payload['matches'] if (row := normalize_result(match, now))]
                if rows:
                    frames.append(pd.DataFrame(rows))
    # Full official seasons include opponents absent from the older target-club extract.
    for path in sorted((root/'ucl_history_20261020').glob('official_CL_*.json')):
        rows = [row for match in json.loads(path.read_text(encoding='utf-8'))['matches']
                if (row := normalize_result(match, now))]
        if rows:
            frames.append(pd.DataFrame(rows))
    for code, *_ in LEAGUES:
        paths = sorted(FOOTBALL_DATA_ORG_DIR.glob(f'matches_{code}_*.json'))
        for path in paths:
            rows = [row for match in json.loads(path.read_text(encoding='utf-8')).get('matches', [])
                    if (row := normalize_result(match, now))]
            if rows:
                frames.append(pd.DataFrame(rows))
    aliases = aliases if aliases is not None else identity_aliases()
    by_code = {code: [] for code, *_ in LEAGUES}
    columns = {'Date','date','home_team','away_team','HomeTeam','AwayTeam','home_score','away_score',
               'FTHG','FTAG','result','ftr','FTR','status','data_source','competition','provider_match_id','source_url'}
    for raw in frames:
        frame = raw[[column for column in raw.columns if column in columns]].copy()
        frame['competition'] = frame.competition.map(COMPETITION_CODES)
        for side in ['home', 'away']:
            column = side + '_team'
            if column not in frame:
                frame[column] = frame['HomeTeam' if side == 'home' else 'AwayTeam']
            frame[column] = frame[column].map(lambda value: identity(value, aliases))
            frame = frame.drop(columns=['HomeTeam' if side == 'home' else 'AwayTeam'], errors='ignore')
        for code, group in frame.groupby('competition'):
            by_code[code].append(group)
    result = {}
    for code, groups in by_code.items():
        if groups:
            frame = canonical_matches(groups)
            result[code] = frame[frame.result.notna() & frame.date.lt(now.normalize())].reset_index(drop=True)
    return result
