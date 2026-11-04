"""Independently verify the evidence ledger and write a compact review artifact."""
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
paths = sorted((ROOT / 'today-prediction-evidence-20261010').glob('*-evaluation.json'))
path = paths[-1]
report = json.loads(path.read_text(encoding='utf-8'))
for capture in report['source_captures']:
    assert hashlib.sha256(Path(capture['raw_capture']).read_bytes()).hexdigest() == capture['source_sha256']
rows = report['database_forecast_rows']
assert len({(r['match_id'], r['model_version']) for r in rows}) == len(rows)
assert all(r['evaluation_status'] == 'eligible' for r in rows)
keys = {'home_win': 'home_prob', 'draw': 'draw_prob', 'away_win': 'away_prob'}
ledger = []
for row in rows:
    result = row['official_result']
    assert result['provider_event_id'] == row['match_id']
    assert datetime.fromisoformat(row['created_at']) < datetime.fromisoformat(row['date'])
    assert result['status'] == 'FINISHED' and result['duration'] == 'REGULAR'
    assert abs(sum(row[k] for k in keys.values()) - 1) < 1e-9
    actual = 'home_win' if result['home_score'] > result['away_score'] else 'away_win' if result['home_score'] < result['away_score'] else 'draw'
    assert actual == result['result']
    assert row['is_correct'] == (row['winner'] == actual)
    ledger.append({'match': row['home_team'] + ' vs ' + row['away_team'],
        'model_version': row['model_version'], 'prediction_id': row['prediction_id'],
        'generated_at': row['created_at'], 'kickoff': row['date'], 'pick': row['winner'],
        'pick_probability': row[keys[row['winner']]], 'draw_probability': row['draw_prob'],
        'score': f"{result['home_score']}-{result['away_score']}", 'actual': actual,
        'correct': row['is_correct'], 'provenance_recorded': row['provenance'] is not None})
for version, metrics in report['model_metrics'].items():
    subset = [row for row in rows if row['model_version'] == version]
    assert metrics['samples'] == len(subset)
    assert abs(metrics['accuracy'] - sum(r['is_correct'] for r in subset) / len(subset)) < 1e-12
    loss = sum(-math.log(r[keys[r['official_result']['result']]]) for r in subset) / len(subset)
    brier = sum(sum((r[keys[k]] - int(k == r['official_result']['result'])) ** 2 for k in keys) for r in subset) / len(subset)
    assert abs(loss - metrics['log_loss']) < 1e-12
    assert abs(brier - metrics['brier_score']) < 1e-12
trial = report['frozen_trials']['trials'][0]
settled = [r for r in trial['fixtures'] if r['settlement_status'] == 'settled' and r['selected_outcome']]
profits = [r['selection_evidence']['decimal_odds'] - 1 if r['selected_outcome'] == r['result'] else -1 for r in settled]
assert len(settled) == trial['settled_selections']
assert abs(sum(profits) - trial['profit_units']) < 1e-12
assert abs(sum(profits) / len(profits) - trial['roi']) < 1e-12
csv_path = ROOT / 'today-prediction-ledger-20261010.csv'
with csv_path.open('w', newline='', encoding='utf-8') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(ledger[0]))
    writer.writeheader()
    writer.writerows(ledger)
lines = ['# Today’s prediction evidence — 10 October 2026', '',
    '**No profitable edge established.** All six accessible EPL fixtures are final. Active v2.0.0 picked 3/6 winners (50%). Frozen candidate v2.1.0 picked 2/5 winners (40%); Sunderland was excluded for missing training history.', '',
    '| Fixture | Active pick | Pick probability | Draw probability | Final score | Correct |',
    '|---|---|---:|---:|---|---|']
for row in ledger:
    lines.append(f"| {row['match']} | {row['pick']} | {row['pick_probability']:.1%} | {row['draw_probability']:.1%} | {row['score']} | {'Yes' if row['correct'] else 'No'} |")
lines += ['', '## Frozen value policy, declared before kickoff', '',
    '| Fixture | Selection | Recorded odds | Profit in paper units |', '|---|---|---:|---:|']
for row in settled:
    lines.append(f"| {row['home']} vs {row['away']} | {row['selected_outcome']} | {row['selection_evidence']['decimal_odds']:.2f} | {row['profit_units']:+.2f} |")
lines += ['', '**Four units staked; 3.5 returned; −0.5 net; ROI −12.5%.** With the declared 2% payout reduction, ROI is −14.25%. United had no eligible value selection. Forecast weights and selection thresholds remain frozen.', '',
    '## Probability comparison', '',
    '| Cohort | Log loss (lower is better) | Multiclass Brier score (lower is better) |', '|---|---:|---:|',
    f"| Active v2.0.0, six matches | {report['model_metrics']['2.0.0']['log_loss']:.4f} | {report['model_metrics']['2.0.0']['brier_score']:.4f} |",
    f"| Candidate v2.1.0, five matches | {trial['model_metrics']['log_loss']:.4f} | {trial['model_metrics']['brier_score']:.4f} |",
    f"| Frozen Bovada probability baseline, same five matches | {trial['market_metrics']['log_loss']:.4f} | {trial['market_metrics']['brier_score']:.4f} |", '',
    'The candidate was worse than the bookmaker baseline on both probability metrics today. The active model uses a different six-game cohort, so these rows do not establish which model is better.', '',
    '## Coverage and verification', '',
    '- The account-wide official `/matches` endpoint returned zero in its TIER_ONE scope. The accessible `/competitions/PL/matches` endpoint returned all six EPL fixtures. Empty global scope is not evidence that no other games occurred.',
    '- The database has six dated football fixtures for today, each with a valid pregame prediction. No additional dated football forecasts were available for today. Existing sport model previews are not a frozen prospective trial.',
    '- Independently checked capture hashes, exact provider IDs/teams/UTC kickoff joins, pregame timestamps, probability sums, all six outcomes, accuracy/log loss/Brier arithmetic, and four paper bet settlements. Frozen trial import and dashboard enforce the immutable trial checksum.',
    '- Active forecasts use the latest valid stored prediction before kickoff, which may differ from the one shown at the user’s 14:27 EAT bet placement. Five latest forecasts have saved regional audit provenance; Arsenal’s older forecast lacks that audit record. The exact displayed model remains unconfirmed.',
    '- Results were saved in separate trial settlement receipts and this audit. No active model, application match rows, training data, or selection thresholds were changed.',
    '- No post-result predictions were generated or counted. No retrospective threshold search was treated as fresh evidence.',
    '- The frozen prospective protocol requires at least 200 settled selections across 60 distinct fixture days before its formal assessment, with a positive lower bound on the stressed ROI interval and calibration/market comparisons. Current progress: 4 selections, 1 day.', '',
    '## Evidence files', '',
    f'- Detailed audit: `{path.relative_to(ROOT).as_posix()}`',
    '- Flat forecast ledger: `today-prediction-ledger-20261010.csv`',
    '- Official source: https://api.football-data.org/v4/competitions/PL/matches?dateFrom=2026-10-10&dateTo=2026-10-10',
    '- Web corroboration: https://www.skysports.com/football/aston-villa-vs-brentford/report/559495 ; https://www.tntsports.co.uk/football/premier-league/2026-2027/live-ipswich-town-fulham_mtc21883056/live.shtml ; https://www.tntsports.co.uk/football/premier-league/2026-2027/live-sunderland-brighton-hove-albion_mtc21883173/live.shtml', '',
    '## Next evidence collection', '',
    'Continue the existing daily regional collector before kickoff; it captures prices, appends active forecasts with provenance, extends the frozen Bovada candidate study for unseen fixtures, and refreshes prior pending results. Do not retrain or change the frozen study in response to these six outcomes. A new model or policy needs a separate trial. Broader league/sport evidence requires forecasts and quotes recorded prospectively before evaluating results; completed games cannot be converted into new forward predictions.', '']
(ROOT / 'today-prediction-evidence-20261010.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'verified': True, 'forecast_rows': len(ledger), 'correct': sum(r['correct'] for r in ledger),
    'settled_paper_bets': len(settled), 'paper_profit': sum(profits), 'paper_roi': trial['roi'],
    'active_provenance_rows': sum(r['provenance_recorded'] for r in ledger), 'summary': str(ROOT / 'today-prediction-evidence-20261010.md')}))
