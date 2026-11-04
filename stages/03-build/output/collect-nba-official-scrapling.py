"""Collect official NBA game pages with Scrapling; run from pipeline/."""
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.scrapling_transport import ScraplingTransport, USER_AGENT
from scrapling.parser import Selector


def main():
    now = datetime.now(timezone.utc)
    start, end = now.date() - timedelta(days=7), now.date() + timedelta(days=14)
    output = ROOT / 'pipeline/data/raw/nba/scrapling' / now.strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, exist_ok=False)
    transport = ScraplingTransport()
    captures, games, leaders, teams, failures = [], {}, [], {}, []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        url = f'https://www.nba.com/games?date={day}'
        try:
            response = transport.get(url, timeout=45, headers={'User-Agent': USER_AGENT})
            response.raise_for_status()
            embedded = Selector(response.text).css('script#__NEXT_DATA__::text').get()
            props = json.loads(embedded)['props']['pageProps']
            if props.get('hasError') or props.get('selectedDate') != str(day):
                raise ValueError('Provider date/error validation failed')
            feed = props['gameCardFeed']
            if feed.get('nextPageToken'):
                raise ValueError('Feed is paginated; capture incomplete')
            raw = output / f'games-{day}-raw.json'
            raw.write_text(embedded, encoding='utf-8')
            count = 0
            for module in feed.get('modules', []):
                for card in module.get('cards', []):
                    game = card.get('cardData', {})
                    if not game.get('gameId'):
                        continue
                    identity = str(game['gameId'])
                    home, away, status = game['homeTeam'], game['awayTeam'], game['gameStatus']
                    row = {'id': identity, 'league': 'basketball_nba', 'date': game['gameTimeUtc'],
                        'home_team': home['teamName'], 'away_team': away['teamName'],
                        'home_team_id': str(home['teamId']), 'away_team_id': str(away['teamId']),
                        'home_score': home.get('score') if status in {2, 3} else None,
                        'away_score': away.get('score') if status in {2, 3} else None,
                        'completed': status == 3, 'status': game.get('gameStatusText'),
                        'season': game.get('seasonYear'), 'season_type': game.get('seasonType'),
                        'source_url': url, 'game_url': game.get('shareUrl'), 'provider': 'nba.com',
                        'captured_at': datetime.now(timezone.utc).isoformat()}
                    assert row['home_team_id'] != row['away_team_id'], 'Identical opponents'
                    datetime.fromisoformat(row['date'].replace('Z', '+00:00'))
                    if row['completed']:
                        assert all(isinstance(row[k], int) and row[k] >= 0 for k in ('home_score', 'away_score')), 'Invalid final scores'
                    if identity in games:
                        raise ValueError(f'Duplicate game ID {identity}')
                    games[identity] = row
                    for side, team in (('home', home), ('away', away)):
                        teams[str(team['teamId'])] = {'id': str(team['teamId']), 'name': team['teamName'],
                            'abbreviation': team.get('teamTricode'), 'slug': team.get('teamSlug')}
                        leader = team.get('teamLeader')
                        if leader and status in {2, 3}:
                            leaders.append({'game_id': identity, 'team_id': str(team['teamId']), 'side': side,
                                **{k: leader.get(k) for k in ('personId', 'name', 'points', 'rebounds', 'assists', 'blocks', 'steals')}})
                    count += 1
            expected = props.get('allGamesInCurrentYear', {}).get(str(day.year), {}).get(str(day))
            if expected is not None and count != expected:
                raise ValueError(f'Expected {expected} games but extracted {count}')
            captures.append({'date': str(day), 'url': response.url, 'http_status': response.status_code,
                'games': count, 'expected_games': expected, 'file': raw.name,
                'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()})
            print(f'{day}: {count} games', flush=True)
        except Exception as exc:
            failures.append({'date': str(day), 'url': url, 'error': str(exc)})
            print(json.dumps(failures[-1]), flush=True)
        time.sleep(1)
    exports = {}
    for name, rows in [('teams', list(teams.values())), ('games', list(games.values())), ('player_leaders', leaders)]:
        path = output / f'{name}.json'
        path.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        exports[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if rows:
            with (output / f'{name}.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    manifest = {'transport': 'scrapling', 'provider': 'nba.com', 'captured_at': now.isoformat(),
        'date_start': str(start), 'date_end': str(end), 'teams': len(teams), 'games': len(games),
        'completed_games': sum(x['completed'] for x in games.values()), 'player_leaders': len(leaders),
        'season_types': dict(Counter(x['season_type'] for x in games.values())),
        'captures': captures, 'failures': failures, 'exports_sha256': exports,
        'note': 'Dates follow NBA selected game date; start times are UTC. Preseason is labeled; scheduled scores are null. Team names match game cards. Player leaders are provider-selected, not full box scores. No odds, standings, database writes, or training.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), **{k:v for k,v in manifest.items() if k != 'captures'}}, indent=2), flush=True)
    return 1 if failures or not games else 0


if __name__ == '__main__':
    raise SystemExit(main())
