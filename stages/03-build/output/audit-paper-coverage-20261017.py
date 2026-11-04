"""Read-only audit of excluded team names and official fixture coverage."""
import sys
from pathlib import Path
import json
from collections import Counter
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pipeline'))
from models.data import team_key
from models.sport_predict import candidate_directory
from models.paper_trial import result_key
from config import RAW_DATA_DIR

audit = json.loads(Path(__file__).with_name('paper-trial-audit-20261017.json').read_text())
history = pd.read_parquet(candidate_directory('20261009T100528981075Z', 'football') / 'dataset.parquet')
known = set(history.home_key) | set(history.away_key)
excluded = [row for row in audit['fixtures'] if row['status'] == 'excluded_model_input']
names = sorted({row[side] for row in excluded for side in ['home', 'away']})
checks = [{'name': name, 'key': team_key(name), 'present': team_key(name) in known,
           'related_keys': sorted(key for key in known if any(token in key for token in name.casefold().replace('&', '').split() if len(token) > 4))}
          for name in names]
aliases = {'Brighton & Hove Albion': 'Brighton', 'Sunderland': 'Sunderland AFC', 'Hull City': 'Hull City AFC'}
alias_checks = [{'name': name, 'candidate_name': canonical, 'key': team_key(canonical),
                 'present': team_key(canonical) in known} for name, canonical in aliases.items()]
official = {}
for path in sorted((RAW_DATA_DIR / 'trial_fixtures').glob('*.json')):
    for row in json.loads(path.read_text()).get('matches', []):
        if row['utcDate'][:10] >= '2026-10-10':
            official[row['id']] = row
seen = {result_key(row['home'], row['away'], row['kickoff']) for row in audit['fixtures'] if not row['manual']}
missing = [{key: row[key] for key in ['id', 'utcDate', 'status', 'homeTeam', 'awayTeam']}
           for row in official.values() if result_key(row['homeTeam']['name'], row['awayTeam']['name'], row['utcDate']) not in seen]
output = {'team_checks': checks, 'alias_checks': alias_checks,
          'known_hull_keys': sorted(key for key in known if 'hull' in key),
          'official_fixtures_since_start': len(official), 'official_statuses': dict(Counter(row['status'] for row in official.values())),
          'official_missing_from_trial': missing,
          'excluded_with_both_teams_known': [row for row in excluded if team_key(row['home']) in known and team_key(row['away']) in known],
          'history_date_range': [str(history.date.min()), str(history.date.max())]}
Path(__file__).with_name('paper-trial-coverage-20261017.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output, indent=2))
