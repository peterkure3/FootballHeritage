"""Cache official nflverse/nflfastR assets and authenticated CFBD game/odds data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from dotenv import load_dotenv
import requests

BASE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BASE / 'data/raw/historical/gridiron_sources' / datetime.now(timezone.utc).strftime('%Y%m%d')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(source: str, years: list[int], pbp_years: list[int], output: Path,
            public_transport: str = 'requests', max_api_calls: int = 40) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest_file = output / 'manifest.json'
    manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {
        'captures': {}, 'failures': [], 'sources': {}, 'odds_observation_verified': False}
    public = requests.Session()
    if public_transport == 'scrapling':
        from etl.scrapling_transport import ScraplingTransport
        public = ScraplingTransport()
    session = requests.Session()
    calls = 0
    load_dotenv(BASE / '.env')

    def save_manifest() -> None:
        manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
        temp = output / 'manifest.json.tmp'
        temp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        temp.replace(manifest_file)

    def download(name: str, url: str, params=None, authenticated=False, asset=False) -> bool:
        nonlocal calls
        path = output / name
        existing = manifest['captures'].get(name)
        if existing and path.exists() and digest(path) == existing['sha256']:
            print(f'Cached: {name}', flush=True)
            return True
        headers = {}
        if authenticated:
            key = os.getenv('CFBD_API_KEY') or os.getenv('CFBD_API_TOKEN')
            if not key:
                manifest['failures'].append({'file': name, 'error': 'CFBD key not configured'})
                save_manifest()
                return False
            if calls >= max_api_calls:
                raise RuntimeError('Configured CFBD API-call budget exhausted')
            headers['Authorization'] = 'Bearer ' + key.strip()
            calls += 1
        client = session if authenticated or asset else public
        try:
            response = client.get(url, params=params, headers=headers, timeout=120)
        except requests.RequestException as exc:
            manifest['failures'].append({'file': name, 'error': type(exc).__name__})
            save_manifest()
            return False
        if response.status_code != 200:
            manifest['failures'].append({'file': name, 'http_status': response.status_code})
            save_manifest()
            if authenticated and response.status_code in {401, 403, 429}:
                raise RuntimeError(f'CFBD access/rate limit HTTP {response.status_code}; collection stopped')
            return False
        if name.endswith('.json'):
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                manifest['failures'].append({'file': name, 'error': 'Expected a nonempty JSON array'})
                save_manifest()
                return False
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_bytes(response.content)
        temp.replace(path)
        manifest['captures'][name] = {'url': url, 'params': params,
            'retrieved_at': datetime.now(timezone.utc).isoformat(), 'http_status': response.status_code,
            'bytes': path.stat().st_size, 'sha256': digest(path),
            'records': len(payload) if name.endswith('.json') else None,
            'transport': 'authenticated_requests' if authenticated else 'official_asset_download' if asset else public_transport}
        manifest['failures'] = [f for f in manifest['failures'] if f.get('file') != name]
        save_manifest()
        print(json.dumps({'file': name, 'bytes': path.stat().st_size,
            'records': manifest['captures'][name]['records']}), flush=True)
        time.sleep(.4)
        return True

    if source in {'nfl', 'all'}:
        manifest['sources']['nfl'] = 'nflverse schedules and nflfastR play-by-play releases'
        download('nfl_games.csv', 'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv')
        for year in pbp_years:
            download(f'nfl_pbp_{year}.parquet',
                f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.parquet', asset=True)
    if source in {'cfbd', 'all'}:
        manifest['sources']['ncaaf'] = 'CollegeFootballData authenticated games and historical lines'
        for year in years:
            download(f'cfbd_games_{year}.json', 'https://api.collegefootballdata.com/games',
                {'year': year, 'seasonType': 'both'}, authenticated=True)
            download(f'cfbd_lines_{year}.json', 'https://api.collegefootballdata.com/lines',
                {'year': year, 'seasonType': 'both'}, authenticated=True)
    manifest['sources']['pfr'] = 'Not collected: public site access returned 403 and published terms restrict ML use without authorization. NFL schedule PFR identifiers are cross-references only.'
    save_manifest()
    print(json.dumps({'output': str(output.resolve()), 'captures': len(manifest['captures']),
        'api_calls_this_run': calls, 'failures': manifest['failures']}), flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['all', 'nfl', 'cfbd'], default='all')
    parser.add_argument('--years', nargs='+', type=int, default=list(range(2013, 2027)))
    parser.add_argument('--pbp-years', nargs='*', type=int, default=[2023, 2024, 2025])
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--public-transport', choices=['requests', 'scrapling'], default='requests')
    parser.add_argument('--max-api-calls', type=int, default=40)
    args = parser.parse_args()
    now = datetime.now(timezone.utc).year
    if any(y < 2013 or y > now for y in args.years) or any(y < 1999 or y > now for y in args.pbp_years):
        parser.error('CFBD years must be 2013 through current; nflfastR years 1999 through current')
    result = collect(args.source, sorted(set(args.years)), sorted(set(args.pbp_years)),
        args.output_dir, args.public_transport, args.max_api_calls)
    if result['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
