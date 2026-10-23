"""Evaluate player distributions on each competition's chronological test fixtures."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from etl.fetch_soccer_events import DEFAULT_ROOT, file_hash
from etl.soccer_event_dataset import load_match
from models.run_soccer_simulation import read_model, validate_players
from models.soccer_players import player_distributions, roster_scenario


def evaluate(dataset: Path, model_root: Path, competitions: list[str], runs: int, seed: int) -> dict:
    if runs < 100:
        raise ValueError('At least 100 player trajectories per fixture required')
    inventory = json.loads((dataset / 'index.json').read_text())
    items = {item['match_id']: item for item in inventory['matches']}
    players = json.loads((dataset / 'players.json').read_text())
    selected = sorted(inventory['competitions']) if competitions == ['all'] else competitions
    destination = model_root / 'player-evaluation'
    destination.mkdir(exist_ok=True)
    summaries = {}
    for competition in selected:
        model_path = model_root / f'{competition}-model.json.gz'
        model, metadata = read_model(model_path)
        model_hash = file_hash(model_path)
        results, excluded = [], []
        for mid in metadata['split']['test']:
            target = destination / f'{mid}.json'
            config = dict(model_sha256=model_hash, runs=runs, seed=seed + mid,
                          dataset_index_sha256=file_hash(dataset / 'index.json'))
            if target.exists():
                cached = json.loads(target.read_text())
                if cached['config'] != config:
                    raise ValueError('Player evaluation cache configuration differs')
                results.append(cached)
                continue
            record = load_match(dataset, items[mid])
            try:
                scenarios = roster_scenario(record['match'], players)
            except ValueError as exc:
                excluded.append(dict(match_id=mid, reason=str(exc)))
                continue
            rollout = model.simulate(scenarios[0]['team_id'], scenarios[1]['team_id'],
                                     items[mid]['date'], runs, seed + mid, runs)
            distribution = player_distributions(model, rollout['histories'], scenarios,
                                                rollout['samples'], seed + mid + 1)
            validation = validate_players(record, distribution, scenarios)
            cached = dict(match_id=mid, kickoff=items[mid]['date'], config=config,
                          validation=validation, players=distribution['players'],
                          assumptions=distribution['scenario_assumptions'])
            temp = target.with_suffix('.tmp')
            temp.write_text(json.dumps(cached, separators=(',', ':')), encoding='utf-8')
            temp.replace(target)
            results.append(cached)
            if len(results) % 10 == 0:
                print(f'Player evaluation {competition}: {len(results)}/{len(metadata["split"]["test"])}', flush=True)
        metrics = defaultdict(list)
        skipped = defaultdict(int)
        for result in results:
            for stat, value in result['validation']['metrics'].items():
                if value.get('scored'):
                    metrics[stat].append(value)
                else:
                    skipped[stat] += 1
        summary = dict(fixtures=len(results), excluded=excluded, trajectories_per_fixture=runs,
                        roster_scenario='Confirmed-at-kickoff IDs; publication time unverified',
                        metrics={stat: dict(scored_fixtures=len(values),
                            mean_player_crps=float(np.mean([v['mean_player_crps'] for v in values])),
                            covered_90=float(np.mean([v['covered_90'] for v in values])))
                            for stat, values in metrics.items()},
                        stats_not_scored_due_to_missing_actors=dict(skipped))
        summaries[competition] = summary
        (model_root / f'{competition}-player-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    report = dict(competitions=summaries, seed=seed,
                  limitations=['One historical season/tournament; no player model promotion',
                               'Metrics average all roster players, including zero-minute bench players',
                               'Incomplete observed actor totals are excluded per fixture/stat',
                               'Intervals include Monte Carlo uncertainty; parameter uncertainty not modeled'])
    (model_root / 'player-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_ROOT / 'normalized')
    parser.add_argument('--model-root', type=Path, default=DEFAULT_ROOT / 'simulation-baseline')
    parser.add_argument('--competitions', nargs='+', default=['all'])
    parser.add_argument('--runs', type=int, default=100)
    parser.add_argument('--seed', type=int, default=20261024)
    args = parser.parse_args()
    evaluate(args.dataset, args.model_root, args.competitions, args.runs, args.seed)


if __name__ == '__main__':
    main()
