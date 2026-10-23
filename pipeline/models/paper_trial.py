"""Immutable trial import and independently sourced regulation-time settlement."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import BASE_DIR, PROCESSED_DATA_DIR
from etl.utils import load_status_json
from models.football_identity import football_identity_key
from models.validation import probability_metrics

TRIAL_ROOT = PROCESSED_DATA_DIR / 'edge_trials'
CLASSES = ['away_win', 'draw', 'home_win']


def import_trial(source, root=TRIAL_ROOT):
    payload = Path(source).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    trial = json.loads(payload)
    if trial.get('status') != 'prospective_paper_trial' or trial.get('profitable_edge_established') is not False:
        raise ValueError('Expected a declared prospective paper trial')
    for row in trial['fixtures']:
        if row['status'] == 'recorded_pregame':
            generated = pd.Timestamp(row['generated_at'])
            observed = pd.Timestamp(row['observed_at'])
            kickoff = pd.Timestamp(row['kickoff'])
            if any(t.tzinfo is None for t in [generated, observed, kickoff]) or not observed <= generated < kickoff:
                raise ValueError('Forecast must be observed and generated before kickoff')
            if row.get('result') is not None or row.get('profit_units') is not None:
                raise ValueError('Forecast import must remain unsettled')
    directory = root / digest
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / 'trial.json'
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError('Trial integrity mismatch')
    else:
        with destination.open('xb') as stream:
            stream.write(payload)
    return directory


def result_key(home, away, kickoff):
    instant = pd.Timestamp(kickoff)
    if instant.tzinfo is None:
        raise ValueError('Results require an exact timezone-aware kickoff')
    return football_identity_key(home), football_identity_key(away), instant.tz_convert('UTC').isoformat()


def settle(trial, results):
    indexed = {}
    for result in results:
        key = result_key(result['home_team'], result['away_team'], result['commence_time'])
        indexed.setdefault(key, []).append(result)
    rows, labels, probabilities, market = [], [], [], []
    for forecast in trial['fixtures']:
        row = {key: forecast.get(key) for key in ['home','away','kickoff','bookmaker','selected_outcome','generated_at','status','reason']}
        row.update(settlement_status='ineligible' if forecast['status'] != 'recorded_pregame' else 'pending',
                   result=None, profit_units=None, stressed_profit_units=None)
        if forecast['status'] == 'recorded_pregame':
            matches = indexed.get(result_key(forecast['home'], forecast['away'], forecast['kickoff']), [])
            if len(matches) == 1:
                result = matches[0]
                scores = [result.get('home_score'), result.get('away_score')]
                observed = pd.Timestamp(result['observed_at'])
                if (result.get('status') == 'FINISHED' and result.get('settlement_rule') == 'REGULATION_TIME'
                    and all(type(score) is int and score >= 0 for score in scores)
                    and observed.tzinfo is not None and observed > pd.Timestamp(forecast['kickoff'])
                    and observed <= pd.Timestamp.now(tz='UTC') and result.get('source_url')):
                    winner = 'home_win' if scores[0] > scores[1] else 'away_win' if scores[1] > scores[0] else 'draw'
                    selection = forecast['selected_outcome']
                    price = forecast['outcomes'][selection]['decimal_odds'] if selection else None
                    profit = price - 1 if selection == winner else -1 if selection else 0
                    stressed = price * (1 - trial['policy']['payout_haircut']) - 1 if selection == winner else -1 if selection else 0
                    row.update(settlement_status='settled', result=winner, home_score=scores[0], away_score=scores[1],
                        profit_units=profit, stressed_profit_units=stressed, result_source=result)
                    labels.append(CLASSES.index(winner))
                    probabilities.append([forecast['outcomes'][key]['probability'] for key in CLASSES])
                    market.append([forecast['outcomes'][key]['bookmaker_margin_removed_probability'] for key in CLASSES])
            elif len(matches) > 1:
                row['settlement_status'] = 'ambiguous_result'
        if forecast.get('selected_outcome'):
            row['selection_evidence'] = forecast['outcomes'][forecast['selected_outcome']]
        rows.append(row)
    bets = [row for row in rows if row['settlement_status'] == 'settled' and row['selected_outcome']]
    units = len(bets)
    profit = sum(row['profit_units'] for row in bets)
    stressed = sum(row['stressed_profit_units'] for row in bets)
    return {'candidate_id': trial['candidate_id'], 'status': 'paper_trial', 'profitable_edge_established': False,
        'generated_at': datetime.now(timezone.utc).isoformat(), 'policy': trial['policy'], 'limits': trial['limits'],
        'fixtures': rows, 'settled_forecasts': len(labels), 'settled_selections': units,
        'pending_forecasts': sum(row['settlement_status'] == 'pending' for row in rows),
        'profit_units': profit if units else None, 'roi': profit / units if units else None,
        'stressed_roi': stressed / units if units else None,
        'model_metrics': probability_metrics(np.array(labels), np.array(probabilities), CLASSES) if labels else None,
        'market_metrics': probability_metrics(np.array(labels), np.array(market), CLASSES) if labels else None,
        'evidence_note': 'Batch totals are descriptive. Pending results are excluded from ROI. Use combined study progress for formal assessment.'}


def settle_directory(directory, results):
    payload = (directory / 'trial.json').read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != directory.name:
        raise ValueError('Trial checksum mismatch')
    report = settle(json.loads(payload), results) | {'trial_sha256': digest}
    path = directory / ('settlement_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    return report


def dashboard(root=TRIAL_ROOT):
    reports = []
    batches = []
    for trial in root.glob('*/trial.json'):
        if hashlib.sha256(trial.read_bytes()).hexdigest() != trial.parent.name:
            raise ValueError('Trial checksum mismatch')
        files = sorted(trial.parent.glob('settlement_*.json'))
        frozen = json.loads(trial.read_bytes())
        report = json.loads(files[-1].read_text(encoding='utf-8')) if files else settle(frozen, [])
        if files and report.get('trial_sha256') != trial.parent.name:
            raise ValueError('Settlement belongs to a different trial')
        report['trial_sha256'] = trial.parent.name
        # Derive summaries from original forecasts and result evidence, not editable totals.
        sources = [row['result_source'] for row in report['fixtures'] if row.get('result_source')]
        report = settle(frozen, sources) | {'trial_sha256': trial.parent.name,
                                          'generated_at': report['generated_at']}
        batches.append({'trial': frozen, 'receipt': report, 'trial_sha256': trial.parent.name})
        reports.append(report)
    from models.trial_study import studies, read_assessment
    summaries = studies(batches)
    for study in summaries:
        assessment = read_assessment(root / '_assessments' / study['study_id'], study['study_id'])
        study['assessment'] = assessment
        if assessment:
            study['assessment_status'] = assessment['status']
        study.pop('entries')
    health_path = BASE_DIR / 'logs' / 'edge_trial_status.json'
    health = load_status_json(health_path)
    return {'trials': sorted(reports, key=lambda row: row['generated_at'], reverse=True),
            'studies': summaries, 'collector': health, 'profitable_edge_established': False}
