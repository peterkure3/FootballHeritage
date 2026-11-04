"""Normalize backend sports. Preview by default; --apply persists changes."""
import argparse
from pathlib import Path
import sys
import psycopg2
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_to_backend import connection_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    conn = psycopg2.connect(**connection_settings(root / 'backend/.env', 'BACKEND', 'football_heritage'))
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT pg_advisory_xact_lock(7160413)')
            cur.execute('SELECT sport,count(*) FROM events GROUP BY sport ORDER BY sport')
            print('Before:', cur.fetchall())
            cur.execute((root / 'backend/migrations/20261031000001_canonical_event_sports.sql').read_text())
            cur.execute('SELECT sport,count(*) FROM events GROUP BY sport ORDER BY sport')
            print('After:', cur.fetchall())
        if args.apply:
            conn.commit()
            print('Applied normalization and future-write guard.')
        else:
            conn.rollback()
            print('Preview rolled back.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
