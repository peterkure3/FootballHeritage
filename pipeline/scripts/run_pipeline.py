"""Bounded pipeline jobs with dependency gates, a shared lock and durable logs."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Iterator

BASE = Path(__file__).resolve().parents[1]
RUNS = BASE / 'logs' / 'automation'


class AlreadyRunning(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def pipeline_lock(path: Path) -> Iterator[None]:
    """The OS releases this lock on a crash; never delete a live lock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise AlreadyRunning('Another pipeline job holds the lock') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


@dataclass(frozen=True)
class Step:
    name: str
    module: str
    args: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    timeout: int = 1800


def plan(job: str, directory: Path, training_args: tuple[str, ...] = (),
         public_only: bool = False) -> list[Step]:
    regional = Step('regional', 'scripts.refresh_regional_pipeline', timeout=2400)
    snapshot = Step('snapshot', 'etl.betting_intel', timeout=900)
    export = Step('export', 'scripts.export_market_report',
                  ('--output', str(directory / 'markets')), ('snapshot',), 600)
    if job == 'markets':
        return [regional, snapshot, export]
    if job == 'weekly':
        # Both trainers save candidates; promotion is a separate reviewed operation.
        return [Step('football_candidate', 'models.train_model_v2', training_args, timeout=21600),
                Step('league_candidates', 'models.train_football_leagues', timeout=21600)]
    if job in {'daily', 'daily-local'}:
        steps = [Step('football_fetch', 'etl.fetch_raw_data', ('--source', 'football')),
                 Step('football_odds', 'etl.fetch_raw_data', ('--source', 'odds')),
                 Step('nba_fetch', 'etl.fetch_nba_data_wrapper'),
                 Step('ncaab_fetch', 'etl.fetch_ncaab_odds'),
                 Step('form', 'etl.fetch_football_form',
                      ('--output-dir', str(BASE / 'data/raw/team_form' / directory.name),
                       '--import-history'), timeout=2400),
                 Step('transform', 'etl.transform', needs=('football_fetch',)),
                 Step('load', 'etl.load_to_db', needs=('transform',)),
                 Step('schema', 'check_schema', ('--ensure', 'nba_games'), ('load',)),
                 Step('predictions', 'models.predict_v2', needs=('load', 'form', 'schema')),
                 regional]
        if job == 'daily':
            steps.append(Step('backend_sync', 'sync_to_backend', needs=('load', 'predictions')))
        if public_only:
            steps = [step for step in steps if step.name not in {'football_odds', 'nba_fetch', 'ncaab_fetch'}]
        return [*steps, snapshot, export]
    if job == 'report':
        return [Step('export', 'scripts.export_market_report',
                     ('--output', str(directory / 'markets')), timeout=600)]
    raise ValueError(f'Unknown job: {job}')


def stop_tree(process: subprocess.Popen) -> None:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def execute(step: Step, directory: Path, python: Path) -> dict:
    started = time.monotonic()
    command = [str(python), '-u', '-m', step.module, *step.args]
    log = directory / f'{step.name}.log'
    result = {'name': step.name, 'command': command, 'log': str(log), 'status': 'failed'}
    env = {**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}
    try:
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=BASE, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
            try:
                code = process.wait(timeout=step.timeout)
            except subprocess.TimeoutExpired:
                stop_tree(process)
                result['status'] = 'timeout'
            except BaseException:
                stop_tree(process)
                raise
            else:
                result.update(exit_code=code, status='succeeded' if code == 0 else 'failed')
    except OSError as exc:
        result['error'] = type(exc).__name__
    result['seconds'] = round(time.monotonic() - started, 3)
    return result


def run(job: str, root: Path, python: Path, training_args: tuple[str, ...] = (),
        public_only: bool = False) -> int:
    directory = root / f'{stamp()}-{job}'
    directory.mkdir(parents=True, exist_ok=False)
    report = {'job': job, 'started_at': datetime.now(timezone.utc).isoformat(),
              'directory': str(directory), 'public_only': public_only, 'status': 'running', 'steps': []}
    outcomes = {}
    try:
        for step in plan(job, directory, training_args, public_only):
            blocked = [name for name in step.needs if outcomes.get(name) != 'succeeded']
            if blocked:
                result = {'name': step.name, 'status': 'blocked', 'dependencies': blocked}
            else:
                print(f'[{job}] {step.name}', flush=True)
                result = execute(step, directory, python)
            outcomes[step.name] = result['status']
            report['steps'].append(result)
            atomic_json(directory / 'run.json', report)
        report['status'] = 'succeeded' if all(v == 'succeeded' for v in outcomes.values()) else 'failed'
    except BaseException as exc:
        report.update(status='interrupted', error=type(exc).__name__)
        raise
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        atomic_json(directory / 'run.json', report)
        atomic_json(root / f'latest-{job}.json', report)
        print(json.dumps({'status': report['status'], 'report': str(directory / 'run.json')}), flush=True)
    return int(report['status'] != 'succeeded')


def doctor() -> int:
    """Read-only probes; never print URLs, credentials or exception messages."""
    import importlib
    checks = []
    for name in ('pandas', 'pyarrow', 'numpy', 'scipy', 'sklearn', 'xgboost',
                 'lightgbm', 'joblib', 'sqlalchemy', 'psycopg2', 'dotenv', 'requests', 'fastapi'):
        try:
            module = importlib.import_module(name)
            checks.append({'check': name, 'ok': True, 'version': getattr(module, '__version__', 'installed')})
        except Exception as exc:
            checks.append({'check': name, 'ok': False, 'error': type(exc).__name__})
    scraper = BASE / '.venv-scrapling/Scripts/python.exe'
    checks.append({'check': 'scrapling_python', 'ok': scraper.is_file()})
    if scraper.is_file():
        probe = subprocess.run([str(scraper), '-c', 'import scrapling'], capture_output=True, timeout=30)
        checks.append({'check': 'scrapling_import', 'ok': probe.returncode == 0})
    try:
        from importlib.metadata import version
        pandas_major = int(version('pandas').split('.')[0])
        sqlalchemy_version = tuple(int(x) for x in version('SQLAlchemy').split('.')[:3])
        checks.append({'check': 'pandas_sqlalchemy_compatibility',
                       'ok': pandas_major < 3 or sqlalchemy_version >= (2, 0, 36)})
    except Exception as exc:
        checks.append({'check': 'pandas_sqlalchemy_compatibility', 'ok': False, 'error': type(exc).__name__})
    try:
        from config import FOOTBALL_DATA_ORG_API_KEY, MODEL_DIR, MODEL_VERSION
        from api.db import get_db_connection, get_heritage_db_connection
        checks.append({'check': 'football_api_key_configured', 'ok': bool(FOOTBALL_DATA_ORG_API_KEY)})
        for name in ('model', 'features', 'label_encoder'):
            checks.append({'check': f'active_{name}', 'ok': (MODEL_DIR / f'{name}_v{MODEL_VERSION}.pkl').is_file()})
        from sqlalchemy import create_engine, text
        for name, factory in (('pipeline_db', get_db_connection), ('backend_db', get_heritage_db_connection)):
            engine = None
            try:
                engine = create_engine(factory().url, connect_args={'connect_timeout': 5})
                with engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                checks.append({'check': name, 'ok': True})
            except Exception as exc:
                checks.append({'check': name, 'ok': False, 'error': type(exc).__name__})
            finally:
                if engine is not None:
                    engine.dispose()
    except Exception as exc:
        checks.append({'check': 'configuration', 'ok': False, 'error': type(exc).__name__})
    print(json.dumps({'python': sys.executable, 'checks': checks}, indent=2))
    return int(any(not row['ok'] for row in checks))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=['daily', 'daily-local', 'markets', 'weekly', 'report', 'doctor', 'status'])
    parser.add_argument('--dry-run', action='store_true', help='Print the plan without running jobs or creating files')
    parser.add_argument('--run-root', type=Path, default=RUNS)
    parser.add_argument('--public-only', action='store_true',
                        help='Daily: skip paid Odds API fetches; retain official fixtures and public collectors')
    parser.add_argument('--training-args', nargs=argparse.REMAINDER, default=[], help='Weekly trainer options; must be last')
    args = parser.parse_args()
    if args.training_args and args.job != 'weekly':
        parser.error('--training-args is for weekly only')
    if args.public_only and args.job not in {'daily', 'daily-local'}:
        parser.error('--public-only is for daily jobs only')
    if any(x == '--output-dir' or x.startswith('--output-dir=') for x in args.training_args):
        parser.error('Unattended training always writes a new candidate; --output-dir is not allowed')
    os.chdir(BASE)
    root = args.run_root.resolve()
    if args.dry_run:
        if args.job in {'doctor', 'status'}:
            parser.error('--dry-run requires a runnable job')
        print(json.dumps([asdict(step) for step in plan(args.job, root / '<run-id>', tuple(args.training_args), args.public_only)], indent=2))
        return 0
    if args.job == 'doctor':
        return doctor()
    if args.job == 'status':
        rows = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(root.glob('latest-*.json'))]
        print(json.dumps(rows, indent=2))
        return int(not rows or any(row['status'] != 'succeeded' for row in rows))
    try:
        with pipeline_lock(BASE / 'logs/automation/pipeline.lock'):
            return run(args.job, root, Path(sys.executable), tuple(args.training_args), args.public_only)
    except AlreadyRunning:
        print('Another pipeline job holds the lock. Retry after it finishes.', file=sys.stderr)
        return 75


if __name__ == '__main__':
    raise SystemExit(main())
