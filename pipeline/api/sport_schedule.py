"""Sport schedules from retained upcoming fixtures and checksum-verified finals."""
from collections import defaultdict
from datetime import date, datetime
import hashlib
import math

from api.betting_intel import SPORTS, timestamp


def identity(sport: str, row: dict, kickoff: datetime) -> tuple:
    names = [str(row.get(key, '')).strip() for key in ('home_team', 'away_team')]
    if sport == 'nba':
        from etl.nba_public_parsers import team
        names = [team(name) or name for name in names]
    return sport, *(name.casefold() for name in names), kickoff.isoformat()


def build_schedule(sport: str, fixtures: list[dict], results: list[dict],
                   start: date, end: date, now: datetime) -> dict:
    """Keep exact fixture identities and quarantine conflicting final scores."""
    if sport not in SPORTS or sport == 'football':
        raise ValueError('Unsupported schedule sport')
    games, finals = {}, defaultdict(list)
    for row in fixtures:
        kickoff = timestamp(row.get('kickoff'))
        if (row.get('sport') != sport or kickoff is None or kickoff <= now
                or not start <= kickoff.date() <= end
                or not row.get('home_team') or not row.get('away_team')):
            continue
        key = identity(sport, row, kickoff)
        if key[1] == key[2]:
            continue
        games.setdefault(key, {
            'home_team': row['home_team'], 'away_team': row['away_team'],
            'date': kickoff.isoformat(), 'league': row.get('competition') or SPORTS[sport]['label'],
            'status': str(row.get('status') or 'SCHEDULED').upper(),
            'home_score': None, 'away_score': None,
        })
    for row in results:
        kickoff, observed = timestamp(row.get('date')), timestamp(row.get('result_available_at'))
        scores = [row.get(key) for key in ('home_score', 'away_score')]
        if (row.get('league') != SPORTS[sport]['league'] or row.get('completed') is not True
                or row.get('date_precision') != 'TIMESTAMP' or kickoff is None
                or observed is None or not kickoff < observed <= now
                or not start <= kickoff.date() <= end
                or not row.get('home_team') or not row.get('away_team')
                or any(isinstance(score, bool) or not isinstance(score, (int, float))
                       or not math.isfinite(score) or score < 0 or not float(score).is_integer() for score in scores)):
            continue
        key = identity(sport, row, kickoff)
        if key[1] == key[2] or (sport != 'nfl' and scores[0] == scores[1]):
            continue
        finals[key].append(row)
    conflicts = 0
    for key, rows in finals.items():
        if len({(row['home_score'], row['away_score']) for row in rows}) != 1:
            games.pop(key, None)
            conflicts += 1
            continue
        row = rows[0]
        games[key] = {'home_team': row['home_team'], 'away_team': row['away_team'],
                      'date': timestamp(row['date']).isoformat(), 'league': SPORTS[sport]['label'],
                      'status': 'FINISHED', 'home_score': int(row['home_score']), 'away_score': int(row['away_score'])}
    items = [{**row, 'id': 'schedule:' + hashlib.sha256('|'.join(key).encode()).hexdigest()[:24],
              'sport': sport} for key, row in sorted(games.items(), key=lambda item: item[0][-1])]
    return {'sport': sport, 'items': items, 'start_date': start.isoformat(), 'end_date': end.isoformat(),
            'generated_at': now.isoformat(), 'excluded_conflicting_finals': conflicts,
            'policy': 'UTC dates. Retained schedules and verified final scores; not a live scoreboard.'}
