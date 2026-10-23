"""Inspect public client assets and fixture provenance without printing credentials."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from sqlalchemy import text

from api.db import get_db_connection
from config import RAW_DATA_DIR, FOOTBALL_DATA_ORG_DIR


def main():
    import sys
    if '--offline-details' in sys.argv:
        root = RAW_DATA_DIR / 'sportsbooks/discovery_20261010T115525Z'
        for name, needles in {
            'betpawa_app': ['sportsbook:{', 'eventsKeysPerQuery', 'endpoint:o.v.sportsbook.proto.getEventsByQueriesV4', '/events/list', 'getEventList'],
            'fortebet_app': ['getEventDetail(', '/offer/prematch', '/offer/sports', '/offer/event_list', '/offer/event_detail'],
            'ababet_client': ['function update_events', 'function update_bets', 'function get_events'],
        }.items():
            body = (root / (name + '.js')).read_text(encoding='utf-8')
            for needle in needles:
                position = body.find(needle)
                if position >= 0:
                    print(name, needle, body[max(0, position - 500):position + 900])
        with get_db_connection().connect() as conn:
            print('database_timezone', conn.execute(text('SHOW timezone')).scalar())
            print('timestamp_types', conn.execute(text("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_name IN ('matches','odds','predictions') AND column_name IN ('date','updated_at','created_at')")).fetchall())
        body = (root / 'fortebet_app.js').read_text(encoding='utf-8')
        print('forte_routes', sorted(set(re.findall(r'webapiRoute\+"([^"\s]+)"', body))))
        for needle in ['OFFER_INIT_URL=', 'OFFER_TREE_URL=', 'getOffer(', 'initOffer(', 'OFFER_UPDATE_URL=']:
            p = body.find(needle)
            if p >= 0:
                print(needle, body[max(0,p-50):p+600])
        body = (root / 'betpawa_app.js').read_text(encoding='utf-8')
        for needle in ['queries:[', 'queries:e', 'queries:t', 'categoryId:', 'getCategoryByIdV4']:
            p = body.find(needle)
            if p >= 0:
                print(needle, body[max(0,p-180):p+500])
        return
    root = RAW_DATA_DIR / 'sportsbooks' / ('discovery_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir()
    urls = {
        'betpawa_env': 'https://www.betpawa.ug/env.js?v=2.242.59',
        'betpawa_app': 'https://www.betpawa.ug/_next/static/chunks/pages/_app-4a5ff3696349f32b.js',
        'fortebet_app': 'https://www.fortebet.ug/main.f42fb91af5a9385b.js',
        'ababet_client': 'https://ababet.ug/js/custom_g.js?1002',
        'ababet_markets': 'https://ababet.ug/js/custom_m.js',
    }
    results = {}
    for name, url in urls.items():
        try:
            response = requests.get(url, timeout=(5, 20))
            (root / (name + '.js')).write_bytes(response.content)
            body = response.text
            paths = sorted(set(re.findall(r'["\']((?:https://|/)[^"\'\s<>]{3,200})["\']', body)))
            paths = [p for p in paths if re.search(r'api|event|sport|match|betting|fixture|result', p, re.I)
                     and not re.search(r'key|token|password|secret', p, re.I)]
            results[name] = {'http_status': response.status_code, 'bytes': len(response.content), 'paths': paths[:60]}
        except requests.RequestException as exc:
            results[name] = {'error_type': type(exc).__name__}
    with get_db_connection().connect() as conn:
        fixtures = conn.execute(text("SELECT match_id,competition,date,home_team,away_team,status,result,data_source FROM matches WHERE date::date = '2026-10-10' AND competition ILIKE '%premier%' ORDER BY date")).mappings().all()
        results['database_fixtures'] = [dict(row) for row in fixtures]
    source_fixtures = []
    for path in sorted(FOOTBALL_DATA_ORG_DIR.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for row in data.get('matches', []):
            if str(row.get('utcDate', '')).startswith('2026-10-10'):
                source_fixtures.append({'file': path.name, 'id': row['id'], 'utcDate': row['utcDate'],
                    'home': row['homeTeam']['name'], 'away': row['awayTeam']['name'],
                    'status': row.get('status'), 'score': row.get('score')})
    results['raw_source_fixtures'] = source_fixtures[-24:]
    (root / 'report.json').write_text(json.dumps(results, default=str, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(root), **results}, default=str, indent=2), flush=True)


if __name__ == '__main__':
    main()
