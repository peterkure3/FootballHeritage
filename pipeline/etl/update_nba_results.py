"""
Update match results for completed NBA games.
Fetches final scores and updates the multisport result capture store.
Run this periodically (e.g., daily) to keep results current.
"""
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.update_sport_results import main

if __name__ == '__main__':
    raise SystemExit(main('nba'))
