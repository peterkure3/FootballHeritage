"""Preserve and quarantine the three verified zero-filled incident artifacts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'pipeline'
sys.path.insert(0, str(BASE))
from etl.utils import save_json

DIGEST = '11a742335a6371a6e2df389bd85494f940c18ab87115f6478a4d5f55823952bf'


def main() -> None:
    damaged = BASE / 'data/processed/sportsbook_odds' / DIGEST
    health = BASE / 'logs/edge_trial_status.json'
    quarantine = BASE / 'data/processed/_quarantine' / (
        'json-corruption-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    files = [damaged / 'manifest.json', damaged / 'odds.parquet', health]
    evidence = []
    # Refuse to move any different file or any path outside this workspace.
    for path in [damaged, health, quarantine, *files]:
        if not path.resolve().is_relative_to(BASE.resolve()):
            raise ValueError(f'Path outside pipeline: {path}')
    for path, expected_size in zip(files, [892, 17525, 260]):
        payload = path.read_bytes()
        if len(payload) != expected_size or payload != bytes(expected_size):
            raise ValueError(f'Incident evidence changed; refusing repair: {path}')
        evidence.append({'path': str(path), 'bytes': len(payload),
                         'sha256': hashlib.sha256(payload).hexdigest(), 'all_zero': True})
    sources = list((BASE / 'data/raw/sportsbooks').glob('*/*.jsonl'))
    if any(hashlib.sha256(path.read_bytes()).hexdigest() == DIGEST for path in sources):
        raise ValueError('Original source is available; reconstruct this import instead')
    quarantine.mkdir(parents=True, exist_ok=False)
    report = {'status': 'quarantined_unrecoverable_import', 'evidence': evidence,
              'quarantine': str(quarantine), 'source_files_checked': len(sources),
              'source_checksum_match': False,
              'excluded_import': DIGEST, 'active_model_changed': False,
              'note': 'Import cannot be reconstructed from surviving local captures. Restore from a verified backup if available.'}
    save_json(report, quarantine / 'recovery.json')
    shutil.move(str(damaged), str(quarantine / DIGEST))
    shutil.move(str(health), str(quarantine / health.name))
    save_json({'outcome': 'unavailable', 'failed_steps': [],
               'status_error': 'Previous collector status was zero-filled; previous success time is unknown.',
               'recovery_evidence': str(quarantine / 'recovery.json')}, health)
    save_json(report, ROOT / 'stages/03-build/output/pipeline-json-recovery-20261015.json')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
