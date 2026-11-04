"""Bounded research capture: three Euro 2024 matches, never production training."""
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.scrapling_transport import ScraplingTransport

OUT = Path(__file__).with_name('soccer-events-pilot-20261022')
BASE = 'https://raw.githubusercontent.com/hudl/open-data/master/'


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / '.gitignore').write_text('*\n!.gitignore\n', encoding='utf-8')
    transport = ScraplingTransport()
    captures = []

    def fetch(url, name, decode=True):
        response = transport.get(url, timeout=60)
        response.raise_for_status()
        body = response.content
        (OUT / name).write_bytes(body)
        captures.append(dict(url=url, final_url=response.url, file=name,
                             retrieved_at=datetime.now(timezone.utc).isoformat(),
                             sha256=hashlib.sha256(body).hexdigest(), bytes=len(body)))
        return json.loads(body) if decode else body

    fetch(BASE + 'LICENSE.pdf', 'statsbomb-license.pdf', decode=False)
    competitions = fetch(BASE + 'data/competitions.json', 'competitions.json')
    matches = fetch(BASE + 'data/matches/55/282.json', 'euro-2024-matches.json')
    assert any(c['competition_id'] == 55 and c['season_id'] == 282 for c in competitions)
    reports = []
    for match in sorted(matches, key=lambda m: m['match_id'])[:3]:
        mid = match['match_id']
        events = fetch(BASE + f'data/events/{mid}.json', f'{mid}-events.json')
        lineups = fetch(BASE + f'data/lineups/{mid}.json', f'{mid}-lineups.json')
        home, away = match['home_team']['home_team_id'], match['away_team']['away_team_id']
        score = {home: 0, away: 0}
        checks = {
            'unique_event_ids': len({e['id'] for e in events}) == len(events),
            'strict_source_index': all(a['index'] < b['index'] for a, b in zip(events, events[1:])),
            'lineup_teams_match': {t['team_id'] for t in lineups} == {home, away},
            'both_regulation_periods_end': {1, 2}.issubset({e['period'] for e in events if e['type']['name'] == 'Half End'}),
        }
        rows = []
        for event in events:
            team = event.get('team', {}).get('id')
            kind = event['type']['name']
            loc = event.get('location') or [None, None]
            detail = event.get(kind.lower().replace(' ', '_'), {})
            end = detail.get('end_location') or [None, None]
            rows.append(dict(source='statsbomb_open_research', match_id=mid,
                             event_id=event['id'], source_index=event['index'],
                             period=event['period'], period_timestamp=event['timestamp'],
                             minute=event['minute'], second=event['second'],
                             team_id=team, player_id=event.get('player', {}).get('id'),
                             event_type=kind, possession_id=event.get('possession'),
                             possession_team_id=event.get('possession_team', {}).get('id'),
                             x=loc[0], y=loc[1], end_x=end[0], end_y=end[1],
                             outcome=detail.get('outcome', {}).get('name'),
                             shot_xg=event.get('shot', {}).get('statsbomb_xg'),
                             home_goals_before=score[home], away_goals_before=score[away]))
            if event['period'] == 5:
                continue  # Shootouts are a separate outcome, never match goals.
            if kind == 'Shot' and event['shot']['outcome']['name'] == 'Goal':
                score[team] += 1
            elif kind == 'Own Goal Against':
                score[away if team == home else home] += 1
        checks['event_score_matches_metadata'] = (score[home], score[away]) == (match['home_score'], match['away_score'])
        with (OUT / f'{mid}-events.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        reports.append(dict(match_id=mid, date=match['match_date'],
                            home=match['home_team']['home_team_name'], away=match['away_team']['away_team_name'],
                            score=[score[home], score[away]], events=len(events),
                            event_types=dict(Counter(e['type']['name'] for e in events)),
                            checks=checks, passed=all(checks.values())))
    # Dataset metadata, not a claim that the entire Wyscout archive was harvested.
    try:
        articles = fetch('https://api.figshare.com/v2/collections/4415000/articles?page_size=100', 'wyscout-articles.json')
        for article in articles:
            if article['title'].lower() in {'events', 'matches', 'players', 'teams'}:
                fetch(article['url'], f"wyscout-{article['id']}-metadata.json")
    except Exception as exc:
        reports.append({'wyscout_metadata_error': str(exc)})
    summary = dict(purpose='research feasibility only; no trained simulator',
                   competition_seasons=len(competitions), euro_2024_matches=len(matches),
                   match_reports=reports, captures=captures,
                   limitations=['same-provider score reconciliation, not independent event verification',
                                'CSV is a discovery projection; retain nested raw JSON for modeling',
                                'source branch is mutable; content hashes identify captured bytes',
                                'coordinate units are provider 120x80, not metres',
                                'StatsBomb data use is governed by captured agreement'])
    (OUT / 'manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'captures'}, indent=2))
    if not all(r['passed'] for r in reports if 'passed' in r):
        raise SystemExit('Event validation failed; see manifest')


if __name__ == '__main__':
    main()
