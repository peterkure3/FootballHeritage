"""Preserve evidenced NBA observation times across independent research captures."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pandas as pd


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aware(value):
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError('Observation timestamps require timezone')
    return timestamp.tz_convert('UTC')


def fingerprint(row):
    return (aware(row['date']), row['league'], row['home_team'], row['away_team'],
            row['home_score'], row['away_score'])


def combine(captures):
    current = {}; last_seen = {}; revisions = []; quarantined = []; preserved = 0
    for capture in sorted(captures, key=lambda c: aware(c['created_at'])):
        observed = aware(capture['created_at']); seen = set()
        for excluded in capture.get('excluded', []):
            key = str(excluded['id'])
            if key in current:
                del current[key]
                quarantined.append({'id': key, 'observed_at': observed.isoformat(), 'reason': excluded['reason']})
        for raw in capture['rows']:
            row = deepcopy(raw); key = str(row['provider_event_id'])
            if key in seen:
                raise ValueError('Duplicate provider ID in a capture')
            seen.add(key)
            available = aware(row['result_available_at'])
            if (available > observed or aware(row['date']) >= available
                    or row['league'] != 'basketball_nba' or row.get('completed') is not True
                    or any(type(row[k]) is not int or row[k] < 0 for k in ['home_score', 'away_score'])
                    or row['home_score'] == row['away_score']):
                raise ValueError('Invalid observed NBA result')
            previous = current.get(key)
            if previous and fingerprint(previous) == fingerprint(row):
                if aware(previous['result_available_at']) < available:
                    row['result_available_at'] = previous['result_available_at']
                    row['first_observation_capture'] = previous['first_observation_capture']
                    preserved += 1
            elif previous:
                if observed == last_seen[key] or available <= last_seen[key]:
                    raise ValueError('Conflicting or backdated correction observation')
                revisions.append({'id': key, 'observed_at': observed.isoformat(),
                                  'old': list(map(str, fingerprint(previous))), 'new': list(map(str, fingerprint(row)))})
            row.setdefault('first_observation_capture', capture['reference'])
            current[key] = row; last_seen[key] = observed
    rows = sorted(current.values(), key=lambda r: (aware(r['date']), str(r['provider_event_id'])))
    return rows, {'earlier_times_preserved': preserved, 'revisions': revisions, 'quarantined': quarantined}


def load_capture(folder):
    manifest_path = folder/'manifest.json'; manifest = json.loads(manifest_path.read_text())
    normalized = folder/'reconciled.jsonl'; evidence = {}
    def verify(path, digest):
        if sha(path) != digest:
            raise ValueError(f'Observation evidence checksum mismatch: {path}')
        evidence[str(path.resolve())] = digest
    verify(manifest_path, sha(manifest_path)); verify(normalized, manifest['normalized_sha256'])
    for source in manifest['sources']:
        verify(folder/source['file'], source['sha256'])
    if 'primary_source_sha256' in manifest:
        primary = folder.parent
        verify(primary/'normalized.jsonl', manifest['primary_source_sha256'])
        primary_manifest = json.loads((primary/'manifest.json').read_text())
        verify(primary/'manifest.json', sha(primary/'manifest.json'))
        if primary_manifest['normalized_sha256'] != manifest['primary_source_sha256']:
            raise ValueError('Primary capture linkage mismatch')
        for source in primary_manifest['sources']:
            verify(primary/source['file'], source['sha256'])
    elif manifest.get('kind') != 'nba_history_observations_v1':
        raise ValueError('Unsupported observation evidence contract')
    if aware(manifest['created_at']) > pd.Timestamp.now(tz='UTC'):
        raise ValueError('Future observation capture')
    capture = {'created_at': manifest['created_at'], 'excluded': manifest.get('excluded', []),
        'reference': {'directory': str(folder), 'manifest_sha256': sha(manifest_path)},
        'rows': [json.loads(line) for line in normalized.read_text().splitlines()]}
    return capture, evidence


def run(inputs, output):
    captures = []; evidence = {}
    for folder in inputs:
        capture, sources = load_capture(folder); captures.append(capture)
        for path, digest in sources.items():
            if path in evidence and evidence[path] != digest:
                raise ValueError('Observation source changed between inputs')
            evidence[path] = digest
    rows, summary = combine(captures)
    output.mkdir(parents=True, exist_ok=False)
    normalized = output/'reconciled.jsonl'
    normalized.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    manifest = {'kind': 'nba_history_observations_v1', 'created_at': pd.Timestamp.now(tz='UTC').isoformat(),
        'matched': len(rows), 'normalized_sha256': sha(normalized), 'excluded': summary['quarantined'],
        'sources': [{'file': os.path.relpath(path, output), 'sha256': digest} for path, digest in sorted(evidence.items())],
        'availability_policy': 'Earliest verified observation of current unchanged result; reset on corrections',
        'production_changed': False, **summary}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False))
    print(json.dumps({'results': len(rows), 'earlier_times_preserved': summary['earlier_times_preserved'],
        'revisions': len(summary['revisions']), 'quarantined': len(summary['quarantined'])}, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.captures, args.output)
