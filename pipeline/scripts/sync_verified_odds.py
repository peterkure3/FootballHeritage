"""Repair bounded source-verified fixture kickoffs and ingest exact-matched snapshots."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from api.db import get_db_connection
from config import FOOTBALL_DATA_ORG_DIR
from models.data import match_odds_to_fixtures
from models.import_sportsbook_odds import normalize_snapshots, import_snapshots

# Reviewed EPL-only spellings; applied to joins, never to frozen model features.
EPL_ALIASES = {'Bournemouth':'AFC Bournemouth', 'Ipswich':'Ipswich Town FC',
    'Manchester Utd':'Manchester United FC', 'Sunderland':'Sunderland AFC',
    'Brighton & Hove Albion':'Brighton & Hove Albion FC', 'Brighton':'Brighton & Hove Albion FC',
    'Tottenham':'Tottenham Hotspur FC'}


def sync(capture, match_date, output, apply=False):
    if output.exists():
        raise ValueError('Choose a new audit path; existing reports are immutable')
    source = capture / 'odds_snapshots.jsonl'
    payload = source.read_bytes()
    records = [json.loads(line) for line in payload.decode().splitlines() if line.strip()]
    records = [r for r in records if r.get('country') == 'England' and r.get('competition') == 'Premier League']
    odds = normalize_snapshots(records) if records else pd.DataFrame()
    if not odds.empty:
        for side in ['home','away']:
            odds[side + '_team'] = odds[side + '_team'].replace(EPL_ALIASES)
    raw_source = sorted(FOOTBALL_DATA_ORG_DIR.glob('matches_PL_*.json'))[-1]
    official = json.loads(raw_source.read_text(encoding='utf-8'))['matches']
    start = pd.Timestamp(match_date, tz='UTC')
    end = start + pd.Timedelta(days=8)
    repairs = []
    inserted = []
    with get_db_connection().begin() as conn:
        conn.execute(text("SET LOCAL TIME ZONE 'UTC'"))
        conn.execute(text('SELECT pg_advisory_xact_lock(7160410)'))
        fixtures = pd.read_sql(text("SELECT match_id,date,home_team,away_team,competition,data_source FROM matches WHERE competition='Premier League' AND date >= :start AND date < :end FOR UPDATE"), conn,
                               params={'start': start.tz_localize(None), 'end': end.tz_localize(None)})
        for raw in official:
            kickoff = pd.Timestamp(raw['utcDate'])
            if not start <= kickoff < end:
                continue
            matches = fixtures[fixtures.match_id.eq(raw['id'])]
            if len(matches) != 1:
                continue
            row = matches.iloc[0]
            if row.home_team != raw['homeTeam']['name'] or row.away_team != raw['awayTeam']['name'] or row.data_source != 'football_data_org':
                continue
            before = pd.Timestamp(row.date).tz_localize('UTC')
            if before == kickoff:
                continue
            if before - kickoff != pd.Timedelta(hours=3):
                raise ValueError('Unexpected fixture discrepancy; refusing an automatic correction')
            repairs.append({'match_id': int(raw['id']), 'before': before.isoformat(), 'after': kickoff.isoformat()})
            fixtures.loc[matches.index, 'date'] = kickoff.tz_localize(None)
            if apply:
                conn.execute(text('UPDATE matches SET date=:date WHERE match_id=:id AND date=:before'),
                             {'date': kickoff.tz_localize(None), 'id': int(raw['id']), 'before': before.tz_localize(None)})
        joined = match_odds_to_fixtures(fixtures, odds, exact_kickoff=True)
        for row in joined.to_dict('records'):
            region = row.get('region')
            book = row['bookmaker'] + (':' + region if isinstance(region, str) and region else '')
            params = {'match_id': int(row['match_id']), 'bookmaker': book,
                      **{key: float(row[key]) for key in ['home_win','draw','away_win']},
                      'updated_at': pd.Timestamp(row['observed_at']).tz_convert('UTC').tz_localize(None)}
            if apply:
                odds_id = conn.execute(text('''INSERT INTO odds (match_id,bookmaker,home_win,draw,away_win,updated_at)
                    SELECT :match_id,:bookmaker,:home_win,:draw,:away_win,:updated_at WHERE NOT EXISTS (
                        SELECT 1 FROM odds WHERE match_id=:match_id AND bookmaker=:bookmaker AND updated_at=:updated_at)
                    RETURNING id'''), params).scalar()
                if odds_id:
                    inserted.append({'snapshot_id': row['snapshot_id'], 'odds_id': odds_id, 'match_id': params['match_id'], 'bookmaker': book})
    report = {'applied': apply, 'source_sha256': hashlib.sha256(payload).hexdigest(),
        'official_source': str(raw_source), 'official_source_sha256': hashlib.sha256(raw_source.read_bytes()).hexdigest(),
        'fixture_repairs': repairs, 'matched_snapshots': len(joined), 'inserted': inserted,
        'generated_at': datetime.now(timezone.utc).isoformat()}
    if apply and records:
        identities = {row['snapshot_id']: int(row['match_id']) for row in joined.to_dict('records')}
        official_names = fixtures.set_index('match_id').to_dict('index')
        for record in records:
            if record['snapshot_id'] in identities:
                canonical = official_names[identities[record['snapshot_id']]]
                record.update(canonical_home_team=canonical['home_team'], canonical_away_team=canonical['away_team'])
        filtered = capture / 'canonical_epl_snapshots.jsonl'
        if not filtered.exists():
            with filtered.open('x', encoding='utf-8') as stream:
                for record in records:
                    stream.write(json.dumps(record) + '\n')
        report['training_import'] = import_snapshots(filtered)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--match-date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sync(args.capture, args.match_date, args.output, args.apply)


if __name__ == '__main__':
    main()
