"""Portable replacement for dated market exports, using the existing quote gates."""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from api.betting_intel import MAX_QUOTE_AGE, SPORTS, build_intelligence, timestamp


def explicit_ev(market: dict) -> None:
    for section in ('ev_bets', 'ai_picks'):
        for row in market[section]:
            fraction = row.pop('ev_pct', None)
            if fraction is not None:
                expected = row['probability'] * row['decimal_odds'] - 1
                if not math.isfinite(fraction) or not math.isclose(fraction, expected, abs_tol=1e-10):
                    raise ValueError('Export EV differs from probability times decimal odds minus one')
                row.update(gross_ev_fraction=fraction, gross_ev_pct=100 * fraction)


def candidate_preview(fixtures: list[dict], bundle: Path, now: datetime) -> tuple[list[dict], dict]:
    import joblib
    import numpy as np
    import pandas as pd
    from config import MODEL_DIR
    from models.features import FEATURE_NAMES, FeatureState
    from models.football_identity import football_history_key
    from models.training_resources import training_threads

    bundle = bundle.resolve()
    if not bundle.is_relative_to((MODEL_DIR / 'candidates').resolve()):
        raise ValueError('Only locally produced model_store/candidates bundles may be loaded')
    manifests = list(bundle.glob('metrics_v*.json'))
    if len(manifests) != 1:
        raise ValueError('Candidate must have exactly one metrics manifest')
    metrics = json.loads(manifests[0].read_text(encoding='utf-8'))
    version = metrics['model_version']
    dataset = bundle / 'dataset.parquet'
    dataset_sha = hashlib.sha256(dataset.read_bytes()).hexdigest()
    if dataset_sha != metrics['dataset_sha256'] or metrics['features'] != FEATURE_NAMES:
        raise ValueError('Candidate dataset checksum or feature schema mismatch')
    trained = timestamp(metrics['trained_at'])
    if trained is None or trained >= now or set(metrics['classes']) != {'home_win', 'draw', 'away_win'}:
        raise ValueError('Invalid candidate training time or class contract')
    history = pd.read_parquet(dataset)
    dates = pd.to_datetime(history.date, utc=True)
    history = history[dates.lt(pd.Timestamp(now).normalize()) & history.result.notna()].sort_values('date')
    known = set(history.home_key) | set(history.away_key)
    state = FeatureState()
    for row in history.to_dict('records'):
        state.update(row)
    model_path = bundle / f'model_v{version}.pkl'
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    model = joblib.load(model_path)
    if model.n_features_in_ != len(FEATURE_NAMES):
        raise ValueError('Candidate model feature count mismatch')
    previews, exclusions = copy.deepcopy(fixtures), []
    for fixture in previews:
        fixture.pop('prediction', None)
        try:
            home = football_history_key(fixture['home_team'], known)
            away = football_history_key(fixture['away_team'], known)
            if min(int((history.home_key.eq(team) | history.away_key.eq(team)).sum()) for team in (home, away)) < 10:
                raise ValueError('Fewer than ten history matches for a team')
            vector = pd.DataFrame([state.vector(home, away)], columns=FEATURE_NAMES)
            with training_threads(2):
                probabilities = model.predict_proba(vector)[0]
            if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
                    or not np.isclose(probabilities.sum(), 1)):
                raise ValueError('Invalid candidate probabilities')
            fixture['prediction'] = {'probabilities': dict(zip(metrics['classes'], probabilities.tolist())),
                'generated_at': now.isoformat(), 'model_version': version, 'status': 'candidate_preview',
                'active': False, 'settlement_rule': 'REGULATION_1X2',
                'probability_basis': 'UNCONDITIONAL_FINAL_RESULT'}
        except ValueError as exc:
            exclusions.append({'fixture_id': fixture['fixture_id'], 'reason': str(exc)})
    return previews, {'bundle': str(bundle), 'active': False, 'model_sha256': model_sha,
                      'dataset_sha256': dataset_sha, 'test': metrics['test'], 'exclusions': exclusions}


def analyze(snapshot: dict, now: datetime, timezone_name: str = 'Africa/Kampala',
            candidate: Path | None = None) -> dict:
    observed = timestamp(snapshot.get('snapshot_at'))
    if observed is None or not 0 <= (now - observed).total_seconds() <= MAX_QUOTE_AGE:
        raise ValueError('Snapshot is missing, future-dated or older than 30 minutes; run the markets job')
    local = ZoneInfo(timezone_name)
    day = now.astimezone(local).date()
    fixtures = snapshot['fixtures']
    today = [f for f in fixtures if f['sport'] == 'football' and timestamp(f['kickoff'])
             and timestamp(f['kickoff']).astimezone(local).date() == day]
    result = {'generated_at': now.isoformat(), 'snapshot_at': snapshot['snapshot_at'],
              'date': str(day), 'timezone': timezone_name,
              'source_errors': snapshot.get('source_errors', []),
              'today_active': build_intelligence('football', today, now),
              'sports': {sport: build_intelligence(sport, fixtures, now) for sport in SPORTS},
              'candidate_active': False, 'active_models_changed': False}
    if candidate is not None:
        previews, provenance = candidate_preview(today, candidate, now)
        result.update(candidate=provenance, today_candidate=build_intelligence('football', previews, now))
    for market in [result['today_active'], *result['sports'].values(),
                   *([result['today_candidate']] if 'today_candidate' in result else [])]:
        explicit_ev(market)
    return result


def write_report(result: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    lines = [f"# Market report - {result['date']}", '',
             f"Generated {result['generated_at']}. Snapshot {result['snapshot_at']}.", '',
             'Prices pass the existing observation-age, kickoff, market and cross-book timing gates.',
             'Gross EV is a model estimate before fees, taxes and limits. No wagers or model activation performed.', '',
             '## Football picks for today', '',
             '| Fixture | Kickoff | Selection | Probability | Book | Odds | Gross EV % |',
             '|---|---|---|---:|---|---:|---:|']
    picks = result['today_active']['ai_picks']
    for row in picks:
        values = [f"{row['home_team']} - {row['away_team']}", row['kickoff'], row['selection'],
                  f"{row['probability']:.2%}", row.get('bookmaker') or '-', row.get('decimal_odds') or '-',
                  f"{row['gross_ev_pct']:.2f}" if row.get('gross_ev_pct') is not None else '-']
        lines.append('| ' + ' | '.join(str(v).replace('|', '/') for v in values) + ' |')
    if not picks:
        lines.extend(['', 'No eligible active-model picks for this date.'])
    lines.extend(['', '## Coverage and source failures', ''])
    for sport, market in result['sports'].items():
        lines.append(f"- {sport}: {json.dumps(market['summary'])}")
    lines.extend(['', 'Source errors: ' + json.dumps(result['source_errors']), '',
                  'Candidate previews, when explicitly requested, remain inactive. Full provenance and exclusions are in analysis.json.',
                  'Empty coverage means no eligible data; it does not establish that no opportunities exist.'])
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    fields = ['home_team', 'away_team', 'kickoff', 'selection', 'probability', 'bookmaker',
              'decimal_odds', 'gross_ev_fraction', 'gross_ev_pct']
    with (output / 'picks.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(picks)


def main() -> int:
    from etl.betting_intel import SNAPSHOT_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=SNAPSHOT_PATH)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, help='Explicit locally produced candidate; never auto-select or promote')
    parser.add_argument('--timezone', default='Africa/Kampala')
    args = parser.parse_args()
    snapshot_bytes = args.snapshot.read_bytes()
    result = analyze(json.loads(snapshot_bytes), datetime.now(timezone.utc), args.timezone, args.candidate)
    result['snapshot_sha256'] = hashlib.sha256(snapshot_bytes).hexdigest()
    write_report(result, args.output)
    print(json.dumps({'report': str(args.output / 'report.md'), 'source_errors': result['source_errors']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
