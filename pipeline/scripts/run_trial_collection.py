"""Scheduled, non-overlapping ingestion/collection with logs and health status."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterator

from etl.utils import load_status_json, save_json

BASE = Path(__file__).resolve().parents[1]
LOGS = BASE / 'logs'


@contextmanager
def exclusive_run(path: Path) -> Iterator[bool]:
    stream = path.open('a+b')
    stream.seek(0)
    acquired = False
    try:
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError:
                pass
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                pass
        yield acquired
    finally:
        if acquired and os.name == 'nt':
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        stream.close()


def execute(module: str, log) -> bool:
    log.write(f'\n{datetime.now(timezone.utc).isoformat()} Running {module}\n')
    log.flush()
    try:
        result = subprocess.run([sys.executable, '-m', module], cwd=BASE, stdout=log,
            stderr=subprocess.STDOUT, timeout=1800,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.write(f'{module}: {type(exc).__name__}\n')
        return False


def main() -> int:
    LOGS.mkdir(exist_ok=True)
    with exclusive_run(LOGS / 'edge_trial.lock') as acquired:
        if not acquired:
            print('Existing trial collection is still running; skipped overlapping invocation.')
            return 0
        status_path = LOGS / 'edge_trial_status.json'
        status = load_status_json(status_path) or {}
        now = datetime.now(timezone.utc)
        status.update(last_attempt_at=now.isoformat(), outcome='running', failed_steps=[])
        status.pop('status_error', None)
        save_status(status_path, status)
        with (LOGS / f'edge_trial_{now:%Y%m%d}.log').open('a', encoding='utf-8') as log:
            if status.get('last_ingested_date') != now.date().isoformat():
                for module in ['scripts.refresh_trial_fixtures']:
                    if not execute(module, log):
                        status['failed_steps'].append(module)
                        break
                else:
                    status['last_ingested_date'] = now.date().isoformat()
            if not execute('scripts.refresh_regional_pipeline', log):
                status['failed_steps'].append('scripts.refresh_regional_pipeline')
            # Recover formal assessment even if collection/settlement had an error.
            if not execute('scripts.assess_paper_trial', log):
                status['failed_steps'].append('scripts.assess_paper_trial')
        status.update(finished_at=datetime.now(timezone.utc).isoformat(),
                      outcome='failed' if status['failed_steps'] else 'success')
        if not status['failed_steps']:
            status['last_success_at'] = status['finished_at']
        save_status(status_path, status)
        if sys.stdout is not None:
            print(json.dumps(status, indent=2))
        return 1 if status['failed_steps'] else 0


def save_status(path: Path, status: dict) -> None:
    save_json(status, path)


if __name__ == '__main__':
    raise SystemExit(main())
