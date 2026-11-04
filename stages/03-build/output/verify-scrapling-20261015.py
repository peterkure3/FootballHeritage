"""Verify this collection's quotes against the stored evidence and database."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from api.db import get_db_connection
from etl.utils import save_json
from api.prediction_dashboard import fixtures
from models.data import team_key
from scripts.sync_bookmaker_grid import CL_TEAM_ALIASES


def main() -> None:
    capture = ROOT / 'pipeline/data/raw/sportsbooks/scrapling-20261015-01'
    source = json.loads((capture / 'source_report.json').read_bytes())
    grid = json.loads(sorted(capture.glob('grid_sync_*.json'))[0].read_bytes())
    epl = json.loads((capture / 'epl_sync.json').read_bytes())
    records = {row['snapshot_id']: row for row in map(json.loads,
        (capture / 'odds_snapshots.jsonl').read_text(encoding='utf-8').splitlines())}
    evidence = []
    with get_db_connection().connect() as connection:
        for item in grid['matches'] + epl['inserted']:
            row = records[item['snapshot_id']]
            region = row.get('region')
            book = row['bookmaker'] + (':' + region if region else '')
            observed = pd.Timestamp(row['source_updated_at'] if row['bookmaker'] == 'bookmaker'
                                    else row['observed_at']).tz_convert('UTC').tz_localize(None)
            prices = {offer['selection']: float(offer['odds_decimal']) for offer in row['outcomes']}
            stored = connection.execute(text('''SELECT o.home_win,o.draw,o.away_win,m.home_team,m.away_team
                FROM odds o JOIN matches m ON m.match_id=o.match_id
                WHERE o.match_id=:match AND o.bookmaker=:book AND o.updated_at=:observed'''),
                {'match': item['match_id'], 'book': book, 'observed': observed}).mappings().all()
            assert len(stored) == 1, (item, len(stored))
            if row['bookmaker'] == 'bookmaker':
                aliases = {name.casefold(): canonical for name, canonical in CL_TEAM_ALIASES.items()}
                raw_home = team_key(aliases.get(row['home_team'].casefold(), row['home_team']))
                raw_away = team_key(aliases.get(row['away_team'].casefold(), row['away_team']))
                home, away = team_key(stored[0]['home_team']), team_key(stored[0]['away_team'])
                assert {raw_home, raw_away} == {home, away}
                if raw_home == away:
                    prices['HOME'], prices['AWAY'] = prices['AWAY'], prices['HOME']
            assert all(float(stored[0][field]) == prices[key]
                       for field, key in [('home_win', 'HOME'), ('draw', 'DRAW'), ('away_win', 'AWAY')]), (item, dict(stored[0]), prices)
            evidence.append({'match_id': item['match_id'], 'bookmaker': book,
                             'snapshot_id': item['snapshot_id']})
    manifest = epl['training_import']
    parquet = Path(manifest['odds_file'])
    assert hashlib.sha256(parquet.read_bytes()).hexdigest() == manifest['parquet_sha256']
    assert len(pd.read_parquet(parquet)) == manifest['snapshots']
    dashboard = fixtures(1, 50)
    quotes = [quote for fixture in dashboard['items'] for quote in fixture['market']['quotes'] if quote['fresh']]
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'transport': source['transport'],
              'configured_sources': len(source['direct_sources']), 'captured_snapshots': len(records),
              'snapshots_by_bookmaker': {key: value for key, value in source['snapshots_by_bookmaker'].items() if value},
              'source_status_counts': dict(Counter(row['status'] for row in source['direct_sources'])),
              'database_quotes_verified': len(evidence),
              'database_fixtures_updated': len({row['match_id'] for row in evidence}),
              'training_snapshots': manifest['snapshots'], 'training_checksum_verified': True,
              'dashboard_fixtures': len(dashboard['items']), 'dashboard_fresh_quotes': len(quotes),
              'evidence': evidence, 'capture': str(capture), 'active_model_changed': False}
    save_json(report, ROOT / 'stages/03-build/output/scrapling-update-20261015.json')
    print(json.dumps({key: value for key, value in report.items() if key != 'evidence'}, indent=2))


if __name__ == '__main__':
    main()
