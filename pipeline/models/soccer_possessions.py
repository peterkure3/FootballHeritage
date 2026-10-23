"""Empirical possession templates fitted exclusively to earlier validated games.

This baseline resamples action sequences, not final scorelines. Coordinates stay
in Wyscout's actor-team attacking direction on a 0..100 grid.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

import numpy as np

from etl.soccer_event_dataset import substitutions

CONTROLLED = {'Pass', 'Shot', 'Free Kick', 'Others on the ball'}
STAT_NAMES = ['goals', 'shots', 'shots_on_target', 'passes', 'completed_passes',
              'corners', 'own_goals_conceded']


def kickoff(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def event_stats(event: dict) -> list[int]:
    shot = int(event['shot'])
    goal = int(event['goal'] and not event['own_goal'])
    # Wyscout accurate shot tag 1801 includes goals and saved shots.
    on_target = int(bool(shot and (event['accurate'] or goal)))
    passing = int(event['kind'] == 'Pass' or (event['kind'] == 'Free Kick' and not shot))
    return [goal, shot, on_target, passing, passing * int(event['accurate']),
            int(event['subtype'] == 'Corner'), int(event['own_goal'])]


def zone(event: dict) -> int:
    if not event['positions']:
        return 1
    return min(2, int(float(event['positions'][0]['x']) // (100 / 3)))


def possessions(record: dict) -> list[dict]:
    """Paired duels are excluded from control decisions, retained in source data."""
    match = record['match']
    sides = {int(k): v['side'] for k, v in match['teamsData'].items()}
    result = []
    for half in [1, 2]:
        source = [e for e in record['events'] if e['period'] == half]
        events = [e for e in source if e['kind'] in CONTROLLED or e['own_goal']]
        if not events:
            continue
        groups, current = [], []
        for event in events:
            if current and (current[-1]['team_id'] != event['team_id'] or
                            current[-1]['goal'] or current[-1]['own_goal']):
                groups.append(current)
                current = []
            current.append(event)
        groups.append(current)
        for index, group in enumerate(groups):
            first = group[0]
            begin = 0.0 if index == 0 else first['seconds']
            end = groups[index + 1][0]['seconds'] if index + 1 < len(groups) else max(e['seconds'] for e in source) + .01
            end = max(begin + .001, end)
            team = first['team_id']
            margin = first['home_goals_before'] - first['away_goals_before']
            if sides[team] == 'away':
                margin = -margin
            actions = [dict(offset=max(0., e['seconds'] - begin), stats=event_stats(e),
                            role=e['role'], player_id=e['player_id'], kind=e['kind'],
                            subtype=e['subtype'], positions=e['positions'],
                            source_event_id=e['event_id']) for e in group]
            next_group = groups[index + 1] if index + 1 < len(groups) else None
            result.append(dict(match_id=match['wyId'], team_id=team,
                               venue=sides[team],
                               opponent_id=next(t for t in sides if t != team),
                               half=half, margin=int(np.sign(margin)), zone=zone(first),
                               duration=end - begin, actions=actions,
                               right_censored=next_group is None,
                               stats=np.sum([a['stats'] for a in actions], axis=0).tolist(),
                               next_zone=zone(next_group[0]) if next_group else 1,
                               switch=bool(next_group and next_group[0]['team_id'] != team)))
    return result


class PossessionModel:
    """Transparent conditional bootstrap; a research baseline, not promoted."""

    def __init__(self, templates: list[dict], dates: list[str], half_lengths: list[list[float]],
                 player_usage: dict, sub_minutes: list[float]) -> None:
        if not templates or not dates:
            raise ValueError('Nonempty training games and templates required')
        self.templates, self.training_dates = templates, dates
        self.training_cutoff = max(kickoff(date) for date in dates)
        self.half_lengths = half_lengths
        self.player_usage, self.sub_minutes = player_usage, sub_minutes
        self.stats = np.asarray([p['stats'] for p in templates], dtype=np.int32)
        self.durations = np.asarray([p['duration'] for p in templates])
        self.next_zones = np.asarray([p['next_zone'] for p in templates])
        self.switches = np.asarray([p['switch'] for p in templates])
        self.pool = {}
        self.attack, self.defense, self.n_attack, self.n_defense = Counter(), Counter(), Counter(), Counter()
        for i, p in enumerate(templates):
            self.pool.setdefault((p['half'], p['margin'], p['zone']), []).append(i)
            self.attack[p['team_id']] += p['stats'][0]
            self.defense[p['opponent_id']] += p['stats'][0]
            self.n_attack[p['team_id']] += 1
            self.n_defense[p['opponent_id']] += 1
        self.global_rate = max(1e-5, self.stats[:, 0].mean())

    @classmethod
    def fit(cls, records: Iterable[dict]) -> 'PossessionModel':
        templates, lengths, minutes, dates = [], [[], []], [], []
        usage = defaultdict(lambda: np.zeros(3, dtype=float))
        exposure = Counter()
        for record in records:
            if record['quarantine']:
                raise ValueError('Quarantined matches cannot train the model')
            # The final possession has no observed next control boundary. Treat
            # its duration as censored rather than repeatedly sampling a near-zero tail.
            templates.extend(p for p in possessions(record) if not p['right_censored'])
            dates.append(record['match']['dateutc'])
            for half in [1, 2]:
                lengths[half - 1].append(max(e['seconds'] for e in record['events'] if e['period'] == half) + .01)
            for event in record['events']:
                if event['period'] <= 2 and event['player_id']:
                    usage[event['player_id']] += [int(event['shot']), int(event['kind'] == 'Pass'), 1]
            for team in record['match']['teamsData'].values():
                formation = team['formation']
                changes = substitutions(formation)
                on = {p['playerId']: 0. for p in formation['lineup']}
                off = {p['playerId']: 90. for p in formation['lineup']}
                for sub in changes:
                    on[sub['playerIn']] = min(90., float(sub['minute']))
                    off[sub['playerIn']] = 90.
                    off[sub['playerOut']] = min(90., float(sub['minute']))
                for pid, start in on.items():
                    exposure[pid] += max(0., off[pid] - start) / 90
                minutes.extend(float(s['minute']) for s in changes
                               if 45 <= float(s['minute']) <= 90)
        usage = {pid: values / max(exposure[pid], 1 / 90) for pid, values in usage.items()}
        return cls(templates, dates, lengths, dict(usage), minutes)

    def sampler(self, half: int, margin: int, location: int, team: int, opponent: int,
                strengths: bool = True, home_side: bool | None = None) -> tuple[np.ndarray, np.ndarray]:
        indices = self.pool.get((half, margin, location))
        if not indices:
            indices = [i for i, p in enumerate(self.templates) if p['half'] == half]
        if home_side is not None:
            venue = 'home' if home_side else 'away'
            indices = [i for i in indices if self.templates[i].get('venue') == venue] or indices
        indices = np.asarray(indices)
        weight = np.ones(len(indices), dtype=float)
        if strengths:
            prior = 300
            attack = (self.attack[team] + prior * self.global_rate) / (self.n_attack[team] + prior)
            defense = (self.defense[opponent] + prior * self.global_rate) / (self.n_defense[opponent] + prior)
            ratio = np.clip(attack * defense / self.global_rate ** 2, .25, 4)
            weight *= np.power(ratio, self.stats[indices, 0])
        return indices, np.cumsum(weight / weight.sum())

    def simulate(self, home: int, away: int, date: str, runs: int = 10000,
                 seed: int = 22, player_runs: int = 0, strengths: bool = True) -> dict:
        if home == away or runs < 1 or player_runs < 0 or player_runs > runs:
            raise ValueError('Invalid fixture or simulation counts')
        if kickoff(date) <= self.training_cutoff:
            raise ValueError('Forecast kickoff must follow all training matches')
        rng = np.random.default_rng(seed)
        scores = np.zeros((runs, 2, len(STAT_NAMES)), dtype=np.int32)
        histories = [[] for _ in range(player_runs)]
        cache = {}
        steps = 0
        first_kickoff = rng.integers(0, 2, size=runs)
        for half in [1, 2]:
            clock = np.zeros(runs)
            limit = rng.choice(self.half_lengths[half - 1], size=runs)
            owner = first_kickoff.copy() if half == 1 else 1 - first_kickoff
            location = np.ones(runs, dtype=int)
            while np.any(clock < limit):
                active = np.flatnonzero(clock < limit)
                if steps > 20000:
                    raise RuntimeError('Nonterminating possession rollout')
                steps += 1
                chosen = np.empty(len(active), dtype=int)
                own_score = scores[active, owner[active], 0]
                other_score = scores[active, 1 - owner[active], 0]
                margins = np.sign(own_score - other_score)
                for side in [0, 1]:
                    for margin in [-1, 0, 1]:
                        for area in [0, 1, 2]:
                            mask = (owner[active] == side) & (margins == margin) & (location[active] == area)
                            if not np.any(mask):
                                continue
                            key = (half, margin, area, side)
                            if key not in cache:
                                cache[key] = self.sampler(half, margin, area,
                                    [home, away][side], [away, home][side], strengths, side == 0)
                            pool, cdf = cache[key]
                            chosen[mask] = pool[np.minimum(len(pool) - 1, np.searchsorted(cdf, rng.random(mask.sum())))]
                increments = self.stats[chosen].copy()
                remaining = limit[active] - clock[active]
                crossing = np.flatnonzero(self.durations[chosen] > remaining)
                for pos in crossing:
                    acts = self.templates[chosen[pos]]['actions']
                    prefix = [a['stats'] for a in acts if a['offset'] < remaining[pos]]
                    increments[pos] = np.sum(prefix, axis=0) if prefix else 0
                owners = owner[active].copy()
                scores[active, owners] += increments
                scores[active, 1 - owners, 0] += increments[:, 6]
                for pos in np.flatnonzero(active < player_runs):
                    run = active[pos]
                    histories[run].append((int(chosen[pos]), half, float(clock[run]),
                                           float(remaining[pos]), int(owners[pos])))
                goals = increments[:, 0] + increments[:, 6] > 0
                # The side conceding restarts. For an own goal that is the
                # current actor's team, so possession must remain on that side.
                switching = np.where(increments[:, 6] > 0, False,
                                     self.switches[chosen] | (increments[:, 0] > 0))
                owner[active] = np.where(switching, 1 - owners, owners)
                location[active] = np.where(goals, 1, self.next_zones[chosen])
                clock[active] += self.durations[chosen]
        if np.any(scores[:, :, 0] > scores[:, :, 2] + scores[:, ::-1, 6]):
            raise RuntimeError('Goal / shots-on-target invariant failed')
        return {'samples': scores, 'histories': histories, 'seed': seed, 'runs': runs}


def distribution(values: np.ndarray) -> dict:
    values = np.asarray(values)
    counts = Counter(int(v) for v in values)
    return dict(mean=float(values.mean()), std=float(values.std()),
                quantiles={str(q): float(np.quantile(values, q)) for q in [.05, .25, .5, .75, .95]},
                pmf={str(k): v / len(values) for k, v in sorted(counts.items())})


def summarize(samples: np.ndarray) -> dict:
    goals = samples[:, :, 0]
    difference, total = goals[:, 0] - goals[:, 1], goals.sum(axis=1)
    counts = Counter(map(tuple, goals.tolist()))
    return dict(runs=len(samples), outcome={
        'home': float(np.mean(difference > 0)), 'draw': float(np.mean(difference == 0)),
        'away': float(np.mean(difference < 0))},
        scorelines={f'{h}-{a}': n / len(samples) for (h, a), n in sorted(counts.items())},
        goal_difference=distribution(difference), total_goals=distribution(total),
        both_teams_score=float(np.mean((goals > 0).all(axis=1))),
        over_2_5=float(np.mean(total > 2.5)),
        team_stats={side: {stat: distribution(samples[:, i, j]) for j, stat in enumerate(STAT_NAMES)}
                    for i, side in enumerate(['home', 'away'])},
        monte_carlo_95_half_width_max=1.96 * .5 / np.sqrt(len(samples)))
