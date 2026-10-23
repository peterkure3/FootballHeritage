"""Capture dated football results and auditable last-five form for upcoming games.

Uses the configured football-data.org account. Missing competitions are reported,
never replaced by invented form. Run before training to refresh the history CSV.
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time

import pandas as pd

from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL, RAW_DATA_DIR, HISTORICAL_CSV_DIR
from etl.fetch_raw_data import FootballDataOrgFetcher
from models.data import canonical_matches, team_key

COMPETITIONS = ['PL', 'CL', 'PPL', 'DED', 'BL1', 'PD', 'SA', 'FL1', 'ELC', 'BSA']


def normalize_result(match: dict, observed_at: datetime) -> dict | None:
    """Only completed regulation-time scores can supply 1X2 training labels."""
    if match.get('status') != 'FINISHED':
        return None
    date = pd.Timestamp(match['utcDate'])
    if date >= observed_at:
        return None
    score = match.get('score', {})
    values = score.get('fullTime', {}) if score.get('duration') == 'REGULAR' else score.get('regularTime', {})
    hg, ag = values.get('home'), values.get('away')
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in [hg, ag]):
        return None
    return dict(date=date.isoformat(), home_team=match['homeTeam']['name'],
                away_team=match['awayTeam']['name'], home_score=hg, away_score=ag,
                home_provider_id=str(match['homeTeam']['id']), away_provider_id=str(match['awayTeam']['id']),
                provider_match_id=str(match['id']), competition=match['competition']['code'],
                status='FINISHED', data_source='football-data.org:team-form', observed_at=observed_at.isoformat())


def last_five(history: pd.DataFrame, team: str, cutoff: datetime) -> dict:
    """Oldest to newest; same-day outcomes excluded to match model features."""
    key = team_key(team)
    if history.empty:
        rows = history
    else:
        rows = history[(history.home_key.eq(key) | history.away_key.eq(key)) &
                       history.date.lt(pd.Timestamp(cutoff).normalize()) & history.result.notna()].tail(5)
    matches = []
    for row in rows.to_dict('records'):
        home = row['home_key'] == key
        gf, ga = (row['home_score'], row['away_score']) if home else (row['away_score'], row['home_score'])
        matches.append(dict(date=row['date'].isoformat(), opponent=row['away_team'] if home else row['home_team'],
                            venue='home' if home else 'away', goals_for=int(gf), goals_against=int(ga),
                            result='W' if gf > ga else 'L' if gf < ga else 'D', competition=row.get('competition')))
    sequence = ''.join(m['result'] for m in matches)
    return dict(sequence=sequence, order='oldest_to_newest', games=len(matches),
                wins=sequence.count('W'), draws=sequence.count('D'), losses=sequence.count('L'),
                status='five_available_results' if len(matches) == 5 else 'insufficient_history',
                scope='provider_covered_competitions', matches=matches)


def collect(output: Path, days: int = 7, competitions: list[str] | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    fetcher = FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL)
    results, upcoming, sources = {}, {}, []
    for code in competitions or COMPETITIONS:
        path = output / f'{code}.json'
        try:
            if path.exists():
                payload = json.loads(path.read_text(encoding='utf-8'))
            else:
                payload = fetcher.fetch_matches(code, (now-timedelta(days=180)).date().isoformat(), end.date().isoformat())
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                time.sleep(7)  # Account's free-tier request limit.
            for match in payload.get('matches', []):
                row = normalize_result(match, now)
                if row:
                    results[row['provider_match_id']] = row
                elif match.get('status') in {'SCHEDULED', 'TIMED'} and now < pd.Timestamp(match['utcDate']) <= end:
                    upcoming[str(match['id'])] = match
            sources.append(dict(competition=code, status='collected', matches=len(payload.get('matches', [])),
                                captured_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        except Exception as exc:
            sources.append(dict(competition=code, status='unavailable', error=type(exc).__name__))
    if not results:
        raise ValueError('No completed results collected; training history unchanged')
    history = canonical_matches([pd.DataFrame(results.values())])
    # Stable dated capture is reusable by the existing training and serving loader.
    history_path = output / 'history.csv'
    history.to_csv(history_path, index=False)
    fixtures = []
    for match in sorted(upcoming.values(), key=lambda m: m['utcDate']):
        fixtures.append(dict(provider_match_id=str(match['id']), kickoff=match['utcDate'],
                             competition=match['competition']['code'],
                             home_team=match['homeTeam']['name'], away_team=match['awayTeam']['name'],
                             home_form=last_five(history, match['homeTeam']['name'], now),
                             away_form=last_five(history, match['awayTeam']['name'], now)))
    report = dict(observed_at=now.isoformat(), end=end.isoformat(), sources=sources,
                  completed_results=len(history), upcoming_fixtures=len(fixtures),
                  both_teams_five=sum(f['home_form']['games'] == f['away_form']['games'] == 5 for f in fixtures),
                  coverage_note='Five available results do not prove all-competition coverage; provider may omit cups or leagues.',
                  history_sha256=hashlib.sha256(history_path.read_bytes()).hexdigest(), fixtures=fixtures)
    (output/'form.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=RAW_DATA_DIR/'team_form'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--competitions', nargs='+')
    parser.add_argument('--import-history', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.days <= 30:
        parser.error('--days must be 1..30')
    report = collect(args.output_dir, args.days, args.competitions)
    if args.import_history:
        destination = HISTORICAL_CSV_DIR / ('team_form_' + args.output_dir.name + '.csv')
        content = (args.output_dir/'history.csv').read_bytes()
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError('Existing history import differs; use a fresh capture directory')
        if not destination.exists():
            with destination.open('xb') as stream:
                stream.write(content)
        report['imported_history'] = str(destination)
    print(json.dumps({k:v for k,v in report.items() if k not in {'fixtures','sources'}}, indent=2))


if __name__ == '__main__':
    main()
