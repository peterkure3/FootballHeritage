"""Fit isolated Wyscout possession models and evaluate chronological rollouts."""
import argparse
import gzip
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import poisson

from etl.fetch_soccer_events import DEFAULT_ROOT, file_hash
from etl.soccer_event_dataset import load_match
from models.soccer_players import player_distributions, roster_scenario
from models.soccer_possessions import PossessionModel, STAT_NAMES, event_stats, summarize


def chronological_split(items: list[dict]) -> dict[str, list[dict]]:
    ordered = sorted(items, key=lambda m: (m['date'], m['match_id']))
    if len(ordered) < 20:
        raise ValueError('At least twenty valid games required')
    train_date, test_date = ordered[int(len(ordered) * .7)]['date'], ordered[int(len(ordered) * .85)]['date']
    return dict(train=[m for m in ordered if m['date'] < train_date],
                validation=[m for m in ordered if train_date <= m['date'] < test_date],
                test=[m for m in ordered if m['date'] >= test_date])


def actual_stats(record: dict) -> np.ndarray:
    sides = {int(k): 0 if v['side'] == 'home' else 1 for k, v in record['match']['teamsData'].items()}
    values = np.zeros((2, len(STAT_NAMES)), dtype=int)
    for event in record['events']:
        if event['period'] > 2:
            continue
        side = sides[event['team_id']]
        values[side] += event_stats(event)
        if event['own_goal']:
            values[1 - side, 0] += 1
    return values


def count_crps(samples: np.ndarray, observed: float) -> float:
    values = np.sort(np.asarray(samples, dtype=float))
    n = len(values)
    return float(np.mean(abs(values - observed)) - np.dot(2 * np.arange(n) - n + 1, values) / n ** 2)


def outcome_metrics(samples: np.ndarray, observed: np.ndarray) -> dict:
    difference = samples[:, 0, 0] - samples[:, 1, 0]
    counts = np.array([(difference > 0).sum(), (difference == 0).sum(), (difference < 0).sum()])
    probabilities = (counts + .5) / (len(samples) + 1.5)
    delta = observed[0, 0] - observed[1, 0]
    label = 0 if delta > 0 else 1 if delta == 0 else 2
    one_hot = np.eye(3)[label]
    return dict(probabilities=probabilities.tolist(), log_loss=float(-np.log(probabilities[label])),
                brier=float(np.sum((probabilities - one_hot) ** 2)),
                correct=int(np.argmax(probabilities) == label))


def fit_goal_baseline(records: Iterable[dict]) -> dict:
    goals, teams = [], {}
    for record in records:
        stats = actual_stats(record)[:, 0]
        goals.append(stats)
        for key, data in record['match']['teamsData'].items():
            side = 0 if data['side'] == 'home' else 1
            state = teams.setdefault(int(key), [0., 0., 0.])
            state[0] += stats[side]
            state[1] += stats[1 - side]
            state[2] += 1
    return dict(means=np.mean(goals, axis=0), teams=teams)


def baseline_rates(baseline: dict, home: int, away: int) -> np.ndarray:
    global_rate = np.mean(baseline['means'])
    factors = []
    for team in [home, away]:
        scored, conceded, games = baseline['teams'].get(team, [0., 0., 0.])
        factors.append(((scored + 5 * global_rate) / (games + 5) / global_rate,
                        (conceded + 5 * global_rate) / (games + 5) / global_rate))
    return baseline['means'] * [factors[0][0] * factors[1][1], factors[1][0] * factors[0][1]]


def evaluate(model: PossessionModel, dataset: Path, items: list[dict], baseline: dict,
             runs: int, seed: int) -> list[dict]:
    rows = []
    for index, item in enumerate(items):
        record = load_match(dataset, item)
        teams = {v['side']: int(k) for k, v in record['match']['teamsData'].items()}
        fixture_seed = seed + item['match_id']
        sample = model.simulate(teams['home'], teams['away'], item['date'], runs, fixture_seed)['samples']
        actual = actual_stats(record)
        # Smoothed empirical outcome probabilities avoid pretending rare outcomes impossible.
        outcome = outcome_metrics(sample, actual)
        rates = baseline_rates(baseline, teams['home'], teams['away'])
        axis = np.arange(60)
        matrix = poisson.pmf(axis, rates[0])[:, None] * poisson.pmf(axis, rates[1])[None, :]
        probs = np.array([np.tril(matrix, -1).sum(), np.trace(matrix), np.triu(matrix, 1).sum()])
        probs /= probs.sum()
        label = 0 if actual[0, 0] > actual[1, 0] else 1 if actual[0, 0] == actual[1, 0] else 2
        reference = np.random.default_rng(fixture_seed).poisson(rates, size=(runs, 2))
        stats = {}
        for stat_index, name in enumerate(STAT_NAMES):
            draws = sample[:, :, stat_index].sum(axis=1)
            observed = int(actual[:, stat_index].sum())
            low, high = np.quantile(draws, [.05, .95])
            stats[name] = dict(observed=observed, predicted_mean=float(draws.mean()),
                               crps=count_crps(draws, observed), covered_90=bool(low <= observed <= high),
                               interval_90=[float(low), float(high)])
        rows.append(dict(match_id=item['match_id'], kickoff=item['date'], runs=runs,
                         actual_goals=actual[:, 0].tolist(), outcome=outcome, stats=stats,
                         goal_baseline=dict(rates=rates.tolist(), probabilities=probs.tolist(),
                             log_loss=float(-np.log(max(1e-15, probs[label]))),
                             brier=float(np.sum((probs - np.eye(3)[label]) ** 2)),
                             total_goals_crps=count_crps(reference.sum(axis=1), int(actual[:, 0].sum())))))
        if (index + 1) % 20 == 0:
            print(f'Evaluated {index + 1}/{len(items)} fixtures', flush=True)
    return rows


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {'matches': 0}
    return dict(matches=len(rows),
                outcome={key: float(np.mean([r['outcome'][key] for r in rows]))
                         for key in ['log_loss', 'brier', 'correct']},
                goal_baseline={key: float(np.mean([r['goal_baseline'][key] for r in rows]))
                               for key in ['log_loss', 'brier', 'total_goals_crps']},
                stats={name: {key: float(np.mean([r['stats'][name][key] for r in rows]))
                              for key in ['observed', 'predicted_mean', 'crps', 'covered_90']}
                       for name in STAT_NAMES})


def save_model(model: PossessionModel, path: Path, metadata: dict) -> None:
    payload = dict(templates=model.templates, dates=model.training_dates,
                   half_lengths=model.half_lengths, sub_minutes=model.sub_minutes,
                   player_usage={str(k): v.tolist() for k, v in model.player_usage.items()}, metadata=metadata)
    path.write_bytes(gzip.compress(json.dumps(payload, separators=(',', ':')).encode('utf-8'),
                                   compresslevel=1, mtime=0))


def validate_players(record: dict, prediction: dict, scenarios: list[dict]) -> dict:
    observed = {pid: np.zeros(len(STAT_NAMES), dtype=int)
                for s in scenarios for pid in s['starters'] + s['bench']}
    missing = np.zeros(len(STAT_NAMES), dtype=int)
    for event in record['events']:
        if event['period'] <= 2:
            if event['player_id'] in observed:
                observed[event['player_id']] += event_stats(event)
            else:
                missing += event_stats(event)
    results = {}
    for j, stat in enumerate(STAT_NAMES[:6]):
        if missing[j]:
            results[stat] = dict(scored=False, reason='Observed actor identities incomplete',
                                 unattributed_observed_count=int(missing[j]))
            continue
        scores, covered = [], []
        for pid, counts in observed.items():
            forecast = prediction['players'][str(pid)][stat]
            # CRPS computed exactly from the empirical discrete PMF.
            support = np.asarray([int(x) for x in forecast['pmf']])
            probabilities = np.asarray(list(forecast['pmf'].values()))
            value = float(np.dot(probabilities, abs(support - counts[j])) - .5 *
                np.sum(probabilities[:, None] * probabilities[None, :] * abs(support[:, None] - support[None, :])))
            scores.append(value)
            covered.append(forecast['quantiles']['0.05'] <= counts[j] <= forecast['quantiles']['0.95'])
        results[stat] = dict(scored=True, mean_player_crps=float(np.mean(scores)), covered_90=float(np.mean(covered)))
    return dict(scope='one held-out fixture; roster includes zero-minute bench players',
                player_count=len(observed), metrics=results)


def read_model(path: Path) -> tuple[PossessionModel, dict]:
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        payload = json.load(handle)
    return PossessionModel(payload['templates'], payload['dates'], payload['half_lengths'],
                           {int(k): v for k, v in payload['player_usage'].items()}, payload['sub_minutes']), payload['metadata']


def run(dataset: Path, output: Path, competitions: list[str], runs: int, demo_runs: int,
        player_runs: int, seed: int, resume: bool = False) -> dict:
    if runs < 100 or demo_runs < 100 or not 0 < player_runs <= demo_runs:
        raise ValueError('At least 100 runs and 1..demo-runs player trajectories required')
    index = json.loads((dataset / 'index.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    (output / '.gitignore').write_text('*\n!.gitignore\n', encoding='utf-8')
    report = dict(kind='inactive soccer possession-bootstrap research baseline',
                  dataset_index_sha256=file_hash(dataset / 'index.json'), seed=seed,
                  runs_per_evaluation_fixture=runs, competitions={},
                  limitations=['Historical 2016/2017-18/2018 coverage; not current fixture forecasts',
                               'Each competition has independent chronological 70/15/15 splits',
                               'Empirical possession resampling with smoothed scoring reweighting',
                               'No red cards, tactical adaptation, injuries, extra time or shootouts modeled',
                               'Validation is reported, not used to tune the frozen baseline',
                               'Official roster IDs used as a confirmed-at-kickoff scenario; no archived lineup publication time'])
    available = sorted(set(m['competition'] for m in index['matches']))
    chosen_competitions = available if competitions == ['all'] else competitions
    if set(chosen_competitions) - set(available):
        raise ValueError('Unknown competition')
    demo_written = False
    for competition in chosen_competitions:
        accepted = [m for m in index['matches'] if m['competition'] == competition and not m['quarantine']]
        split = chronological_split(accepted)
        print(f'Fitting {competition}: ' + str({k: len(v) for k, v in split.items()}), flush=True)
        metadata = dict(competition=competition, dataset_sha256=report['dataset_index_sha256'],
                        training_ids=[m['match_id'] for m in split['train']],
                        split={key: [m['match_id'] for m in value] for key, value in split.items()},
                        training_max_kickoff=max(m['date'] for m in split['train']),
                        source='Wyscout public archive; Pappalardo et al. (2019)', license='CC BY 4.0')
        path = output / f'{competition}-model.json.gz'
        if resume and path.exists():
            model, saved_metadata = read_model(path)
            if saved_metadata != metadata:
                raise ValueError('Cached model metadata differs from this run')
        else:
            model = PossessionModel.fit(load_match(dataset, m) for m in split['train'])
            save_model(model, path, metadata)
        baseline = fit_goal_baseline(load_match(dataset, m) for m in split['train'])
        config = dict(model_sha256=file_hash(path), runs=runs, seed=seed, evaluation_version=1)
        evaluation_path = output / f'{competition}-evaluation.json'
        if resume and evaluation_path.exists():
            cached = json.loads(evaluation_path.read_text())
            if cached.get('config') != config:
                raise ValueError('Cached evaluation configuration differs from this run')
            evaluation = {key: cached[key] for key in ['validation', 'test']}
        else:
            evaluation = {name: evaluate(model, dataset, split[name], baseline, runs, seed)
                          for name in ['validation', 'test']}
            evaluation_path.write_text(json.dumps(dict(evaluation, config=config), indent=2), encoding='utf-8')
        report['competitions'][competition] = dict(split_sizes={k: len(v) for k, v in split.items()},
            training_max_kickoff=max(model.training_dates), possessions=len(model.templates),
            model_sha256=file_hash(path), metrics={k: aggregate(v) for k, v in evaluation.items()})
        # Prefer England for the named-player example; otherwise use the first requested competition.
        if not demo_written and (competition == 'England' or len(chosen_competitions) == 1):
            fixture = split['test'][0]
            record = load_match(dataset, fixture)
            players = json.loads((dataset / 'players.json').read_text())
            scenarios = roster_scenario(record['match'], players)
            result = model.simulate(scenarios[0]['team_id'], scenarios[1]['team_id'],
                                    fixture['date'], demo_runs, seed, player_runs)
            player_result = player_distributions(model, result['histories'], scenarios,
                                                 result['samples'][:player_runs], seed + 1)
            demo = dict(fixture_id=fixture['match_id'], label=record['match']['label'],
                        kickoff=fixture['date'], training_max_kickoff=max(model.training_dates),
                        team_distribution=summarize(result['samples']),
                        player_distribution=player_result,
                        player_validation=validate_players(record, player_result, scenarios),
                        players={str(pid): players.get(str(pid), {'name': f'Unknown Wyscout player {pid}',
                                                                'role': s['roles'][pid]}) for s in scenarios
                                 for pid in s['starters'] + s['bench']},
                        actual_stats=actual_stats(record).tolist(), seed=seed)
            (output / 'demo.json').write_text(json.dumps(demo, indent=2), encoding='utf-8')
            # Verify the serialized model gives the identical seeded rollout.
            restored, _ = read_model(path)
            replay = restored.simulate(scenarios[0]['team_id'], scenarios[1]['team_id'],
                                      fixture['date'], demo_runs, seed, player_runs)
            if not np.array_equal(result['samples'], replay['samples']) or result['histories'] != replay['histories']:
                raise RuntimeError('Saved model replay differs')
            report['demo'] = dict(match_id=fixture['match_id'], team_runs=demo_runs,
                                  player_runs=player_runs, saved_model_replay='identical',
                                  trajectory_events=len(player_result['trace']),
                                  player_validation=demo['player_validation'])
            demo_written = True
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_ROOT / 'normalized')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_ROOT / 'simulation-baseline')
    parser.add_argument('--competitions', nargs='+', default=['all'])
    parser.add_argument('--runs', type=int, default=1000)
    parser.add_argument('--demo-runs', type=int, default=10000)
    parser.add_argument('--player-runs', type=int, default=250)
    parser.add_argument('--seed', type=int, default=20261022)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    run(args.dataset, args.output_dir, args.competitions, args.runs, args.demo_runs, args.player_runs, args.seed, args.resume)


if __name__ == '__main__':
    main()
