"""Acquire the original CC BY Wyscout archive with resumable, verified captures."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / 'data/raw/historical/soccer_events/20261022'
COLLECTION = 'https://api.figshare.com/v2/collections/4415000/articles?page_size=100'


def file_hash(path: Path, algorithm: str = 'sha256') -> str:
    digest = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def collect(root: Path) -> dict:
    from etl.scrapling_transport import ScraplingTransport
    root.mkdir(parents=True, exist_ok=True)
    (root / '.gitignore').write_text('*\n!.gitignore\n', encoding='utf-8')
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'provider': 'Wyscout public archive', 'captures': {},
        'citation': 'Pappalardo et al. (2019), doi:10.1038/s41597-019-0247-7',
        'collection': COLLECTION}
    transport = ScraplingTransport()

    def capture(name: str, url: str, expected: dict | None = None) -> bytes:
        path = root / name
        prior = manifest['captures'].get(name)
        if prior and path.exists() and file_hash(path) == prior['sha256']:
            body = path.read_bytes()
        else:
            response = transport.get(url, timeout=300)
            response.raise_for_status()
            body = response.content
            temp = path.with_suffix(path.suffix + '.tmp')
            temp.write_bytes(body)
            if expected:
                if len(body) != expected['size']:
                    raise ValueError(f'Size mismatch: {name}')
                if hashlib.md5(body).hexdigest() != expected['computed_md5']:
                    raise ValueError(f'Provider MD5 mismatch: {name}')
            temp.replace(path)
            manifest['captures'][name] = {
                'url': url, 'final_url': urlunsplit(urlsplit(response.url)._replace(query='')),
                'sha256': file_hash(path), 'bytes': len(body),
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'provider_md5': expected.get('computed_md5') if expected else None}
            temporary = root / 'manifest.json.tmp'
            temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            temporary.replace(manifest_path)
        if expected and (len(body) != expected['size'] or
                         hashlib.md5(body).hexdigest() != expected['computed_md5']):
            raise ValueError(f'Cached file differs from source metadata: {name}')
        print(f'Verified {name}: {len(body):,} bytes', flush=True)
        return body

    articles = json.loads(capture('collection.json', COLLECTION))
    for article in articles:
        if article['title'].lower() not in {'events', 'matches', 'teams', 'players'}:
            continue
        metadata = json.loads(capture(f"article-{article['id']}.json", article['url']))
        if metadata['license']['name'] != 'CC BY 4.0':
            raise ValueError('Unexpected dataset license; acquisition stopped')
        for asset in metadata['files']:
            name = asset['name']
            if name not in {'events.zip', 'matches.zip', 'players.json', 'teams.json'}:
                raise ValueError(f'Unexpected asset name: {name}')
            capture(name, asset['download_url'], asset)
    if not {'events.zip', 'matches.zip', 'players.json', 'teams.json'} <= manifest['captures'].keys():
        raise ValueError('Archive is incomplete')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    collect(args.output_dir)


if __name__ == '__main__':
    main()
