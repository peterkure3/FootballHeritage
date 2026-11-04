"""Import independently verified upcoming fixtures from the dated official capture."""
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from api.db import get_db_connection
from etl.load_to_db import upsert_matches
from etl.transform import normalize_football_data_org_matches
from football_competitions import LEAGUES

capture = ROOT / 'pipeline/data/raw/team_form/leagues_20261025'
paths = [capture / (code + '.json') for code, *_ in LEAGUES if (capture / (code + '.json')).exists()]
for path in paths:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if any(row['competition']['code'] != path.stem for row in payload.get('matches', [])):
        raise ValueError('Competition identity mismatch')
frame = normalize_football_data_org_matches(paths)
frame['date'] = pd.to_datetime(frame.date, utc=True)
frame = frame[frame.status.isin(['SCHEDULED', 'TIMED']) & frame.date.gt(pd.Timestamp.now(tz='UTC'))].copy()
if frame.match_id.duplicated().any() or frame.empty:
    raise ValueError('Empty or duplicate official fixture capture')
frame['date'] = frame.date.dt.tz_convert('UTC').dt.tz_localize(None)
report = {'fixtures': len(frame), 'by_competition': frame.competition.value_counts().to_dict()}
print(json.dumps(report, indent=2))
if '--apply' in sys.argv:
    upsert_matches(frame, get_db_connection())
    report['applied'] = True
    (capture / 'fixture_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
