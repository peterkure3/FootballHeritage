"""Completion audit over source bytes, dataset, all splits and forecast artifacts."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.fetch_soccer_events import DEFAULT_ROOT, file_hash
from etl.soccer_event_dataset import load_match
from models.run_soccer_simulation import actual_stats, read_model
from models.soccer_possessions import kickoff


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-players', action='store_true')
    args = parser.parse_args()
    raw, dataset = DEFAULT_ROOT, DEFAULT_ROOT / 'normalized'
    output = raw / 'simulation-baseline'
    source = json.loads((raw / 'manifest.json').read_text())
    for name, capture in source['captures'].items():
        assert file_hash(raw / name) == capture['sha256'], name
        if capture.get('provider_md5'):
            assert file_hash(raw / name, 'md5') == capture['provider_md5'], name
    inventory = json.loads((dataset / 'index.json').read_text())
    assert len(inventory['matches']) == 1941
    assert inventory['total_events'] == 3251294
    assert not inventory['missing_event_matches']
    items = {m['match_id']: m for m in inventory['matches']}
    assert len(items) == 1941
    events, accepted = 0, 0
    for item in inventory['matches']:
        record = load_match(dataset, item)
        assert len(record['events']) == item['events']
        assert record['quarantine'] == item['quarantine']
        events += len(record['events'])
        if not record['quarantine']:
            observed = actual_stats(record)
            score = {t['side']: t['score'] for t in record['match']['teamsData'].values()}
            assert observed[:, 0].tolist() == [score['home'], score['away']]
            accepted += 1
    assert accepted == inventory['accepted'] == 1930
    report = json.loads((output / 'report.json').read_text())
    assert len(report['competitions']) == 7
    evidence = dict(source_hashes=len(source['captures']), dataset_events=events,
                    accepted_matches=accepted, quarantine_matches=1941 - accepted,
                    competitions={}, validation_fixtures=0, test_fixtures=0,
                    player_fixtures=0, training_fixtures=0)
    for competition, summary in report['competitions'].items():
        model_path = output / f'{competition}-model.json.gz'
        assert file_hash(model_path) == summary['model_sha256']
        model, metadata = read_model(model_path)
        split = {k: set(v) for k, v in metadata['split'].items()}
        assert not (split['train'] & split['validation'] or split['train'] & split['test'] or split['validation'] & split['test'])
        assert set.union(*split.values()) == {m['match_id'] for m in inventory['matches']
                                            if m['competition'] == competition and not m['quarantine']}
        cutoff = max(kickoff(items[mid]['date']) for mid in split['train'])
        assert cutoff < min(kickoff(items[mid]['date']) for mid in split['validation'])
        assert max(kickoff(items[mid]['date']) for mid in split['validation']) < min(kickoff(items[mid]['date']) for mid in split['test'])
        assert {p['match_id'] for p in model.templates} <= split['train']
        assert all(p['duration'] > 0 for p in model.templates)
        evaluations = json.loads((output / f'{competition}-evaluation.json').read_text())
        assert evaluations['config']['model_sha256'] == summary['model_sha256']
        for name in ['validation', 'test']:
            rows = evaluations[name]
            assert len(rows) == len(split[name])
            assert {r['match_id'] for r in rows} == split[name]
            assert all(r['runs'] == 1000 and abs(sum(r['outcome']['probabilities']) - 1) < 1e-12 for r in rows)
            evidence[f'{name}_fixtures'] += len(rows)
        evidence['training_fixtures'] += len(split['train'])
        player_count = 0
        for mid in split['test']:
            path = output / f'player-evaluation/{mid}.json'
            if not path.exists():
                continue
            player = json.loads(path.read_text())
            assert player['config']['model_sha256'] == summary['model_sha256']
            assert player['config']['runs'] == 100
            assert all(abs(sum(stat['pmf'].values()) - 1) < 1e-12
                       for stats in player['players'].values() for stat in stats.values())
            player_count += 1
        if args.require_players:
            assert player_count == len(split['test']), (competition, player_count, len(split['test']))
        evidence['player_fixtures'] += player_count
        evidence['competitions'][competition] = dict(
            split={k: len(v) for k, v in split.items()}, player_fixtures=player_count,
            training_cutoff=cutoff.isoformat(), donor_match_ids='all in training split')
    convergence = json.loads((output / 'convergence.json').read_text())
    assert convergence['runs'] == 50000
    assert abs(sum(convergence['probabilities']['outcome'].values()) - 1) < 1e-12
    batch = json.loads((output / 'batch-verification.json').read_text())
    assert batch[0]['teams']['runs'] == 200 and batch[0]['players']['runs'] == 20
    assert report['demo']['saved_model_replay'] == 'identical'
    evidence['monte_carlo_rollouts_validation_and_test'] = (evidence['validation_fixtures'] + evidence['test_fixtures']) * 1000
    evidence['larger_example_runs'] = convergence['runs']
    evidence['all_player_evaluations_complete'] = evidence['player_fixtures'] == evidence['test_fixtures']
    evidence['source_code_sha256'] = {name: file_hash(ROOT / name) for name in [
        'pipeline/etl/fetch_soccer_events.py', 'pipeline/etl/soccer_event_dataset.py',
        'pipeline/models/soccer_possessions.py', 'pipeline/models/soccer_players.py',
        'pipeline/models/run_soccer_simulation.py', 'pipeline/models/evaluate_soccer_players.py',
        'pipeline/scripts/simulate_soccer_fixtures.py', 'pipeline/tests/test_soccer_simulation.py']}
    evidence['runtime_versions'] = dict(python=sys.version, numpy=version('numpy'), scipy=version('scipy'))
    destination = Path(__file__).with_name('soccer-baseline-certification-20261022.json')
    destination.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
