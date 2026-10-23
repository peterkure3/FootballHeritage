"""Combine completed browser inspections and curl evidence into a reviewable audit."""
import argparse
from collections import Counter
import json
from pathlib import Path


def audit(captures):
    sources, curls, verification = [], [], []
    for root in captures:
        for source in json.loads((root / 'report.json').read_text(encoding='utf-8')):
            status = source['status']
            if 'restricted in your country' in source.get('visible_text', '').lower():
                status = 'region_restricted'
            sources.append({
                'bookmaker': source['bookmaker'], 'region': source.get('region'),
                'source_url': source.get('source_url'), 'final_url': source.get('final_url'),
                'status': status, 'title': source.get('title'),
                'capture_root': str(root / source['bookmaker']),
                'public_requests': [{
                    'method': request['method'], 'url': request['url'],
                    'browser_status': request['status'], 'shape': request.get('shape'),
                    'capture': request.get('capture'),
                } for request in source.get('requests', []) if request.get('capture')],
                'failures': source.get('failures', []),
            })
        diagnostic = sorted(root.glob('curl_replay_*.json'))
        if diagnostic:
            curls.extend(json.loads(diagnostic[-1].read_text(encoding='utf-8')))
        immutable = sorted(root.glob('curl_replays/*/report.json'))
        if immutable:
            verification.extend(json.loads(immutable[-1].read_text(encoding='utf-8')))
    if len({source['bookmaker'] for source in sources}) != len(sources):
        raise ValueError('Capture manifests overlap; choose disjoint inspection batches')
    return {
        'inspection_scope': 'Anonymous default-page network inspection; missing captured odds requests do not establish lack of football coverage.',
        'inventory': len(sources), 'resolved_urls': sum(bool(source['source_url']) for source in sources),
        'source_status_counts': dict(Counter(source['status'] for source in sources)),
        'curl_requests': len(curls),
        'curl_successful_json': sum(row['curl_status'] in {'200', '206'} and row.get('json_response', False) for row in curls),
        'sources': sources, 'curl_replays': curls, 'verification_replay': verification,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.captures)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in [
        'inventory', 'resolved_urls', 'source_status_counts', 'curl_requests', 'curl_successful_json',
    ]}, indent=2))


if __name__ == '__main__':
    main()
