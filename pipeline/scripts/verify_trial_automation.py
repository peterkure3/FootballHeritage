"""Exercise the actual trial HTTP endpoint using an isolated local server."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import requests
from config import BASE_DIR, MODEL_DIR


def main() -> None:
    artifacts = list(MODEL_DIR.glob('*.pkl'))
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api.main:app',
        '--host', '127.0.0.1', '--port', '5568'], cwd=BASE_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        payload = None
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('Isolated trial API exited before startup')
            try:
                response = requests.get('http://127.0.0.1:5568/api/v1/prediction-dashboard/paper-trials', timeout=2)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException:
                time.sleep(.5)
        assert payload and payload['studies']
        study = payload['studies'][0]
        assert study['protocol']['minimum_selections'] == 200
        assert study['protocol']['minimum_fixture_days'] == 60
        assert study['settled_selections'] == 4 and study['fixture_days'] == 1
        assert study['assessment_status'] == 'collecting' and study['assessment'] is None
        assert abs(study['roi'] + .125) < 1e-12
        assert payload['profitable_edge_established'] is False
        assert {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts} == before
        output = BASE_DIR.parent / 'stages/03-build/output/trial-automation-live-20261010.json'
        report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'http_status': response.status_code,
            'active_artifacts_unchanged': True, 'response': payload}
        output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        print(json.dumps({'http_status': response.status_code, 'selections': study['settled_selections'],
            'days': study['fixture_days'], 'gate': study['assessment_status'], 'report': str(output)}))
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == '__main__':
    main()
