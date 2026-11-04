"""Collect the accessible 2025 NFL games corpus and cross-check existing scores."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from dotenv import dotenv_values
import pandas as pd
import requests
from models.gridiron_sources import NFL_RENAMES

key = dotenv_values(ROOT / 'pipeline/.env')['BALLDONTLIE_API_KEY']
output = ROOT / 'pipeline/data/raw/balldontlie' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
output.mkdir(parents=True, exist_ok=False)
url = 'https://api.balldontlie.io/nfl/v1/games'
games, captures, seen_cursors = {}, [], set()
cursor = None
for page in range(10):
    params = {'seasons[]': 2025, 'per_page': 100}
    if cursor is not None:
        params['cursor'] = cursor
    response = requests.get(url, params=params, headers={'Authorization': key}, timeout=40)
    if response.status_code != 200:
        raise SystemExit(f'NFL games HTTP {response.status_code}; partial captures retained')
    path = output / f'nfl-2025-page-{page+1}.json'
    path.write_text(response.text.replace(key, '[REDACTED]'), encoding='utf-8')
    payload = response.json()
    rows = payload['data']
    for game in rows:
        assert game['season'] == 2025, 'Provider season filter mismatch'
        assert str(game['id']) not in games, 'Duplicate paginated game ID'
        games[str(game['id'])] = game
    captures.append({'file': path.name, 'url': url, 'params': params, 'records': len(rows),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    print(json.dumps({'page':page+1, 'records':len(rows), 'total_games':len(games)}), flush=True)
    cursor = payload.get('meta', {}).get('next_cursor')
    if cursor is None or not rows:
        break
    assert cursor not in seen_cursors, 'Pagination cursor repeated'
    seen_cursors.add(cursor)
    time.sleep(13)
else:
    raise SystemExit('Pagination limit reached; do not claim complete season')

frame = pd.DataFrame([{'provider_event_id': str(g['id']), 'season': g['season'], 'week':g['week'],
    'date':g['date'], 'home_team':g['home_team']['full_name'], 'away_team':g['visitor_team']['full_name'],
    'home_abbreviation':g['home_team']['abbreviation'], 'away_abbreviation':g['visitor_team']['abbreviation'],
    'home_score':g['home_team_score'], 'away_score':g['visitor_team_score'],
    'status':g.get('status'), 'status_state':g.get('status_state'), 'postseason':g.get('postseason'),
    'updated_at':g.get('updated_at')} for g in games.values()])
frame.to_csv(output / 'nfl-2025-games.csv', index=False)
(output / 'nfl-2025-games.json').write_text(json.dumps(list(games.values()), indent=2), encoding='utf-8')
reference = pd.read_csv(ROOT / 'pipeline/data/raw/historical/gridiron_sources/20261015/normalized/nfl_games_odds.csv')
reference = reference[reference.season.eq(2025)]
lookup = {(str(pd.Timestamp(r['date']).date()), r['provider_home_team_id'], r['provider_away_team_id']):r
    for r in reference.to_dict('records')}
matched, conflicts, unmatched = 0, [], []
for game in frame.to_dict('records'):
    codes = [NFL_RENAMES.get(game[f'{side}_abbreviation'], game[f'{side}_abbreviation']) for side in ['home','away']]
    identity = (str(pd.Timestamp(game['date']).date()), *codes)
    ref = lookup.get(identity)
    if ref is None:
        unmatched.append(game['provider_event_id'])
    elif (game['home_score'],game['away_score']) != (ref['home_score'],ref['away_score']):
        conflicts.append({'balldontlie_id':game['provider_event_id'], 'nflverse_id':ref['provider_event_id']})
    else:
        matched += 1
manifest = {'provider':'balldontlie', 'season':2025, 'retrieved_at':datetime.now(timezone.utc).isoformat(),
    'capture_dir':str(output.resolve()), 'games':len(frame), 'pagination_complete':True,
    'captures':captures, 'independent_cross_check':{'reference_games':len(reference),
        'matching_results':matched, 'score_conflicts':conflicts, 'unmatched_games':unmatched},
    'odds_collected':False, 'model_retrained':False}
(output / 'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT / 'stages/03-build/output/balldontlie-nfl-20261016.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2),flush=True)
