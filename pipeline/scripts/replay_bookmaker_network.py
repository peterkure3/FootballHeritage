"""Replay observed public fixture requests with curl, without browser credentials."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


def eligible(request):
    url = request['url']
    endpoint = urlsplit(url).path
    return (request.get('capture') and request['method'] in {'GET', 'POST'}
            and not re.search(r'analytics|tracking|telemetry|virtual|live|login|register|wallet|account|profile|token|auth|redacted|banned|orders|patron|promotion|logo|dictionary|i18n|cms', endpoint, re.I)
            and not re.search(r'redacted', url, re.I)
            and re.search(r'match|event|prematch|competition|league|fixture|offer|coupon|games|sport', endpoint, re.I)
            and (request['method'] == 'GET' or re.search(r'offer|events/list|search', endpoint, re.I))
            and '<redacted>' not in json.dumps(request.get('body'))
            and request.get('body') != '<non-JSON body; review required>')


def replay(capture, book, index, request):
    destination = capture / book / f'curl_{index}.json'
    command = ['curl.exe', '--silent', '--show-error', '--location', '--connect-timeout', '6',
               '--max-time', '20', '--request', request['method'], '--url', request['url'],
               '--output', str(destination), '--write-out', '%{http_code}']
    for key, value in request.get('headers', {}).items():
        command.extend(['--header', key + ': ' + value])
    body = request.get('body')
    body_file = None
    if body is not None:
        body_file = capture / book / f'curl_{index}_body.json'
        body_file.write_text(json.dumps(body), encoding='utf-8')
        command.extend(['--data-binary', '@' + str(body_file)])
    result = subprocess.run(command, capture_output=True, text=True, timeout=25)
    revocation_best_effort = False
    if result.returncode == 35 and 'CRYPT_E_REVOCATION_OFFLINE' in result.stderr:
        # Schannel could not reach the revocation service. Certificate/hostname
        # verification stays enabled; known revoked certificates remain errors.
        command.insert(1, '--ssl-revoke-best-effort')
        revocation_best_effort = True
        result = subprocess.run(command, capture_output=True, text=True, timeout=25)
    row = {'bookmaker': book, 'url': request['url'], 'method': request['method'],
           'headers': request.get('headers', {}), 'browser_status': request['status'],
           'curl_status': result.stdout, 'exit_code': result.returncode,
           'observed_at': datetime.now(timezone.utc).isoformat(), 'browser_credentials_used': False,
           'revocation_best_effort': revocation_best_effort,
           'curl_arguments': command, 'capture': str(destination)}
    if body_file:
        row['body_file'] = str(body_file)
    if result.returncode:
        row['error'] = result.stderr[-200:]
    elif destination.exists():
        try:
            value = json.loads(destination.read_text(encoding='utf-8'))
            row['json_response'] = True
            row['shape'] = 'array' if isinstance(value, list) else list(value)[:15]
        except (ValueError, UnicodeError):
            row['json_response'] = False
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--books', nargs='*')
    parser.add_argument('--limit-per-book', type=int, default=6)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    replay_root = args.capture / 'curl_replays' / stamp
    replay_root.mkdir(parents=True, exist_ok=False)
    jobs = []
    for source in json.loads((args.capture / 'report.json').read_text(encoding='utf-8')):
        if args.books and source['bookmaker'] not in args.books:
            continue
        if not re.fullmatch(r'[a-z0-9_]+', source['bookmaker']):
            raise ValueError('Bookmaker IDs must be safe stable slugs')
        selected = [r for r in source.get('requests', []) if eligible(r)]
        selected.sort(key=lambda r: (not bool(re.search(r'matches|events|prematch|coupon|games', r['url'], re.I)), r['url']))
        for index, request in enumerate(selected[:args.limit_per_book]):
            jobs.append((source['bookmaker'], index, request))
    for book in {job[0] for job in jobs}:
        (replay_root / book).mkdir()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda job: replay(replay_root, *job), jobs))
    report = replay_root / 'report.json'
    report.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(report), 'requests': len(results),
        'successful_JSON': sum(r['curl_status'] in {'200','206'} and r.get('json_response', False) for r in results),
        'sources': sorted({r['bookmaker'] for r in results})}, indent=2))


if __name__ == '__main__':
    main()
