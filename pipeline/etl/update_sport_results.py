"""Capture recent sport finals for the existing file-backed multisport loaders."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import requests

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import API_RETRY_ATTEMPTS, API_TIMEOUT, RAW_DATA_DIR
from etl.fetch_basketball_history import normalize_events

SPORTS = {
    'nba': {'path': 'basketball/nba', 'league': 'basketball_nba'},
    'ncaab': {'path': 'basketball/mens-college-basketball', 'league': 'basketball_ncaab', 'groups': 50},
    'wnba': {'path': 'basketball/wnba', 'league': 'basketball_wnba'},
    'nfl': {'path': 'football/nfl', 'league': 'americanfootball_nfl', 'ties': True},
    'ncaaf': {'path': 'football/college-football', 'league': 'americanfootball_ncaaf', 'groups': 80},
}


def normalize(payload: dict, sport: str, observed_at: datetime, raw_ref: str) -> list[dict]:
    """Keep explicit regular/postseason finals, with observed availability and OT scores."""
    spec = SPORTS[sport]
    if not isinstance(payload, dict) or not isinstance(payload.get('events'), list):
        raise ValueError('Scoreboard response must contain an events list')
    declared = {league.get('slug') for league in (payload.get('leagues') or []) if isinstance(league, dict) and league.get('slug')}
    if declared and spec['path'].split('/')[-1] not in declared:
        raise ValueError('Scoreboard league does not match the requested sport')
    if len(payload['events']) >= 1000:
        raise ValueError('Scoreboard may be truncated; capture not published')
    eligible = []
    for event in payload['events']:
        if event.get('season', {}).get('type') not in {2, 3}:
            continue
        for competition in event.get('competitions', []):
            if competition.get('type', {}).get('abbreviation') == 'ALLSTAR':
                continue
            status = competition.get('status', {}).get('type', {})
            if (status.get('completed') is not True or status.get('state') != 'post'
                    or status.get('name') not in {'STATUS_FINAL', 'STATUS_FINAL_OVERTIME'}):
                continue
            competitors = competition.get('competitors', [])
            if len(competitors) != 2 or {team.get('homeAway') for team in competitors} != {'home', 'away'}:
                raise ValueError('Completed fixture requires one home and one away competitor')
            normalized_competitors = []
            for competitor in competitors:
                score = competitor.get('score')
                try:
                    valid = not isinstance(score, bool) and math.isfinite(float(score)) and float(score) >= 0 and float(score).is_integer()
                except (TypeError, ValueError):
                    valid = False
                if not valid:
                    raise ValueError('Invalid final score')
                normalized_competitors.append({**competitor, 'score': int(float(score))})
            if not spec.get('ties', False) and normalized_competitors[0]['score'] == normalized_competitors[1]['score']:
                raise ValueError('Unexpected tied basketball or college football final')
            eligible.append({**event, 'competitions': [{**competition, 'competitors': normalized_competitors}]})
    rows = normalize_events(eligible, spec['league'], raw_ref, allow_ties=spec.get('ties', False))
    for row in rows:
        kickoff = datetime.fromisoformat(row['date'])
        if (kickoff >= observed_at or not row['home_team'].strip() or not row['away_team'].strip()
                or row['home_team'].casefold().strip() == row['away_team'].casefold().strip()):
            raise ValueError('Invalid completed fixture identity or timestamp')
        row.update(result_available_at=observed_at.isoformat(), result_availability_precision='OBSERVED_CAPTURE',
                   settlement_rule='INCLUDING_OVERTIME_TIES_VOID' if sport == 'nfl' else 'INCLUDING_OVERTIME',
                   collection_scope='RECENT_SCOREBOARD')
    return rows


def fetch(url: str, params: dict) -> requests.Response:
    for attempt in range(API_RETRY_ATTEMPTS):
        try:
            response = requests.get(url, params=params, timeout=(10, API_TIMEOUT))
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            status = error.response.status_code if error.response is not None else None
            retryable = isinstance(error, (requests.Timeout, requests.ConnectionError)) or status == 429 or (status is not None and status >= 500)
            if not retryable or attempt + 1 == API_RETRY_ATTEMPTS:
                raise
            time.sleep(min(30, 2 ** (attempt + 1)))
    raise RuntimeError('No request attempts configured')


def update_results(sport: str, days: int = 7, *, start_date: date | None = None,
                   end_date: date | None = None, root: Path = RAW_DATA_DIR) -> dict:
    if sport not in SPORTS:
        raise ValueError('Unsupported sport')
    today = datetime.now(timezone.utc).date()
    end = end_date or today
    start = start_date or end - timedelta(days=days)
    if not 1 <= days <= 90 or start > end or end > today or (end - start).days > 90:
        raise ValueError('Use an ordered date range of at most 90 days through today')
    spec = SPORTS[sport]
    output = root / 'results' / sport / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, exist_ok=False)
    rows, sources = [], []
    try:
        day = start
        while day <= end:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{spec['path']}/scoreboard"
            params = {'dates': day.strftime('%Y%m%d'), 'limit': 1000}
            if spec.get('groups'):
                params['groups'] = spec['groups']
            response = fetch(url, params)
            observed = datetime.now(timezone.utc)
            raw = response.content
            path = output / f'{day:%Y%m%d}.json'
            path.write_bytes(raw)
            payload = json.loads(raw)
            parsed = normalize(payload, sport, observed, str(path.resolve()))
            rows.extend(parsed)
            sources.append({'file': path.name, 'url': url, 'params': params, 'observed_at': observed.isoformat(),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'completed_games': len(parsed)})
            print(f'{sport.upper()} {day}: {len(parsed)} completed games', flush=True)
            day += timedelta(days=1)
            if day <= end:
                time.sleep(.3)
        unique = {}
        for row in rows:
            key = row['provider_event_id']
            if key in unique and any(row[field] != unique[key][field] for field in ('date', 'home_team', 'away_team', 'home_score', 'away_score')):
                raise ValueError('Conflicting observations of the same provider game')
            unique.setdefault(key, row)
        rows = list(unique.values())
        data = ''.join(json.dumps(row, allow_nan=False) + '\n' for row in rows).encode('utf-8')
        (output / 'normalized.jsonl').write_bytes(data)
        report = {'schema_version': 1, 'sport': sport, 'league': spec['league'],
                  'start_date': start.isoformat(), 'end_date': end.isoformat(),
                  'captured_at': datetime.now(timezone.utc).isoformat(), 'completed_games': len(rows),
                  'sources': sources, 'normalized_sha256': hashlib.sha256(data).hexdigest(),
                  'availability_policy': 'Observed after retrieval; never backdated to game day',
                  'score_policy': 'Provider final scores including overtime', 'models_changed': False}
        temporary = output / 'manifest.tmp'
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        temporary.replace(output / 'manifest.json')
        return {**report, 'output': str(output)}
    except Exception as error:
        (output / 'failure.json').write_text(json.dumps({'sport': sport, 'error_type': type(error).__name__,
                                                       'message': 'Incomplete result update; no manifest published.'}), encoding='utf-8')
        raise


def load_recent_results(leagues: list[str], root: Path = RAW_DATA_DIR) -> list[dict]:
    rows = []
    for sport, spec in SPORTS.items():
        if spec['league'] not in leagues:
            continue
        for path in sorted((root / 'results' / sport).glob('*/manifest.json')):
            report = json.loads(path.read_text(encoding='utf-8'))
            if report.get('schema_version') != 1 or report['sport'] != sport or report['league'] != spec['league']:
                raise ValueError('Result capture scope mismatch')
            data = (path.parent / 'normalized.jsonl').read_bytes()
            if hashlib.sha256(data).hexdigest() != report['normalized_sha256']:
                raise ValueError('Result capture checksum mismatch')
            for source in report['sources']:
                if Path(source['file']).name != source['file'] or hashlib.sha256((path.parent / source['file']).read_bytes()).hexdigest() != source['sha256']:
                    raise ValueError('Raw result capture checksum mismatch')
            captured = [json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip()]
            if any(row.get('league') != spec['league'] for row in captured):
                raise ValueError('Cross-sport result capture')
            rows.extend(captured)
    return rows


def check_results(sport: str, root: Path = RAW_DATA_DIR) -> dict:
    rows = load_recent_results([SPORTS[sport]['league']], root)
    report = {'sport': sport, 'stored_final_rows': len(rows),
              'distinct_provider_games': len({row['provider_event_id'] for row in rows})}
    if sport in {'nba', 'ncaab'}:
        from api.sport_performance import feed
        performance = feed(sport)['summary']
        report.update(eligible_settled_forecasts=performance['total_predictions'],
                      pending_or_unverified_finals=performance['excluded']['pending'])
    return report


def main(sport: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    if sport is None:
        parser.add_argument('sport', choices=list(SPORTS))
    parser.add_argument('--days', type=int, default=7, help='Look back this many days through today (inclusive)')
    parser.add_argument('--start-date', type=date.fromisoformat)
    parser.add_argument('--end-date', type=date.fromisoformat)
    parser.add_argument('--check', action='store_true', help='Inspect local result coverage; no HTTP requests or writes')
    args = parser.parse_args()
    sport = sport or args.sport
    try:
        report = check_results(sport) if args.check else update_results(sport, args.days, start_date=args.start_date, end_date=args.end_date)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, requests.RequestException) as error:
        reason = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(f'{sport.upper()} result update failed: {reason}; previous completed captures retained.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
