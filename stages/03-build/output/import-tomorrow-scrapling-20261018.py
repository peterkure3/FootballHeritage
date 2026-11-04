"""Filter the Scrapling capture to Kampala's tomorrow and verify exact DB matches."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from api.db import get_db_connection
from models.football_identity import football_identity_key
from models.import_sportsbook_odds import normalize_snapshots
from scripts.sync_bookmaker_grid import COMPETITIONS, matched_grid_quotes, sync_grid
from scripts.sync_verified_odds import EPL_ALIASES

capture = ROOT / 'pipeline/data/raw/sportsbooks/scrapling-tomorrow-20261018-20261017-01'
source = json.loads((capture / 'source_report.json').read_text(encoding='utf-8'))
assert source['transport'] == 'scrapling'
local = timezone(timedelta(hours=3))
start = datetime(2026, 10, 18, tzinfo=local)
end = start + timedelta(days=1)
raw = [json.loads(line) for line in (capture / 'odds_snapshots.jsonl').read_text(encoding='utf-8').splitlines() if line]
records = [dict(row) for row in raw if start <= datetime.fromisoformat(row['commence_time'].replace('Z', '+00:00')) < end]
normalize_snapshots(records)
engine = get_db_connection()
with engine.connect() as connection:
    fixtures = pd.read_sql(text('''SELECT match_id,date,home_team,away_team,competition FROM matches
        WHERE date >= :start AND date < :end AND result IS NULL
        AND UPPER(COALESCE(status,'')) NOT IN ('LIVE','IN_PLAY','PAUSED','FINISHED','CANCELLED','CANCELED','POSTPONED')'''),
        connection, params={'start': start.astimezone(timezone.utc).replace(tzinfo=None),
                            'end': end.astimezone(timezone.utc).replace(tzinfo=None)})
official = {}
for row in fixtures.to_dict('records'):
    key = (row['competition'], football_identity_key(row['home_team']), football_identity_key(row['away_team']),
           pd.Timestamp(row['date']).tz_localize('UTC').isoformat())
    official.setdefault(key, []).append(row)
for record in records:
    raw_ref = Path(record['raw_capture_ref'])
    record['raw_capture_ref'] = str((capture / raw_ref).resolve()) if not raw_ref.is_absolute() else str(raw_ref)
    assert Path(record['raw_capture_ref']).is_file(), record['raw_capture_ref']
    competition = COMPETITIONS.get(record['competition'], record['competition'])
    if competition == 'Premier League':
        names = [EPL_ALIASES.get(record[f'{side}_team'], record[f'{side}_team']) for side in ['home', 'away']]
        key = (competition, *(football_identity_key(name) for name in names), pd.Timestamp(record['commence_time']).isoformat())
        match = official.get(key, [])
        if len(match) == 1:
            record.update(canonical_home_team=match[0]['home_team'], canonical_away_team=match[0]['away_team'])
destination = capture / 'tomorrow-20261018-EAT'
destination.mkdir(exist_ok=True)
dataset = ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records)
dataset_path = destination / 'odds_snapshots.jsonl'
if dataset_path.exists():
    assert dataset_path.read_text(encoding='utf-8') == dataset, 'Existing tomorrow export differs'
else:
    with dataset_path.open('x', encoding='utf-8') as stream:
        stream.write(dataset)
joined = matched_grid_quotes(fixtures, records)
sync = sync_grid(destination, apply=True)
(destination / 'ingestion.json').write_text(json.dumps(sync, indent=2), encoding='utf-8')
verified = []
stale_provider = []
with engine.connect() as connection:
    for row in joined.to_dict('records'):
        observed = pd.Timestamp(row['source_updated_at'] if row['bookmaker'] == 'bookmaker' else row['observed_at'])
        if not pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24) <= observed <= pd.Timestamp.now(tz='UTC'):
            stale_provider.append(row['snapshot_id'])
            continue
        region = row.get('region')
        book = row['bookmaker'] + (':' + region if isinstance(region, str) and region else '')
        stored = connection.execute(text('''SELECT home_win,draw,away_win FROM odds
            WHERE match_id=:match AND bookmaker=:book AND updated_at=:observed'''),
            {'match': int(row['match_id']), 'book': book, 'observed': observed.tz_convert('UTC').tz_localize(None)}).mappings().all()
        assert len(stored) == 1, (row['snapshot_id'], len(stored))
        assert all(abs(float(stored[0][key]) - float(row[key])) < 1e-9 for key in ['home_win', 'draw', 'away_win'])
        verified.append({'match_id': int(row['match_id']), 'bookmaker': book, 'snapshot_id': row['snapshot_id'],
                         'home_team': row['home_team'], 'away_team': row['away_team'],
                         'kickoff': pd.to_datetime(row['date'], utc=True).isoformat(),
                         'home_win': float(row['home_win']), 'draw': float(row['draw']), 'away_win': float(row['away_win'])})
duplicate_check = sync_grid(destination, apply=True)
assert duplicate_check['inserted'] == 0
summary = {'date': '2026-10-18', 'timezone': 'Africa/Kampala', 'transport': 'scrapling',
    'collected_at': source['completed_at'], 'configured_sources': len(source['direct_sources']),
    'source_statuses': dict(Counter(row['status'] for row in source['direct_sources'])),
    'all_dates_snapshots': len(raw), 'tomorrow_snapshots': len(records),
    'tomorrow_by_bookmaker': dict(Counter(row['bookmaker'] for row in records)),
    'tomorrow_fixture_pairs': len({(row['competition'], row['home_team'], row['away_team'], row['commence_time']) for row in records}),
    'database_inserted': sync['inserted'], 'database_verified': len(verified),
    'database_fixtures': len({row['match_id'] for row in verified}), 'database_by_bookmaker': dict(Counter(row['bookmaker'] for row in verified)),
    'unmatched_snapshots': sync['unmatched_snapshots'], 'stale_provider_snapshots_not_imported': len(stale_provider),
    'repeat_ingestion_inserted': duplicate_check['inserted'], 'capture': str(capture),
    'tomorrow_dataset': str(destination / 'odds_snapshots.jsonl'), 'verified_quotes': verified}
(destination / 'ingestion.json').write_text(json.dumps(sync, indent=2), encoding='utf-8')
(ROOT / 'stages/03-build/output/scrapling-tomorrow-20261018.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in summary.items() if key != 'verified_quotes'}, indent=2))
