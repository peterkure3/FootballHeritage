"""Link captured football prices to unique competition/team/exact-kickoff fixtures."""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from api.db import get_db_connection
from models.data import match_odds_to_fixtures
from models.import_sportsbook_odds import normalize_snapshots

COMPETITIONS = {
    'soccer_epl': 'Premier League', 'England Premier League': 'Premier League',
    'England - Premier League': 'Premier League',
    'soccer_uefa_champs_league': 'UEFA Champions League',
    'UEFA - Champions League': 'UEFA Champions League',
    'UEFA Champions League': 'UEFA Champions League',
}
CL_TEAM_ALIASES = {
    'Inter': 'FC Internazionale Milano', 'Internazionale': 'FC Internazionale Milano',
    'Inter Milan': 'FC Internazionale Milano', 'Inter Milano': 'FC Internazionale Milano',
    'Bayern Munich': 'FC Bayern München', 'FC Bayern Munich': 'FC Bayern München',
    'Bayern München': 'FC Bayern München', 'Bayern Munchen': 'FC Bayern München',
    'Club Brugge': 'Club Brugge KV', 'Lens': 'Racing Club de Lens',
    'RC Lens': 'Racing Club de Lens', 'Racing Club Lens': 'Racing Club de Lens',
    'Sporting CP': 'Sporting Clube de Portugal', 'Sporting Lisbon': 'Sporting Clube de Portugal',
    'Sporting': 'Sporting Clube de Portugal', 'Sp Lisbon': 'Sporting Clube de Portugal',
    'Sporting Lisboa': 'Sporting Clube de Portugal',
    'Viking': 'Viking FK', 'Viking Stavanger': 'Viking FK',
    'LASK': 'LASK Linz', 'Roma': 'AS Roma', 'Dortmund': 'Borussia Dortmund',
    'Shakhtar': 'FK Shakhtar Donetsk', 'AEK': 'PAE AEK', 'PSG': 'Paris Saint-Germain FC',
    'Betis': 'Real Betis Balompié', 'Slovan': 'ŠK Slovan Bratislava',
    'Porto': 'FC Porto', 'Stuttgart': 'VfB Stuttgart',
    'Bodo/Glimt': 'FK Bodø/Glimt',
    'Bodo-Glimt': 'FK Bodø/Glimt', 'Paris Saint Germain': 'Paris Saint-Germain FC',
    'Feyenoord': 'Feyenoord Rotterdam', 'Como': 'Como 1907',
    'Como Calcio': 'Como 1907',
    'Real Madrid': 'Real Madrid CF', 'Fenerbahce': 'Fenerbahçe SK',
    'Fenerbahce Istanbul': 'Fenerbahçe SK', 'Bodø/Glimt': 'FK Bodø/Glimt',
    'Bodoe/Glimt': 'FK Bodø/Glimt', 'Real Betis': 'Real Betis Balompié',
    'Real Betis Seville': 'Real Betis Balompié',
    'Shakhtar Donetsk': 'FK Shakhtar Donetsk', 'FC Shakhtar Donetsk': 'FK Shakhtar Donetsk',
    'AEK Athens': 'PAE AEK', 'Slovan Bratislava': 'ŠK Slovan Bratislava',
    'SK Slovan Bratislava': 'ŠK Slovan Bratislava',
}


def matched_grid_quotes(fixtures, records):
    if not records or fixtures.empty:
        return pd.DataFrame()
    odds = normalize_snapshots(records)
    odds['competition'] = odds.competition.replace(COMPETITIONS)
    joined = []
    for competition, offers in odds.groupby('competition'):
        offers = offers.copy()
        if competition == 'UEFA Champions League':
            for side in ['home', 'away']:
                names = offers[side + '_team']
                aliases = {name.casefold(): canonical for name, canonical in CL_TEAM_ALIASES.items()}
                offers[side + '_team'] = names.str.casefold().map(aliases).combine_first(names)
        matches = fixtures[fixtures.competition.eq(competition)]
        if not matches.empty:
            group = match_odds_to_fixtures(matches, offers, exact_kickoff=True)
            # BetOnline and BookMaker line positions can differ from fixture home/away.
            # Match the same two named teams at the exact kickoff, swapping their prices too.
            reverse = offers[offers.bookmaker.isin(['betonlineag', 'bookmaker'])].copy()
            if not reverse.empty:
                reverse[['home_team', 'away_team']] = reverse[['away_team', 'home_team']].to_numpy()
                reverse[['home_win', 'away_win']] = reverse[['away_win', 'home_win']].to_numpy()
                reversed_group = match_odds_to_fixtures(matches, reverse, exact_kickoff=True)
                group = pd.concat([group, reversed_group], ignore_index=True)
                if not group.empty:
                    group = group[group.groupby('snapshot_id').snapshot_id.transform('size').eq(1)]
            if not group.empty:
                joined.append(group)
    return pd.concat(joined, ignore_index=True) if joined else pd.DataFrame()


def load_grid_snapshots(capture):
    """Use the full normalized export when adapters expanded an original capture."""
    manifest = capture / 'normalization_report.json'
    dataset = 'odds_snapshots.jsonl'
    if manifest.exists():
        dataset = json.loads(manifest.read_text(encoding='utf-8'))['dataset']
        if dataset not in {'odds_snapshots.jsonl', 'odds_snapshots_complete.jsonl'}:
            raise ValueError('Unexpected normalized sportsbook dataset')
    path = capture / dataset
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return path, records


def capture_cache_rejections(capture):
    """Honor HTTP cache evidence when the collector retained it."""
    audit = capture / 'cache-audit.json'
    if not audit.exists():
        return {}
    rejected = {}
    for source in json.loads(audit.read_text(encoding='utf-8')):
        responses = source.get('http_audit', [])
        if not responses or source.get('http_status') != 200:
            rejected[source['bookmaker']] = 'source_unavailable'
            continue
        response = responses[-1]
        headers = {key.lower(): value for key, value in response['headers'].items()}
        observed = pd.Timestamp(response['observed_at'])
        age = float(headers.get('age') or 0)
        if headers.get('date'):
            age = max(age, (observed - pd.Timestamp(parsedate_to_datetime(headers['date']))).total_seconds())
        if age > 120:
            rejected[source['bookmaker']] = 'upstream_cache_older_than_120_seconds'
        if source['bookmaker'] == 'bookmaker' and headers.get('last-modified'):
            modified = pd.Timestamp(parsedate_to_datetime(headers['last-modified']))
            if (observed - modified).total_seconds() > 300:
                rejected[source['bookmaker']] = 'conservative_page_timestamp_older_than_300_seconds'
    return rejected


def sync_grid(capture, apply=False):
    dataset, records = load_grid_snapshots(capture)
    report = {'capture': str(capture), 'dataset': dataset.name, 'applied': apply, 'snapshots': len(records), 'inserted': 0}
    rejected = capture_cache_rejections(capture)
    records = [record for record in records if record['bookmaker'] not in rejected]
    report.update(cache_rejections=rejected, eligible_snapshots=len(records))
    with get_db_connection().begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(7160411)'))
        fixtures = pd.read_sql(text("""SELECT match_id, date, home_team, away_team, competition
            FROM matches WHERE date > (NOW() AT TIME ZONE 'UTC') AND result IS NULL
            AND UPPER(COALESCE(status,'')) NOT IN
                ('LIVE','IN_PLAY','PAUSED','FINISHED','CANCELLED','CANCELED','POSTPONED')"""), connection)
        joined = matched_grid_quotes(fixtures, records)
        report['matched_snapshots'] = len(joined)
        report['by_bookmaker'] = joined.bookmaker.value_counts().to_dict() if not joined.empty else {}
        report['by_competition'] = joined.competition.value_counts().to_dict() if not joined.empty else {}
        report['unmatched_snapshots'] = len(records) - len(joined)
        report['matches'] = [{key: row[key] for key in ['snapshot_id', 'match_id', 'bookmaker', 'competition']}
                             for row in joined.to_dict('records')]
        for row in joined.to_dict('records') if apply else []:
            observed = pd.Timestamp(row['observed_at'])
            if row['bookmaker'] == 'bookmaker':
                observed = pd.Timestamp(row['source_updated_at'])
            now = pd.Timestamp.now(tz='UTC')
            if not now - pd.Timedelta(hours=24) <= observed <= now:
                continue
            region = row.get('region')
            book = row['bookmaker'] + (':' + region if isinstance(region, str) and region else '')
            params = {'match_id': int(row['match_id']), 'bookmaker': book,
                      **{key: float(row[key]) for key in ['home_win', 'draw', 'away_win']},
                      'observed': observed.tz_convert('UTC').tz_localize(None)}
            identifier = connection.execute(text("""INSERT INTO odds
                (match_id, bookmaker, home_win, draw, away_win, updated_at)
                SELECT :match_id, :bookmaker, :home_win, :draw, :away_win, :observed
                WHERE NOT EXISTS (SELECT 1 FROM odds WHERE match_id=:match_id
                    AND bookmaker=:bookmaker AND updated_at=:observed) RETURNING id"""), params).scalar()
            report['inserted'] += identifier is not None
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    report = sync_grid(args.capture, args.apply)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (args.capture / ('grid_sync_' + stamp + '.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'matches'}, indent=2))


if __name__ == '__main__':
    main()
