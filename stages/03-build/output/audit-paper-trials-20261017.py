"""Read-only decomposition of trial eligibility, selections and settlements."""
import sys
from pathlib import Path
import json
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pipeline'))
from models.paper_trial import TRIAL_ROOT, dashboard

now = datetime.now(timezone.utc)
data = dashboard()
summary = {'audited_at': now.isoformat(), 'collector': data['collector'], 'studies': data['studies'], 'batches': [], 'fixtures': [], 'policy_mismatches': []}
for report in data['trials']:
    trial = json.loads((TRIAL_ROOT / report['trial_sha256'] / 'trial.json').read_text())
    manual = trial['policy'].get('selection') == 'user_selected'
    summary['batches'].append({
        'id': report['trial_sha256'], 'created_at': trial['created_at'], 'manual': manual,
        'fixtures': len(trial['fixtures']), 'statuses': dict(Counter(row['status'] for row in trial['fixtures'])),
        'settled_selections': report['settled_selections'], 'pending_forecasts': report['pending_forecasts'],
    })
    for forecast, receipt in zip(trial['fixtures'], report['fixtures']):
        analysis = forecast.get('outcomes', {})
        best = max(analysis, key=lambda outcome: analysis[outcome]['stressed_estimated_ev']) if analysis else None
        expected = best if best and analysis[best]['stressed_estimated_ev'] >= .05 else None
        if not manual and forecast['status'] == 'recorded_pregame' and forecast['selected_outcome'] != expected:
            summary['policy_mismatches'].append(receipt)
        summary['fixtures'].append({
            'home': forecast['home'], 'away': forecast['away'], 'kickoff': forecast['kickoff'],
            'manual': manual, 'created_at': trial['created_at'], 'generated_at': forecast.get('generated_at'),
            'observed_at': forecast.get('observed_at'), 'status': forecast['status'], 'reason': forecast.get('reason'),
            'selection': forecast.get('selected_outcome'), 'best_outcome': best,
            'best_stressed_ev': analysis[best]['stressed_estimated_ev'] if best else None,
            'outcomes': analysis, 'settlement': receipt['settlement_status'], 'result': receipt.get('result'),
            'home_score': receipt.get('home_score'), 'away_score': receipt.get('away_score'),
            'profit': receipt.get('profit_units'), 'bookmaker': forecast['bookmaker'],
            'has_started': datetime.fromisoformat(forecast['kickoff'].replace('Z', '+00:00')) <= now,
        })
for manual, label in [(False, 'automatic'), (True, 'manual')]:
    rows = [row for row in summary['fixtures'] if row['manual'] == manual]
    summary[label] = {'fixtures': len(rows), 'statuses': dict(Counter(row['status'] for row in rows)),
        'settlements': dict(Counter(row['settlement'] for row in rows)),
        'selections': sum(bool(row['selection']) for row in rows),
        'selected_settled': sum(bool(row['selection']) and row['settlement'] == 'settled' for row in rows),
        'selected_pending': sum(bool(row['selection']) and row['settlement'] == 'pending' for row in rows),
        'past_pending': [row for row in rows if row['has_started'] and row['settlement'] == 'pending'],
        'exclusion_reasons': dict(Counter(row['reason'] or row['status'] for row in rows if row['status'] != 'recorded_pregame'))}
output = Path(__file__).with_name('paper-trial-audit-20261017.json')
output.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in summary.items() if key not in {'fixtures', 'batches'}}, indent=2))
print('BATCHES', json.dumps(summary['batches'], indent=2))
print('FIXTURES', json.dumps([{k: v for k, v in row.items() if k != 'outcomes'} for row in summary['fixtures']], indent=2))
