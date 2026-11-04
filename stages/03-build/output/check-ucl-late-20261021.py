"""Reprice verified causal history vectors; reject live and unsuitable quotes."""
import ast
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from models.data import team_key
from models.features import FEATURE_NAMES, FeatureState

spec = importlib.util.spec_from_file_location('repair', OUT / 'recalibrate-ucl-20261020.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
groups = ''
for node in ast.parse((OUT / 'analyze-ucl-20261021.py').read_text(encoding='utf-8')).body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'groups' for t in node.targets):
        groups = ast.literal_eval(node.value)
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'groups':
        groups += ast.literal_eval(node.value)
aliases = {team_key(v): line.split('|')[0] for line in groups.splitlines() for v in line.split('|')}
aliases.update({team_key('Internazionale'): 'Inter', team_key('LOSC Lille'): 'Lille', team_key('FC Bayern Munich'): 'Bayern Munich'})
def name(value):
    return aliases.get(team_key(value), repair.reviewed_name(value))

previous_path = OUT / 'ucl-picks-rechecked-20261021.json'
previous = json.loads(previous_path.read_text())
directory = ROOT / 'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020'
metrics = json.loads((directory / 'metrics_v2.1.0.json').read_text())
model_hash = hashlib.sha256((directory / 'model_v2.1.0.pkl').read_bytes()).hexdigest()
assert model_hash == metrics['model_sha256'] == previous['model_sha256']
history_path = ROOT / 'pipeline/data/raw/ucl_history_20261021/regulation_history.csv'
verification = json.loads((OUT / 'ucl-history-verification-20261021.json').read_text())
assert hashlib.sha256(history_path.read_bytes()).hexdigest() == verification['artifacts']['regulation_history.csv']['sha256']
model = joblib.load(directory / 'model_v2.1.0.pkl')
classes = metrics['classes']
pointer = json.loads((OUT / 'ucl-revision-inputs-20261021.json').read_text())
capture = Path(pointer['capture'])
audit = json.loads((capture / 'cache-audit.json').read_text())
now = pd.Timestamp.now(tz='UTC')
cache, usable = [], set()
for source in audit:
    response = source['http_audit'][-1] if source['http_audit'] else None
    reason = None
    if not response or source.get('http_status') != 200:
        reason = 'source_unavailable'
    else:
        hdr = response['headers']
        observed = pd.Timestamp(response['observed_at'])
        age = float(hdr.get('Age') or 0)
        if hdr.get('Date'):
            age = max(age, (observed - pd.Timestamp(parsedate_to_datetime(hdr['Date']))).total_seconds())
        if age > 120:
            reason = 'upstream_cache_older_than_120s'
        if source['bookmaker'] == 'bookmaker' and hdr.get('Last-Modified') and (observed - pd.Timestamp(parsedate_to_datetime(hdr['Last-Modified']))).total_seconds() > 300:
            reason = 'page_last_modified_older_than_300s_conservative_exclusion'
    cache.append({'bookmaker': source['bookmaker'], 'accepted': reason is None, 'reason': reason, 'headers': response['headers'] if response else {}})
    if reason is None:
        usable.add(source['bookmaker'])
quotes = [json.loads(line) for line in (capture / 'odds_snapshots_complete.jsonl').read_text().splitlines() if line]
results, excluded = [], []
for old in previous['matches']:
    home, away = old['home'], old['away']
    kickoff = pd.Timestamp(old['kickoff'])
    if kickoff <= now:
        excluded.append({'home': home, 'away': away, 'reason': 'kickoff_has_passed'})
        continue
    books = {}
    for q in quotes:
        if q['bookmaker'] not in usable:
            continue
        pair = (name(q['home_team']), name(q['away_team']))
        if set(pair) != {home, away} or abs((pd.Timestamp(q['commence_time']) - kickoff).total_seconds()) > 60:
            continue
        if q['sport'] != 'football' or q['market'] != 'h2h' or q['period'] != 'FULL_TIME_90_MIN' or q['settlement_rule'] != 'REGULATION_TIME' or q['is_live'] or q['market_status'] != 'OPEN':
            continue
        if len(q['outcomes']) != 3 or any(x['status'] != 'OPEN' for x in q['outcomes']):
            continue
        prices = {x['selection']: x['odds_decimal'] for x in q['outcomes']}
        if set(prices) != {'HOME', 'DRAW', 'AWAY'} or not all(np.isfinite(v) and v > 1 for v in prices.values()):
            continue
        values = [prices['HOME'], prices['DRAW'], prices['AWAY']] if pair[0] == home else [prices['AWAY'], prices['DRAW'], prices['HOME']]
        current = {'bookmaker': q['bookmaker'], 'prices': dict(zip(['home_win', 'draw', 'away_win'], values)), 'observed_at': q['observed_at'], 'source_url': q['source_url'], 'raw_capture_ref': q['raw_capture_ref']}
        if q['bookmaker'] not in books or pd.Timestamp(current['observed_at']) > pd.Timestamp(books[q['bookmaker']]['observed_at']):
            books[q['bookmaker']] = current
    qs = list(books.values())
    assert qs, (home, 'no verified open quotes')
    odds = {c: float(np.mean([q['prices'][c] for q in qs])) for c in classes}
    odds_vector = FeatureState().vector(home, away, odds)
    features = old['features'].copy()
    for feature in FEATURE_NAMES[:11] + ['odds_missing']:
        features[feature] = odds_vector[feature]
    assert all(features[f] == old['features'][f] for f in FEATURE_NAMES if f not in FEATURE_NAMES[:11] + ['odds_missing'])
    with threadpool_limits(limits=2):
        probabilities = model.predict_proba(pd.DataFrame([features], columns=FEATURE_NAMES))[0]
    assert np.isfinite(probabilities).all() and (probabilities > 0).all() and (probabilities < 1).all() and np.isclose(sum(probabilities), 1)
    consensus = np.mean([[1 / q['prices'][c] / sum(1 / v for v in q['prices'].values()) for c in classes] for q in qs], axis=0)
    best = {c: max(qs, key=lambda q: q['prices'][c]) for c in classes}
    reciprocal_sum = sum(1 / best[c]['prices'][c] for c in classes)
    result = {'home': home, 'away': away, 'kickoff': old['kickoff'], 'quotes': qs, 'probabilities': dict(zip(classes, map(float, probabilities))), 'consensus': dict(zip(classes, map(float, consensus))), 'best': {c: {'odds': best[c]['prices'][c], 'bookmaker': best[c]['bookmaker'], 'ev': float(probabilities[i] * best[c]['prices'][c] - 1), 'fair_odds': float(1 / probabilities[i])} for i, c in enumerate(classes)}, 'reciprocal_sum': reciprocal_sum, 'nominal_arb_roi': 1 / reciprocal_sum - 1, 'form': old['form'], 'features': features}
    results.append(result)
assert len(results) == 7 and len(excluded) == 2
report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'capture': str(capture), 'price_observed_at': sorted({q['observed_at'] for r in results for q in r['quotes']}), 'cache_validation': cache, 'excluded': excluded, 'model_sha256': model_hash, 'model_retrained': False, 'model_market_edge_proven': False, 'history_rows': previous['history_rows'], 'history_regulation_rows': previous['new_history_regulation_rows'], 'withheld_history_records': previous['withheld_history_records'], 'historical_vector_source': str(previous_path), 'historical_vector_source_sha256': hashlib.sha256(previous_path.read_bytes()).hexdigest(), 'matches': results}
output_name = sys.argv[1] if len(sys.argv) > 1 else 'ucl-late-scrapling-check-20261021.json'
assert Path(output_name).name == output_name and output_name.endswith('.json')
(OUT / output_name).write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'matches'}))
for r in results:
    print(json.dumps({k: v for k, v in r.items() if k not in ['features', 'form', 'quotes']} | {'form': {t: c['last_five'] for t, c in r['form'].items()}, 'books': [q['bookmaker'] for q in r['quotes']]}))
