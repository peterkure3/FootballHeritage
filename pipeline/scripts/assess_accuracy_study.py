"""Deduplicate frozen forecast batches and reassess their captured result evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from scripts.evaluate_accuracy_shadow import assess


def read_verified(path: Path, expected: str) -> dict:
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch: {path}')
    return json.loads(payload)


def combine(trials: list[dict], contract: list[str] | None = None) -> tuple[dict, int]:
    if not trials:
        raise ValueError('No frozen forecast batches')
    contract = contract or ['model_hashes', 'alias_map', 'classes', 'policy']
    reference = {key: trials[0][key] for key in contract}
    fixtures = {}
    duplicates = 0
    for trial in trials:
        if {key: trial[key] for key in contract} != reference:
            raise ValueError('Changed study contract requires a separate study')
        for fixture in trial['fixtures']:
            key = str(fixture['id'])
            if key in fixtures:
                duplicates += 1
                if (pd.Timestamp(fixture['generated_at']) == pd.Timestamp(fixtures[key]['generated_at'])
                        and fixture != fixtures[key]):
                    raise ValueError('Conflicting forecasts at the same generation time')
                if pd.Timestamp(fixture['generated_at']) >= pd.Timestamp(fixtures[key]['generated_at']):
                    continue
            fixtures[key] = fixture
    return {**trials[0], 'fixtures': sorted(fixtures.values(), key=lambda row: (row['kickoff'], str(row['id'])))}, duplicates


def run(root: Path, output: Path) -> dict:
    trials, evidence, batches = [], {}, []
    for trial_path in sorted(root.glob('*/trial.json')):
        directory = trial_path.parent
        digest = (directory/'trial.sha256').read_text().strip()
        trial = read_verified(trial_path, digest)
        for source in trial['sources']:
            read_verified(directory/source['path'], source['sha256'])
        trials.append(trial)
        batches.append({'directory': str(directory), 'trial_sha256': digest})
        for receipt_path in sorted(directory.glob('assessments/*/assessment.json')):
            receipt = json.loads(receipt_path.read_text())
            if receipt['trial_sha256'] != digest:
                raise ValueError('Assessment belongs to another frozen trial')
            for source in receipt['result_sources']:
                observed = pd.Timestamp(source['observed_at'])
                payload = read_verified(receipt_path.parent/source['path'], source['sha256'])
                for result in payload.get('matches', []):
                    key = str(result['id'])
                    if key not in evidence or observed > evidence[key][0]:
                        evidence[key] = (observed, [result])
                    elif observed == evidence[key][0] and result not in evidence[key][1]:
                        # Same-time conflicting observations stay ambiguous.
                        evidence[key][1].append(result)
    combined, duplicates = combine(trials)
    report = assess(combined, [row for _, values in evidence.values() for row in values], pd.Timestamp.now(tz='UTC'))
    report.update(batches=batches, duplicate_forecasts_excluded=duplicates,
                  selection_rule='earliest recorded forecast per provider ID',
                  result_rule='latest captured provider response; same-time conflicts remain ambiguous')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: report[key] for key in ['status','settled','pending','duplicate_forecasts_excluded']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root, args.output)
