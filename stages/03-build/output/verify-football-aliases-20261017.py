"""Verify repaired inputs on real artifacts without importing retrospective picks."""
import sys
from pathlib import Path
import hashlib
import json
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pipeline'))
from threadpoolctl import threadpool_limits
from models.sport_predict import candidate_directory, predict_candidate
from models.paper_trial import TRIAL_ROOT, dashboard

candidate = '20261009T100528981075Z'
directory = candidate_directory(candidate, 'football')
protected = list(directory.glob('*')) + list(TRIAL_ROOT.glob('*/trial.json'))
before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected if path.is_file()}
audit = json.loads(Path(__file__).with_name('paper-trial-audit-20261017.json').read_text())
aliases = {'Brighton & Hove Albion': 'Brighton', 'Sunderland': 'Sunderland AFC', 'Hull City': 'Hull City AFC'}
checked = []
existing = 0
with threadpool_limits(limits=1):
    for row in audit['fixtures']:
        if row['manual']:
            continue
        prices = {key: value['decimal_odds'] for key, value in row['outcomes'].items()}
        kwargs = {'home_odds': prices.get('home_win'), 'away_odds': prices.get('away_win'), 'draw_odds': prices.get('draw')}
        result = predict_candidate(candidate, 'football', row['home'], row['away'], row['kickoff'], **kwargs)
        if row['status'] == 'excluded_model_input':
            canonical = predict_candidate(candidate, 'football', aliases.get(row['home'], row['home']),
                aliases.get(row['away'], row['away']), row['kickoff'], **kwargs)
            assert result['probabilities'] == canonical['probabilities']
            checked.append({'home': row['home'], 'away': row['away'], 'probabilities_match_canonical': True})
        else:
            expected = {key: value['probability'] for key, value in row['outcomes'].items()}
            assert all(abs(result['probabilities'][key] - value) < 1e-12 for key, value in expected.items()), row
            existing += 1
live = []
for name in aliases:
    body = {'candidate_id': candidate, 'sport': 'football', 'home_team': name, 'away_team': 'Arsenal',
            'kickoff': '2027-01-01T12:00:00Z'}
    request = Request('http://localhost:5555/api/v1/sport-models/preview',
                      data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=45) as response:
        result = json.load(response)
        assert result['home_team'] == name and abs(sum(result['probabilities'].values()) - 1) < 1e-6
        live.append({'name': name, 'http_status': response.status})
after = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in before}
assert before == after, 'Model artifacts or immutable trial records changed'
current = dashboard()
output = {'repaired_excluded_inputs': checked, 'existing_forecasts_reproduced': existing,
          'live_api': live, 'artifacts_and_original_trials_unchanged': True,
          'retrospective_trials_imported': 0,
          'studies': [{key: study[key] for key in ['candidate_id', 'settled_selections', 'pending_selections']}
                      for study in current['studies']]}
Path(__file__).with_name('football-alias-verification-20261017.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output, indent=2))
