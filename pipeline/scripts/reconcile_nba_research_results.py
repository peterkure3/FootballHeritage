"""Independently reconcile current NBA research finals with daily ESPN captures."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
import requests

from etl.nba_public_parsers import team


def normalize_event(event: dict) -> dict | None:
    status = event.get('status', {})
    if (event.get('season', {}).get('type') != 2 or status.get('type', {}).get('completed') is not True
            or type(status.get('period')) is not int or status['period'] < 4):
        return None
    competitors = event['competitions'][0]['competitors']
    home = [row for row in competitors if row.get('homeAway') == 'home']
    away = [row for row in competitors if row.get('homeAway') == 'away']
    if len(home) != 1 or len(away) != 1:
        raise ValueError('Ambiguous independent competitor orientation')
    home, away = home[0], away[0]
    names = team(home['team']['displayName']), team(away['team']['displayName'])
    if not all(names) or names[0] == names[1]:
        raise ValueError('Unknown independent NBA identity')
    scores = home.get('score'), away.get('score')
    if any(not str(score).isdigit() for score in scores):
        raise ValueError('Invalid independent final score')
    if int(scores[0]) == int(scores[1]):
        raise ValueError('Tied NBA final score')
    kickoff = pd.Timestamp(event['date'])
    if kickoff.tzinfo is None:
        raise ValueError('Independent kickoff requires timezone')
    return {'id': str(event['id']), 'date': kickoff.isoformat(),
            'home_team': names[0], 'away_team': names[1],
            'home_score': int(scores[0]), 'away_score': int(scores[1])}


def capture_days(primary: list[dict]) -> list[pd.Timestamp]:
    # ESPN groups by US date; UTC kickoffs after midnight can belong to the prior day.
    days = set()
    for row in primary:
        kickoff = pd.Timestamp(row['date'])
        if kickoff.tzinfo is None:
            raise ValueError('Primary kickoff requires timezone')
        day = kickoff.tz_convert('UTC').normalize()
        days.update([day, day - pd.Timedelta(days=1)])
    if not days:
        raise ValueError('No primary results to reconcile')
    return sorted(days)


def run(root: Path) -> dict:
    manifest = json.loads((root/'manifest.json').read_text())
    source = root/'normalized.jsonl'
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['normalized_sha256']:
        raise ValueError('Primary result checksum mismatch')
    for entry in manifest['sources']:
        if hashlib.sha256((root/entry['file']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Primary raw response checksum mismatch')
    primary = [json.loads(line) for line in source.read_text().splitlines()]
    output = root/'reconciliation'; output.mkdir(exist_ok=False)
    days = capture_days(primary)

    def capture(day):
        date = day.strftime('%Y%m%d')
        response = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                                params={'dates': date, 'limit': 100}, timeout=30)
        observed = datetime.now(timezone.utc).isoformat()
        path = output/f'{date}.json'; path.write_bytes(response.content)
        evidence = {'file': path.name, 'sha256': hashlib.sha256(response.content).hexdigest(),
                    'observed_at': observed, 'url': response.url, 'status': response.status_code}
        if response.status_code != 200:
            return evidence, []
        return evidence, [row for event in response.json().get('events', []) if (row := normalize_event(event))]

    sources = []; independent = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        for evidence, rows in executor.map(capture, days):
            sources.append(evidence)
            for row in rows:
                key = row['home_team'], row['away_team'], pd.Timestamp(row['date']).isoformat()
                if key in independent and independent[key][0] != row:
                    raise ValueError('Conflicting independent final observations')
                independent[key] = row, evidence
    accepted = []; excluded = []
    for row in primary:
        key = row['home_team'], row['away_team'], pd.Timestamp(row['date']).isoformat()
        matched = independent.get(key)
        if not matched:
            excluded.append({'id': row['provider_event_id'], 'reason': 'no_exact_independent_final'})
        elif any(row[column] != matched[0][column] for column in ['home_score','away_score']):
            excluded.append({'id': row['provider_event_id'], 'reason': 'independent_score_disagreement'})
        else:
            available = max(pd.Timestamp(row['result_available_at']), pd.Timestamp(matched[1]['observed_at']))
            accepted.append({**row, 'result_available_at': available.isoformat(),
                'independent_provider_event_id': matched[0]['id'], 'independent_source': matched[1]})
    target = output/'reconciled.jsonl'
    target.write_text(''.join(json.dumps(row)+'\n' for row in accepted))
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'sources': sources,
              'primary_source_sha256': manifest['normalized_sha256'], 'matched': len(accepted),
              'excluded': excluded, 'normalized_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'availability_policy': 'Observed after both independent captures; never backdated', 'production_changed': False}
    (output/'manifest.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'matched': len(accepted), 'excluded': excluded,
                      'source_errors': [s for s in sources if s['status'] != 200]}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(); run(args.root)
