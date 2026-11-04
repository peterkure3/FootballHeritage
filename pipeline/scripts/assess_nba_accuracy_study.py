"""Accumulate one frozen NBA study, recomputing results from captured evidence."""
import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.assess_accuracy_study import combine, read_verified
from scripts.evaluate_nba_freshness_shadow import assess


def combine_nba(trials):
    if not trials:
        raise ValueError('No frozen NBA forecast batches')
    status = trials[0]['status']
    common = ['status', 'classes', 'policy', 'baseline_history_sha256']
    if status == 'prospective_NBA_model_shadow':
        contract = common + ['model_hashes', 'feature_contract']
    elif status == 'prospective_NBA_freshness_shadow':
        contract = common + ['model_sha256', 'same_model_for_both_arms']
    else:
        raise ValueError('Unsupported NBA study contract')
    if any(trial['status'] != status for trial in trials):
        raise ValueError('Different NBA hypotheses require a separate study')
    return combine(trials, contract)


def latest_evidence(evidence, result, observed):
    key = str(result['id'])
    if key not in evidence or observed > evidence[key][0]:
        evidence[key] = observed, [result]
    elif observed == evidence[key][0] and result not in evidence[key][1]:
        evidence[key][1].append(result)


def run(root: Path, output: Path):
    trials = []; evidence = {}; batches = []; now = pd.Timestamp.now(tz='UTC')
    for path in sorted(root.glob('*/trial.json')):
        directory = path.parent; digest = (directory/'trial.sha256').read_text().strip()
        trial = read_verified(path, digest)
        for source in trial['schedule_sources']:
            read_verified(directory/source['file'], source['sha256'])
        # Validate all recaptures, including forecasts that deduplication will exclude.
        assess(trial, [], now)
        trials.append(trial); batches.append({'directory': str(directory), 'trial_sha256': digest})
        for path in sorted(directory.glob('assessments/*/assessment.json')):
            receipt = json.loads(path.read_text())
            if receipt['trial_sha256'] != digest:
                raise ValueError('NBA assessment belongs to another trial')
            for source in receipt['result_sources']:
                observed = pd.Timestamp(source['observed_at'])
                if observed.tzinfo is None or observed > now:
                    raise ValueError('Invalid NBA result observation time')
                payload = read_verified(path.parent/source['file'], source['sha256'])
                if source['status'] != 200:
                    continue
                for result in payload.get('events', []):
                    latest_evidence(evidence, result, observed)
    combined, duplicates = combine_nba(trials)
    report = assess(combined, [row for _, values in evidence.values() for row in values], now)
    report.update(batches=batches, study_contract=combined['status'], duplicate_forecasts_excluded=duplicates,
        selection_rule='earliest recorded forecast per provider ID',
        result_rule='latest observed ESPN event; same-time conflicting observations stay ambiguous')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({key: report[key] for key in ['status', 'settled', 'pending', 'duplicate_forecasts_excluded']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.root, args.output)
