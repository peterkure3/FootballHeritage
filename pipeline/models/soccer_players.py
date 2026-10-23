"""Assign actors to sampled event trajectories under pre-kickoff roster scenarios."""
import numpy as np

from models.soccer_possessions import PossessionModel, STAT_NAMES, distribution


def roster_scenario(match: dict, players: dict) -> list[dict]:
    """Read IDs only; never use held-out goal counts, cards or substitutions."""
    result = []
    for side in ['home', 'away']:
        team = next(t for t in match['teamsData'].values() if t['side'] == side)
        formation = team['formation']
        starters = [p['playerId'] for p in formation['lineup']]
        bench = [p['playerId'] for p in formation.get('bench', [])]
        if len(starters) != 11 or len(set(starters + bench)) != len(starters + bench):
            raise ValueError('Need eleven unique starters and a disjoint bench')
        roles = {pid: players.get(str(pid), {}).get('role', 'UNK') for pid in starters + bench}
        if sum(roles[pid] == 'GK' for pid in starters) != 1:
            raise ValueError('Exactly one starting goalkeeper required')
        result.append(dict(team_id=team['teamId'], starters=starters, bench=bench, roles=roles))
    return result


def sampled_intervals(scenario: dict, minutes: list[float], rng: np.random.Generator) -> dict:
    """Baseline: up to three outfield replacements; no observed future substitutions."""
    intervals = {pid: [0., float('inf')] for pid in scenario['starters']}
    eligible = [pid for pid in scenario['starters'] if scenario['roles'][pid] != 'GK']
    bench = [pid for pid in scenario['bench'] if scenario['roles'][pid] != 'GK']
    if not minutes:
        return intervals
    count = min(3, len(eligible), len(bench))
    times = sorted(rng.choice(minutes, size=count).tolist())
    for time in times:
        outgoing = eligible.pop(int(rng.integers(len(eligible))))
        same_role = [pid for pid in bench if scenario['roles'][pid] == scenario['roles'][outgoing]]
        incoming = (same_role or bench)[int(rng.integers(len(same_role or bench)))]
        bench.remove(incoming)
        intervals[outgoing][1] = time
        intervals[incoming] = [time, float('inf')]
    return intervals


def player_distributions(model: PossessionModel, histories: list[list], scenarios: list[dict],
                         expected_samples: np.ndarray, seed: int) -> dict:
    if not histories:
        raise ValueError('At least one player trajectory required')
    rng = np.random.default_rng(seed)
    all_ids = sorted(pid for s in scenarios for pid in s['starters'] + s['bench'])
    if len(set(all_ids)) != len(all_ids):
        raise ValueError('A player cannot appear on both teams')
    lookup = {pid: i for i, pid in enumerate(all_ids)}
    # Last column is goalkeeper saves, derived from the opponent's non-goal SOT.
    stats = np.zeros((len(histories), len(all_ids), len(STAT_NAMES) + 1), dtype=np.int32)
    trace = []
    for run, history in enumerate(histories):
        intervals = [sampled_intervals(s, model.sub_minutes, rng) for s in scenarios]
        actor_cache = {}
        for tidx, half, begin, remaining, side in history:
            template = model.templates[tidx]
            for action in template['actions']:
                if action['offset'] >= remaining:
                    continue
                minute = (45 if half == 2 else 0) + (begin + action['offset']) / 60
                active = tuple(pid for pid, (start, end) in intervals[side].items() if start <= minute < end)
                category = 0 if action['stats'][1] else 1 if action['stats'][3] else 2
                key = (side, active, action['role'], category)
                if key not in actor_cache:
                    scenario = scenarios[side]
                    eligible = [p for p in active if scenario['roles'][p] == action['role']]
                    if not eligible:
                        eligible = [p for p in active if scenario['roles'][p] != 'GK'] or list(active)
                    prior = [1., 10., 20.][category]
                    weights = np.asarray([model.player_usage.get(p, [0., 0., 0.])[category] + prior for p in eligible])
                    actor_cache[key] = eligible, np.cumsum(weights / weights.sum())
                eligible, cdf = actor_cache[key]
                actor = eligible[min(len(eligible) - 1, int(np.searchsorted(cdf, rng.random())))]
                stats[run, lookup[actor], :len(STAT_NAMES)] += action['stats']
                saves = action['stats'][2] - action['stats'][0]
                if saves:
                    keepers = [pid for pid, (start, end) in intervals[1 - side].items()
                               if start <= minute < end and scenarios[1 - side]['roles'][pid] == 'GK']
                    if len(keepers) != 1:
                        raise ValueError('Active goalkeeper missing')
                    stats[run, lookup[keepers[0]], -1] += saves
                if run == 0:
                    trace.append(dict(half=half, seconds=begin + action['offset'],
                                      team_id=scenarios[side]['team_id'], player_id=actor,
                                      kind=action['kind'], subtype=action['subtype'],
                                      positions=action['positions'], stats=action['stats'],
                                      donor_match_id=template['match_id'],
                                      donor_event_id=action['source_event_id']))
        # Assert sample-wise consistency, including own goals credited to opponents.
        for side, scenario in enumerate(scenarios):
            team_players = [lookup[p] for p in scenario['starters'] + scenario['bench']]
            aggregate = stats[run, team_players, :len(STAT_NAMES)].sum(axis=0)
            expected = expected_samples[run, side].copy()
            expected[0] -= expected_samples[run, 1 - side, 6]
            if not np.array_equal(aggregate, expected):
                raise RuntimeError('Player / team event aggregation mismatch')
    return dict(runs=len(histories), stat_definitions=STAT_NAMES + ['goalkeeper_saves'],
                players={str(pid): {name: distribution(stats[:, i, j])
                         for j, name in enumerate(STAT_NAMES + ['goalkeeper_saves'])}
                         for i, pid in enumerate(all_ids)},
                trace=trace, scenario_assumptions=[
                    'Starting XI and bench treated as known at kickoff',
                    'Up to three sampled outfield substitutions at training-derived times',
                    'No red cards, injuries, tactical formation changes or extra time modeled',
                    'Role-conditioned actor assignment uses earlier player event counts with smoothing',
                    'SOT means accurate-tagged shot or goal; corners and passing use provider definitions'])
