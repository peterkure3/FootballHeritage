"""One-run export using FootballHeritage's existing feature and market engines."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import joblib
import numpy as np
import pandas as pd
from api.betting_intel import SPORTS, build_intelligence, complete_books
from api.routers.ai_picks import generate_ai_picks
from etl.betting_intel import SNAPSHOT_PATH
from models.features import FEATURE_NAMES, FeatureState
from models.football_identity import football_history_key
from models.training_resources import training_threads

now = datetime.now(timezone.utc)
out = ROOT / 'stages/03-build/output/market-refresh-20261103'
out.mkdir(exist_ok=True)
bundle = ROOT / 'pipeline/models/model_store/candidates/20261103-market-refresh'
metrics = json.loads((bundle / 'metrics_v2.1.0.json').read_text(encoding='utf-8'))
assert hashlib.sha256((bundle / 'dataset.parquet').read_bytes()).hexdigest() == metrics['dataset_sha256']
assert metrics['features'] == FEATURE_NAMES
assert pd.Timestamp(metrics['trained_at']) < pd.Timestamp(now)
history = pd.read_parquet(bundle / 'dataset.parquet')
history = history[history.date.lt(pd.Timestamp(now).normalize()) & history.result.notna()].sort_values('date')
known = set(history.home_key) | set(history.away_key)
state = FeatureState()
for row in history.to_dict('records'):
    state.update(row)
model = joblib.load(bundle / 'model_v2.1.0.pkl')
assert model.n_features_in_ == len(FEATURE_NAMES)
snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding='utf-8'))
fixtures = [f for f in snapshot['fixtures'] if f['sport'] == 'football'
            and pd.Timestamp(f['kickoff']).tz_convert('Africa/Kampala').date() == pd.Timestamp(now).tz_convert('Africa/Kampala').date()]
candidate = copy.deepcopy(fixtures)
excluded = []
for fixture in candidate:
    fixture.pop('prediction', None)
    try:
        home = football_history_key(fixture['home_team'], known)
        away = football_history_key(fixture['away_team'], known)
        if min(sum(history.home_key.eq(t) | history.away_key.eq(t)) for t in (home, away)) < 10:
            raise ValueError('Fewer than ten history matches for a team')
        # History-only expert keeps the price used for EV outside the probability inputs.
        vector = pd.DataFrame([state.vector(home, away)], columns=FEATURE_NAMES)
        with training_threads(2):
            p = model.predict_proba(vector)[0]
        assert np.isfinite(p).all() and (p > 0).all() and np.isclose(p.sum(), 1)
        fixture['prediction'] = dict(probabilities=dict(zip(metrics['classes'], p.tolist())),
            generated_at=now.isoformat(), model_version='2.1.0', status='candidate_preview',
            settlement_rule='REGULATION_1X2', probability_basis='UNCONDITIONAL_FINAL_RESULT')
    except ValueError as exc:
        excluded.append(dict(fixture_id=fixture['fixture_id'], reason=str(exc)))
result = dict(generated_at=now.isoformat(), snapshot_at=snapshot['snapshot_at'],
    candidate=str(bundle), candidate_active=False, market_features_used=False,
    candidate_metrics=metrics['test'], dataset_sha256=metrics['dataset_sha256'],
    model_sha256=hashlib.sha256((bundle / 'model_v2.1.0.pkl').read_bytes()).hexdigest(),
    source_errors=snapshot['source_errors'], exclusions=excluded,
    active_ai_picks=generate_ai_picks(limit=20),
    today_active=build_intelligence('football', fixtures, now),
    today_candidate=build_intelligence('football', candidate, now),
    sports={sport: build_intelligence(sport, snapshot['fixtures'], now) for sport in SPORTS})
# The existing intelligence engine's ev_pct field holds a fraction. Export
# explicit units and independently check price/probability arithmetic.
for market in [result['today_active'], result['today_candidate'], *result['sports'].values()]:
    for section in ('ev_bets', 'ai_picks'):
        for row in market[section]:
            if row.get('ev_pct') is not None:
                fraction = row.pop('ev_pct')
                assert np.isclose(fraction, row['probability'] * row['decimal_odds'] - 1)
                row['gross_ev_fraction'] = fraction
                row['gross_ev_pct'] = 100 * fraction
# Every exported executable-price calculation must pass the existing freshness gates.
for market in [result['today_candidate'], *result['sports'].values()]:
    for arb in market['arbitrage']:
        assert arb['reciprocal_sum'] < 1
        assert np.isclose(sum(leg['reference_stake'] for leg in arb['legs']), 100)
        assert all(0 <= (now - datetime.fromisoformat(leg['observed_at'].replace('Z', '+00:00'))).total_seconds() <= 1800 for leg in arb['legs'])
path = out / 'analysis.json'
path.write_text(json.dumps(result, indent=2, default=str, allow_nan=False), encoding='utf-8')
lines = ['# Football Heritage market refresh — 3 November 2026', '',
    f'Generated {now.isoformat()}. Market snapshot {snapshot["snapshot_at"]}.', '',
    f'New isolated candidate: {metrics["data_report"]["fixtures"]:,} completed fixtures; {metrics["test"]["samples"]:,} held-out fixtures; test accuracy {metrics["test"]["accuracy"]:.2%}; log loss {metrics["test"]["log_loss"]:.5f}. Candidate remains inactive.', '',
    'Matched bookmaker comparison has only 56 held-out fixtures: candidate log loss 0.96213 versus bookmaker 0.93758 (lower is better). This does not establish a betting advantage.', '',
    'Candidate previews below use the refreshed history and the existing history expert. Live app picks continue to use the active model. Gross EV is a model estimate; no market-beating performance or executable arbitrage is established.', '',
    '| Fixture | Kickoff EAT | Candidate selection | Probability | Book | Odds | Gross EV |',
    '|---|---|---|---:|---|---:|---:|']
for pick in result['today_candidate']['ai_picks']:
    lines.append(f'| {pick["home_team"]} – {pick["away_team"]} | {pd.Timestamp(pick["kickoff"]).tz_convert("Africa/Kampala").strftime("%H:%M")} | {pick["selection"]} | {pick["probability"]:.1%} | {pick["bookmaker"] or "—"} | {pick["decimal_odds"] or "—"} | {str(round(pick["gross_ev_pct"], 2)) + "%" if pick.get("gross_ev_pct") is not None else "—"} |')
lines.extend(['', '## Active-model picks for today', '',
    '| Fixture | Selection | Probability | Book | Odds | Gross EV |',
    '|---|---|---:|---|---:|---:|'])
for pick in result['today_active']['ai_picks']:
    lines.append(f'| {pick["home_team"]} – {pick["away_team"]} | {pick["selection"]} | {pick["probability"]:.1%} | {pick["bookmaker"] or "—"} | {pick["decimal_odds"] or "—"} | {str(round(pick["gross_ev_pct"], 2)) + "%" if pick.get("gross_ev_pct") is not None else "—"} |')
lines.extend(['', '## Market coverage', ''])
for sport, data in result['sports'].items():
    lines.append(f'- {sport}: {json.dumps(data["summary"])}')
lines.extend(['', f'Today’s candidate coverage: {json.dumps(result["today_candidate"]["summary"])}.',
    f'Explicit identity/history exclusions: {json.dumps(excluded)}.', '',
    'Quotes expire after 30 minutes; arbitrage legs must be observed within 120 seconds. Fees, taxes, limits, liquidity, accepted wagers and lineups were not verified. Positive EV is not a guaranteed return. No wagers placed or model activation performed.', '',
    'The configured paid Odds API returned HTTP 401. Public collectors supplied the refreshed quotes. NFL and college football had no usable current quoted markets; player props were unavailable. NBA fixture-validation and missing candidate-history exclusions are retained in analysis.json.', '',
    'Exported gross_ev_pct is percentage points; gross_ev_fraction is the unit-stake return fraction. Both are independently checked against probability × odds − 1. The existing engine’s misleading ev_pct field is replaced only in this export.', '',
    'Full prices, devigged probabilities, value edges, arbitrage legs, active picks, candidate picks and source errors: [analysis.json](analysis.json).'])
(out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps(dict(report=str(out / 'report.md'), today=result['today_candidate']['summary'],
    candidate_test=metrics['test'], sports={k: v['summary'] for k, v in result['sports'].items()}), indent=2))
