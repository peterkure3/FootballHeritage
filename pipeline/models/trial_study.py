"""Aggregate frozen trial batches and assess one immutable prospective cohort."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models.validation import probability_metrics

PROTOCOL = {'minimum_selections': 200, 'minimum_fixture_days': 60,
            'bootstrap_samples': 10000, 'seed': 42, 'confidence': .95,
            'method': 'fixture-day cluster bootstrap', 'version': 1}
CLASSES = ['away_win', 'draw', 'home_win']


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def studies(batches: list[dict]) -> list[dict]:
    """Different candidate artifacts, policies and books never share a denominator."""
    from models.paper_trial import result_key
    grouped = {}
    for batch in batches:
        trial, receipt = batch['trial'], batch['receipt']
        identity = {'candidate_id': trial['candidate_id'],
                    'candidate_checksums': trial.get('candidate_checksums', {}),
                    'policy': trial['policy'],
                    'bookmakers': sorted({r['bookmaker'] for r in trial['fixtures']})}
        study_id = digest(identity)
        group = grouped.setdefault(study_id, {'study_id': study_id, **identity,
                                             'batch_count': 0, '_rows': {}})
        group['batch_count'] += 1
        if len(trial['fixtures']) != len(receipt['fixtures']):
            raise ValueError('Settlement fixture count mismatch')
        for forecast, result in zip(trial['fixtures'], receipt['fixtures']):
            key = result_key(forecast['home'], forecast['away'], forecast['kickoff'])
            entry = {'fixture_key': list(key), 'forecast': forecast, 'settlement': result,
                     'trial_sha256': batch['trial_sha256']}
            previous = group['_rows'].get(key)
            if previous:
                if digest(previous['forecast']) != digest(forecast):
                    raise ValueError('Conflicting duplicate forecast in frozen study')
                if previous['settlement'].get('result') and result.get('result') and previous['settlement']['result'] != result['result']:
                    raise ValueError('Conflicting duplicate settlement')
                if previous['settlement']['settlement_status'] == 'settled':
                    continue
            group['_rows'][key] = entry
    output = []
    for group in grouped.values():
        entries = sorted(group.pop('_rows').values(), key=lambda r: (r['fixture_key'][2], r['fixture_key'][:2]))
        selected = [e for e in entries if e['forecast'].get('selected_outcome')]
        bets = [e for e in selected if e['settlement']['settlement_status'] == 'settled']
        days = {e['fixture_key'][2][:10] for e in bets}
        profit = sum(e['settlement']['profit_units'] for e in bets)
        stressed = sum(e['settlement']['stressed_profit_units'] for e in bets)
        cohort = eligible_cohort(selected)
        valid_manifest = set(group['candidate_checksums']) >= {'dataset.parquet', 'model_v2.1.0.pkl', 'metrics_v2.1.0.json'}
        primary_policy = (group['bookmakers'] == ['bovada'] and group['policy'] == {
            'minimum_stressed_ev': .05, 'payout_haircut': .02, 'units_per_selection': 1,
            'max_selections_per_fixture': 1, 'settlement': 'REGULATION_TIME',
            'selection': 'largest_stressed_ev', 'max_quote_age_seconds': 900, 'no_threshold_tuning': True})
        group.update(entries=entries, settled_selections=len(bets), fixture_days=len(days),
            pending_selections=len(selected) - len(bets), recorded_selections=len(selected),
            profit_units=profit if bets else None, roi=profit / len(bets) if bets else None,
            stressed_roi=stressed / len(bets) if bets else None, protocol=PROTOCOL,
            selections_remaining=max(0, PROTOCOL['minimum_selections'] - len(bets)),
            days_remaining=max(0, PROTOCOL['minimum_fixture_days'] - len(days)),
            assessment_ready=bool(cohort and valid_manifest and primary_policy),
            assessment_status='ready' if cohort and valid_manifest and primary_policy else 'collecting',
            eligibility_note='Requires the frozen Bovada policy, artifact manifest, and all selections through the cohort day settled.',
            profitable_edge_established=False)
        output.append(group)
    return sorted(output, key=lambda group: group['study_id'])


def eligible_cohort(selected: list[dict]) -> list[dict]:
    """First complete chronological prefix reaching both gates, including its whole day."""
    by_day = defaultdict(list)
    for entry in selected:
        by_day[entry['fixture_key'][2][:10]].append(entry)
    cohort = []
    for day, rows in sorted(by_day.items()):
        if any(e['settlement']['settlement_status'] != 'settled' for e in rows):
            return []
        cohort.extend(rows)
        if len(cohort) >= PROTOCOL['minimum_selections'] and len({e['fixture_key'][2][:10] for e in cohort}) >= PROTOCOL['minimum_fixture_days']:
            return cohort
    return []


def assess(cohort: list[dict]) -> dict:
    from models.market_demo import paired_comparison
    dates = pd.Series([entry['fixture_key'][2] for entry in cohort])
    days = pd.to_datetime(dates, utc=True).dt.strftime('%Y-%m-%d').to_numpy()
    ordinary = np.array([e['settlement']['profit_units'] for e in cohort], dtype=float)
    stressed = np.array([e['settlement']['stressed_profit_units'] for e in cohort], dtype=float)
    blocks = [np.flatnonzero(days == day) for day in sorted(set(days))]
    if len(cohort) < PROTOCOL['minimum_selections'] or len(blocks) < PROTOCOL['minimum_fixture_days']:
        raise ValueError('Formal cohort thresholds not met')
    counts = np.array([len(block) for block in blocks])
    totals = np.array([[ordinary[b].sum(), stressed[b].sum()] for b in blocks])
    rng = np.random.default_rng(PROTOCOL['seed'])
    draws = rng.integers(0, len(blocks), size=(PROTOCOL['bootstrap_samples'], len(blocks)))
    returns = totals[draws].sum(axis=1) / counts[draws].sum(axis=1)[:, None]
    interval = np.quantile(returns, [.025, .975], axis=0)
    y = np.array([CLASSES.index(e['settlement']['result']) for e in cohort])
    model = np.array([[e['forecast']['outcomes'][k]['probability'] for k in CLASSES] for e in cohort])
    market = np.array([[e['forecast']['outcomes'][k]['bookmaker_margin_removed_probability'] for k in CLASSES] for e in cohort])
    cumulative = np.r_[0., stressed.cumsum()]
    passed = bool(interval[0, 1] > 0)
    return {'status': 'paper_evidence_passed' if passed else 'paper_evidence_not_established',
        'paper_evidence_passed': passed, 'profitable_edge_established': False,
        'selections': len(cohort), 'fixture_days': len(blocks), 'protocol': PROTOCOL,
        'roi': float(ordinary.mean()), 'stressed_roi': float(stressed.mean()),
        'roi_ci95': interval[:, 0].tolist(), 'stressed_roi_ci95': interval[:, 1].tolist(),
        'max_stressed_drawdown_units': float((np.maximum.accumulate(cumulative) - cumulative).max()),
        'model_metrics': probability_metrics(y, model, CLASSES),
        'market_metrics': probability_metrics(y, market, CLASSES),
        'paired_comparison': paired_comparison(y, model, market, dates,
            samples=PROTOCOL['bootstrap_samples'], seed=PROTOCOL['seed'], classes=CLASSES),
        'coverage': 'Selected fixtures in the frozen cohort; skipped fixtures remain in the trial ledger.',
        'limits': ['Paper prices are not confirmed executable; real-price availability and costs remain unverified.',
                   'Day resampling does not remove all team and season dependence.',
                   'One assessment per frozen study; a new policy/model needs independent validation.']}


def read_assessment(directory: Path, study_id: str) -> dict | None:
    manifest_path, result_path = directory / 'cohort.json', directory / 'assessment.json'
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['study_id'] != study_id or manifest['protocol'] != PROTOCOL:
        raise ValueError('Assessment study/protocol mismatch')
    if digest(manifest['entries']) != manifest['cohort_sha256']:
        raise ValueError('Frozen cohort integrity mismatch')
    if not result_path.exists():
        return {'status': 'cohort_frozen', 'cohort_sha256': manifest['cohort_sha256']}
    result = json.loads(result_path.read_text(encoding='utf-8'))
    if result['cohort_sha256'] != manifest['cohort_sha256'] or result['study_id'] != study_id:
        raise ValueError('Assessment does not belong to frozen cohort')
    return result


def assess_once(study: dict, root: Path) -> dict | None:
    directory = root / '_assessments' / study['study_id']
    existing = read_assessment(directory, study['study_id'])
    if existing and existing['status'] != 'cohort_frozen':
        return existing
    if not existing and not study['assessment_ready']:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'cohort.json'
    if not manifest_path.exists():
        entries = eligible_cohort([e for e in study['entries'] if e['forecast'].get('selected_outcome')])
        manifest = {'study_id': study['study_id'], 'protocol': PROTOCOL,
                    'frozen_at': datetime.now(timezone.utc).isoformat(),
                    'cohort_sha256': digest(entries), 'entries': entries}
        atomic_create(manifest_path, manifest)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    read_assessment(directory, study['study_id'])
    result = assess(manifest['entries']) | {'study_id': study['study_id'],
        'cohort_sha256': manifest['cohort_sha256'], 'assessed_at': datetime.now(timezone.utc).isoformat()}
    atomic_create(directory / 'assessment.json', result)
    return read_assessment(directory, study['study_id'])


def atomic_create(path: Path, payload: dict) -> None:
    """Publish complete JSON without replacing an existing study decision."""
    import os
    import tempfile
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.trial-')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        Path(temporary).unlink(missing_ok=True)
