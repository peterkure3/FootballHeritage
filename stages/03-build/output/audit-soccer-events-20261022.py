"""Write a compact source/quality/model evidence artifact; no production writes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.fetch_soccer_events import DEFAULT_ROOT
from etl.soccer_event_dataset import load_match
from models.soccer_possessions import CONTROLLED


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--resume-england', action='store_true')
    args = parser.parse_args()
    dataset = DEFAULT_ROOT / 'normalized'
    if args.resume_england:
        from etl.fetch_soccer_events import file_hash
        from models.run_soccer_simulation import actual_stats, outcome_metrics, read_model
        target = DEFAULT_ROOT / 'simulation-baseline'
        model_path = target / 'England-model.json.gz'
        evaluation_path = target / 'England-evaluation.json'
        cached = json.loads(evaluation_path.read_text())
        row = cached['validation'][0]
        inventory = json.loads((dataset / 'index.json').read_text())
        item = next(m for m in inventory['matches'] if m['match_id'] == row['match_id'])
        record = load_match(dataset, item)
        teams = {t['side']: t['teamId'] for t in record['match']['teamsData'].values()}
        model, _ = read_model(model_path)
        samples = model.simulate(teams['home'], teams['away'], item['date'], 1000,
                                 20261022 + item['match_id'])['samples']
        assert outcome_metrics(samples, actual_stats(record)) == row['outcome']
        for j, stat in enumerate(row['stats']):
            assert float(samples[:, :, j].sum(axis=1).mean()) == row['stats'][stat]['predicted_mean']
        cached['config'] = dict(model_sha256=file_hash(model_path), runs=1000,
                                seed=20261022, evaluation_version=1)
        evaluation_path.write_text(json.dumps(cached, indent=2))
        print('Existing England evaluation reproduced; resume metadata recorded', flush=True)
        return
    index = json.loads((dataset / 'index.json').read_text())
    captures = json.loads((DEFAULT_ROOT / 'manifest.json').read_text())
    path = dataset / 'actor-audit.json'
    if not path.exists():
        counts, missing, controlled = Counter(), Counter(), Counter()
        for item in index['matches']:
            record = load_match(dataset, item)
            for event in record['events']:
                counts[event['kind']] += 1
                if not event['player_id']:
                    missing[event['kind']] += 1
                    if event['kind'] in CONTROLLED:
                        controlled[event['kind']] += 1
        path.write_text(json.dumps(dict(event_types=dict(counts), missing_actor_by_type=dict(missing),
                                        missing_controlled_actor=dict(controlled)), indent=2))
    audit = json.loads(path.read_text())
    diagnostics = Counter()
    for match in index['matches']:
        diagnostics.update(match['diagnostics'])
    evidence = dict(dataset={k: v for k, v in index.items() if k != 'matches'},
                    diagnostics=dict(diagnostics), actor_audit=audit,
                    quarantined=[m for m in index['matches'] if m['quarantine']],
                    sources={name: {k: v for k, v in capture.items() if k != 'final_url'}
                             for name, capture in captures['captures'].items()})
    report = DEFAULT_ROOT / 'simulation-baseline/report.json'
    if not args.audit_only and report.exists():
        evidence['simulation'] = json.loads(report.read_text())
        player_report = DEFAULT_ROOT / 'simulation-baseline/player-report.json'
        if player_report.exists():
            evidence['player_evaluation'] = json.loads(player_report.read_text())
    destination = Path(__file__).with_name('soccer-events-evidence-20261022.json')
    destination.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(dict(events=index['total_events'], matches=len(index['matches']),
                         accepted=index['accepted'], actor_audit=audit,
                         diagnostics=dict(diagnostics)), indent=2))


if __name__ == '__main__':
    main()
