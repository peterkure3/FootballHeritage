"""Run an inactive soccer event model for explicit fixture/lineup scenarios.

Input JSON is a list of {fixture_id, kickoff, home_team_id, away_team_id,
lineups?}. Optional lineups contains two {team_id, starters, bench, roles} objects
in home/away order. IDs and role-map keys must be Wyscout provider IDs.
"""
import argparse
import json
from pathlib import Path

from models.run_soccer_simulation import read_model
from models.soccer_players import player_distributions
from models.soccer_possessions import summarize


def forecast(model_path: Path, fixture_path: Path, output: Path, runs: int,
             player_runs: int, seed: int) -> list[dict]:
    model, metadata = read_model(model_path)
    fixtures = json.loads(fixture_path.read_text(encoding='utf-8'))
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('Nonempty fixture array required')
    if runs < 100 or not 0 <= player_runs <= runs:
        raise ValueError('At least 100 runs; player-runs must be 0..runs')
    identities = [str(f['fixture_id']) for f in fixtures]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate fixture IDs')
    result = []
    for i, fixture in enumerate(fixtures):
        home, away = int(fixture['home_team_id']), int(fixture['away_team_id'])
        if home not in model.n_attack or away not in model.n_attack:
            raise ValueError('Both teams need event history in this competition model')
        roster = fixture.get('lineups')
        count = player_runs if roster else 0
        if roster:
            if len(roster) != 2 or [int(s['team_id']) for s in roster] != [home, away]:
                raise ValueError('Lineup sides must match fixture native IDs')
            for scenario in roster:
                scenario['roles'] = {int(k): v for k, v in scenario['roles'].items()}
                ids = scenario['starters'] + scenario['bench']
                if len(scenario['starters']) != 11 or len(ids) != len(set(ids)):
                    raise ValueError('Need eleven starters and a disjoint bench')
                if set(ids) - scenario['roles'].keys():
                    raise ValueError('Missing player roles')
                if sum(scenario['roles'][p] == 'GK' for p in scenario['starters']) != 1:
                    raise ValueError('Exactly one starting goalkeeper required')
        rollout = model.simulate(home, away, fixture['kickoff'], runs, seed + i, count)
        item = dict(fixture_id=fixture['fixture_id'], kickoff=fixture['kickoff'],
                    model_metadata=metadata, status='historical research model; not production',
                    seed=seed + i, teams=summarize(rollout['samples']))
        if count:
            item['players'] = player_distributions(model, rollout['histories'], roster,
                                                   rollout['samples'][:count], seed + i + 100000)
        result.append(item)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=10000)
    parser.add_argument('--player-runs', type=int, default=250)
    parser.add_argument('--seed', type=int, default=20261022)
    args = parser.parse_args()
    forecast(args.model, args.fixtures, args.output, args.runs, args.player_runs, args.seed)


if __name__ == '__main__':
    main()
