"""Capture recent regular-season NBA results for research, not production loading."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import pandas as pd
import requests

from config import RAW_DATA_DIR
from etl.nba_public_parsers import team

SEASON_START = '2026-10-20'
SCHEDULE_SOURCE = 'https://www.nba.com/news/key-dates'


def normalize(game: dict, observed: str, raw_ref: str) -> dict | None:
    kickoff = pd.to_datetime(game.get('datetime'), utc=True, errors='coerce')
    captured = pd.Timestamp(observed)
    if (pd.isna(kickoff) or kickoff < pd.Timestamp(SEASON_START, tz='UTC') or kickoff >= captured
            or game.get('season') != 2026 or game.get('postseason') is not False
            or game.get('postponed') or game.get('status') != 'Final'
            or game.get('status_state') != 'final' or game.get('period', 0) < 4):
        return None
    home, away = team(game.get('home_team', {}).get('full_name')), team(game.get('visitor_team', {}).get('full_name'))
    h, a = game.get('home_team_score'), game.get('visitor_team_score')
    if not home or not away or home == away or type(h) is not int or type(a) is not int or min(h, a) < 0 or h == a:
        raise ValueError('Invalid completed NBA fixture')
    for side, expected in [('home', h), ('visitor', a)]:
        quarters = [game.get(f'{side}_q{i}') for i in range(1, 5)]
        if all(type(value) is int for value in quarters):
            overtime = [value for key, value in game.items() if key.startswith(side+'_ot') and value is not None]
            if any(type(value) is not int or value < 0 for value in quarters+overtime) or sum(quarters+overtime) != expected:
                raise ValueError('Quarter totals disagree with final score')
    return {'provider_event_id': str(game['id']), 'date': kickoff.isoformat(), 'league': 'basketball_nba',
            'home_team': home, 'away_team': away, 'home_score': h, 'away_score': a, 'completed': True,
            'result_available_at': captured.isoformat(), 'result_availability_precision': 'CAPTURED_NOW',
            'source_file': raw_ref, 'date_precision': 'TIMESTAMP', 'season': 2026,
            'settlement_rule': 'INCLUDING_OVERTIME'}


def collect(output: Path) -> dict:
    key = os.getenv('BALLDONTLIE_API_KEY')
    if not key:
        raise ValueError('BALLDONTLIE access is not configured')
    output.mkdir(parents=True, exist_ok=False)
    end = datetime.now(timezone.utc).date().isoformat()
    cursor = None; cursors = set(); rows = []; sources = []; ids = set(); exclusions = 0
    for page in range(5):
        params = {'start_date': SEASON_START, 'end_date': end, 'per_page': 100}
        if cursor is not None:
            params['cursor'] = cursor
        response = requests.get('https://api.balldontlie.io/v1/games', params=params,
                                headers={'Authorization': key}, timeout=35)
        observed = datetime.now(timezone.utc).isoformat()
        raw = response.text.replace(key, '[REDACTED]').encode('utf-8')
        path = output/f'page-{page+1}.json'; path.write_bytes(raw)
        sources.append({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'observed_at': observed, 'http_status': response.status_code, 'params': params})
        response.raise_for_status()
        payload = json.loads(raw)
        for game in payload.get('data', []):
            if game['id'] in ids:
                raise ValueError('Duplicate provider game ID')
            ids.add(game['id'])
            row = normalize(game, observed, str(path))
            if row is None:
                exclusions += 1
            else:
                rows.append(row)
        cursor = payload.get('meta', {}).get('next_cursor')
        if cursor is None:
            break
        if cursor in cursors:
            raise ValueError('Repeated pagination cursor')
        cursors.add(cursor); time.sleep(13)
    else:
        raise ValueError('Bounded pagination exceeded')
    data = output/'normalized.jsonl'
    data.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
    report = {'captured_at': datetime.now(timezone.utc).isoformat(), 'source': 'https://api.balldontlie.io/v1/games',
              'sources': sources, 'season_start': SEASON_START, 'schedule_source': SCHEDULE_SOURCE,
              'completed_games': len(rows), 'excluded': exclusions,
              'normalized_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
              'production_changed': False, 'availability_note': 'Captured now; never backdated to game day.',
              'limitations': ['Provider final scores are not independently reconciled against another result source.',
                             'Regular-season classification uses official season start plus provider postseason flag.']}
    (output/'manifest.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({key: report[key] for key in ['completed_games','excluded','captured_at']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=RAW_DATA_DIR/'research/nba_results_20261031')
    args = parser.parse_args(); collect(args.output)
