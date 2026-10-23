"""Freeze prematch soccer candidate forecasts; never claim estimated EV is profit."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from models.import_sportsbook_odds import normalize_snapshots
from models.sport_predict import candidate_directory, predict_candidate


def price_analysis(probabilities, prices, haircut=.02):
    if set(probabilities) != set(prices):
        raise ValueError("All model outcomes require matching actual prices")
    if not 0 <= haircut < 1:
        raise ValueError("Invalid payout stress")
    if any(not 0 <= p <= 1 for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 1e-6:
        raise ValueError("Invalid probability distribution")
    if any(not 1 < price < float('inf') for price in prices.values()):
        raise ValueError("Invalid decimal prices")
    inverse_sum = sum(1 / price for price in prices.values())
    return {outcome: {"probability": p, "decimal_odds": prices[outcome],
        "break_even_probability": 1 / prices[outcome],
        "bookmaker_margin_removed_probability": 1 / prices[outcome] / inverse_sum,
        "estimated_ev": p * prices[outcome] - 1,
        "stressed_estimated_ev": p * prices[outcome] * (1 - haircut) - 1}
        for outcome, p in probabilities.items()}


def run(source, output, candidate_id, match_date):
    payload = source.read_bytes()
    records = [json.loads(line) for line in payload.decode('utf-8').splitlines() if line.strip()]
    records = [r for r in records if r.get('country') == 'England' and
               r.get('competition') == 'Premier League' and r['commence_time'].startswith(match_date)]
    if not records:
        raise ValueError("No EPL snapshots for requested day")
    normalize_snapshots(records)
    directory = candidate_directory(candidate_id, 'football')
    history = pd.read_parquet(directory / 'dataset.parquet')
    metrics = json.loads((directory / 'metrics_v2.1.0.json').read_text(encoding='utf-8'))
    manifest = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                for name in ['dataset.parquet', 'model_v2.1.0.pkl', 'metrics_v2.1.0.json']}
    if manifest['dataset.parquet'] != metrics['dataset_sha256']:
        raise ValueError("Candidate dataset checksum mismatch")
    report = {'status': 'prospective_paper_trial', 'profitable_edge_established': False,
        'candidate_id': candidate_id, 'active_model_changed': False,
        'source': str(source.resolve()), 'source_sha256': hashlib.sha256(payload).hexdigest(),
        'candidate_checksums': manifest, 'created_at': datetime.now(timezone.utc).isoformat(),
        'policy': {'minimum_stressed_ev': .05, 'payout_haircut': .02,
                   'units_per_selection': 1, 'max_selections_per_fixture': 1,
                   'settlement': 'REGULATION_TIME', 'selection': 'largest_stressed_ev',
                   'max_quote_age_seconds': 900, 'no_threshold_tuning': True},
        'limits': ['Paper quotes are not confirmed executable prices.',
                   'Estimated EV depends on model calibration and is not demonstrated profit.',
                   'One bookmaker; no lineup or injury verification.',
                   'Previously inspected historical candidates are not fresh final validation.'],
        'fixtures': []}
    seen = set()
    for quote in records:
        identity = (quote['provider_event_id'], quote['bookmaker'])
        if identity in seen:
            raise ValueError("Duplicate fixture/book quote")
        seen.add(identity)
        now = pd.Timestamp.now(tz='UTC')
        observed = pd.Timestamp(quote['observed_at'])
        kickoff = pd.Timestamp(quote['commence_time'])
        row = {'home': quote['home_team'], 'away': quote['away_team'], 'kickoff': kickoff.isoformat(),
               'bookmaker': quote['bookmaker'], 'snapshot_id': quote['snapshot_id'],
               'observed_at': observed.isoformat(), 'source_updated_at': quote.get('source_updated_at'),
               'raw_capture_ref': quote['raw_capture_ref'], 'selected_outcome': None}
        if now >= kickoff or not 0 <= (now - observed).total_seconds() <= 900:
            row['status'] = 'excluded_started_or_stale_quote'
        elif pd.Timestamp(history.date.max()) >= observed or pd.Timestamp(metrics['trained_at']) >= observed:
            row['status'] = 'excluded_history_or_training_not_before_quote'
        else:
            prices = {dict(HOME='home_win', DRAW='draw', AWAY='away_win')[o['selection']]: o['odds_decimal']
                      for o in quote['outcomes']}
            try:
                with threadpool_limits(limits=1):
                    forecast = predict_candidate(candidate_id, 'football', quote['home_team'], quote['away_team'],
                        quote['commence_time'], home_odds=prices['home_win'], draw_odds=prices['draw'], away_odds=prices['away_win'])
                generated = pd.Timestamp.now(tz='UTC')
                if generated >= kickoff:
                    row['status'] = 'excluded_forecast_completed_after_kickoff'
                else:
                    analysis = price_analysis(forecast['probabilities'], prices)
                    best = max(analysis, key=lambda key: analysis[key]['stressed_estimated_ev'])
                    row.update(status='recorded_pregame', forecast=forecast, outcomes=analysis,
                               generated_at=generated.isoformat(), result=None, profit_units=None,
                               selected_outcome=best if analysis[best]['stressed_estimated_ev'] >= .05 else None)
            except ValueError as exc:
                row.update(status='excluded_model_input', reason=str(exc))
        report['fixtures'].append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({'output': str(output), 'fixtures': [
        {k: row.get(k) for k in ['home', 'away', 'status', 'selected_outcome', 'reason']}
        for row in report['fixtures']]}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-id', required=True)
    parser.add_argument('--match-date', required=True)
    args = parser.parse_args()
    run(args.source, args.output, args.candidate_id, args.match_date)


if __name__ == '__main__':
    main()
