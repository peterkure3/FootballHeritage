"""Match current UCL quotes to official fixtures, forecast and simulate without publishing."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import unicodedata

import pandas as pd

from api.betting_intel import build_intelligence, complete_books, timestamp
from football_competitions import canonical_competition
from models.data import team_key
from models.football_identity import football_history_key
from models.league_data import identity, identity_aliases
from models.training_resources import training_threads
from scripts.analyze_soccer_markets import OUTCOMES, simulate
from scripts.export_market_report import candidate_preview, explicit_ev
from scripts.sync_bookmaker_grid import capture_cache_rejections

ALIASES = identity_aliases()
REVIEWED = {'aek': 'aek athens', 'fenerbahce sk': 'fenerbahce',
    'fenerbahce istanbul': 'fenerbahce', 'real betis balompie': 'real betis',
    'real betis seville': 'real betis', 'betis': 'real betis', 'psv': 'psv eindhoven',
    'sabah': 'sabah fk', 'sabah baku': 'sabah fk', 'sabah masazir': 'sabah fk',
    'viking': 'viking fk', 'slavia prague': 'slavia praha',
    'rasenballsport leipzig': 'rb leipzig', 'rc lens': 'lens', 'como calcio': 'como'}


def ascii_key(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))


def match_team(name: str) -> str:
    raw = ascii_key(team_key(name))
    if raw in REVIEWED:
        return REVIEWED[raw]
    value = ascii_key(identity(name, ALIASES))
    return REVIEWED.get(value, value)


def fixture_key(home: str, away: str, kickoff: str) -> tuple:
    return match_team(home), match_team(away), timestamp(kickoff)


def attach_quotes(capture: Path, official: list[dict], now: datetime) -> tuple[list[dict], dict]:
    fixtures = [{**row, 'fixture_id': 'official:' + row['provider_match_id'], 'sport': 'football',
                 'competition': 'UEFA Champions League', 'status': 'SCHEDULED',
                 'settlement_rule': 'REGULATION_1X2', 'offers': []} for row in official]
    lookup = {fixture_key(f['home_team'], f['away_team'], f['kickoff']): f for f in fixtures}
    if len(lookup) != len(fixtures):
        raise ValueError('Ambiguous official fixture identities')
    cache = capture_cache_rejections(capture)
    excluded = Counter()
    for line in (capture / 'odds_snapshots.jsonl').read_text(encoding='utf-8').splitlines():
        if not line:
            continue
        row = json.loads(line)
        if canonical_competition(row['competition'], row.get('country')) != 'UEFA Champions League':
            continue
        key = fixture_key(row['home_team'], row['away_team'], row['commence_time'])
        if key not in lookup:
            reason = 'reversed_home_away' if (key[1], key[0], key[2]) in lookup else 'not_official_today_fixture'
            excluded[f"{row['bookmaker']}:{reason}"] += 1
            continue
        observed = timestamp(row['observed_at'])
        updated = timestamp(row.get('source_updated_at'))
        reason = cache.get(row['bookmaker'])
        if observed is None or not 0 <= (now - observed).total_seconds() <= 900:
            reason = 'quote_not_fresh'
        elif updated is not None and not 0 <= (now - updated).total_seconds() <= 900:
            reason = 'upstream_update_not_fresh'
        elif (row.get('market') != 'h2h' or row.get('period') != 'FULL_TIME_90_MIN'
              or row.get('settlement_rule') != 'REGULATION_TIME' or row.get('is_live')
              or row.get('market_status') != 'OPEN' or key[2] <= now):
            reason = 'incompatible_or_started_market'
        outcomes = row['outcomes']
        if (len(outcomes) != 3 or {o['selection'] for o in outcomes} != {'HOME', 'DRAW', 'AWAY'}
                or any(not math.isfinite(float(o['odds_decimal']))
                       or float(o['odds_decimal']) <= 1 for o in outcomes)):
            reason = 'incomplete_market'
        elif row.get('market_status') != 'OPEN' or any(o.get('status') != 'OPEN' for o in outcomes):
            reason = 'availability_not_explicitly_open'
        if reason:
            excluded[f"{row['bookmaker']}:{reason}"] += 1
            continue
        book = row['bookmaker'] + ':' + str(row.get('region') or 'UNSPECIFIED')
        for outcome in outcomes:
            lookup[key]['offers'].append({'market': 'h2h', 'bookmaker': book,
                'selection': {'HOME': 'home_win', 'DRAW': 'draw', 'AWAY': 'away_win'}[outcome['selection']],
                'decimal_odds': float(outcome['odds_decimal']), 'observed_at': observed.isoformat(),
                'source_updated_at': row.get('source_updated_at'), 'source_url': row.get('source_url'),
                'snapshot_id': row['snapshot_id']})
    return fixtures, {'cache_rejections': cache, 'excluded': dict(excluded),
                      'sources': json.loads((capture / 'source_report.json').read_text(encoding='utf-8'))}


def run(capture: Path, form: Path, candidate: Path, output: Path, runs: int,
        previous: Path | None = None) -> dict:
    if runs < 10000:
        raise ValueError('Use at least 10,000 simulation draws')
    now = datetime.now(timezone.utc)
    official = json.loads((form / 'form.json').read_text(encoding='utf-8'))
    day = pd.Timestamp(now).tz_convert('Africa/Kampala').date()
    upcoming = [f for f in official['fixtures'] if f['competition'] == 'CL'
                and pd.Timestamp(f['kickoff']).tz_convert('Africa/Kampala').date() == day
                and timestamp(f['kickoff']) > now]
    fixtures, collection = attach_quotes(capture, upcoming, now)
    candidates, provenance = candidate_preview(fixtures, candidate, now)
    history = pd.read_parquet(candidate / 'dataset.parquet')
    history = history[pd.to_datetime(history.date, utc=True).lt(pd.Timestamp(now).normalize())
                      & history.result.notna()].sort_values('date')
    known = set(history.home_key) | set(history.away_key)
    active = copy.deepcopy(fixtures)
    active_errors = []
    from api.db import get_db_connection
    from models.predict_v2 import predict_match
    for fixture in active:
        try:
            with training_threads(2):
                prediction = predict_match(fixture['home_team'], fixture['away_team'],
                                           engine=get_db_connection(), cutoff=pd.Timestamp(now))
            fixture['prediction'] = {'probabilities': {key: prediction[name] for key, name in
                [('home_win', 'home_prob'), ('draw', 'draw_prob'), ('away_win', 'away_prob')]},
                'generated_at': now.isoformat(), 'model_version': prediction['model_version'],
                'status': 'active', 'settlement_rule': 'REGULATION_1X2'}
        except (ValueError, OSError, RuntimeError) as exc:
            active_errors.append({'fixture_id': fixture['fixture_id'], 'error': str(exc)})
    active_market = build_intelligence('football', active, now)
    candidate_market = build_intelligence('football', candidates, now)
    explicit_ev(active_market)
    explicit_ev(candidate_market)
    rows, simulation_errors = [], []
    for fixture in candidates:
        row = {**fixture}
        row.pop('home_form', None)
        row.pop('away_form', None)
        row['active_prediction'] = next(f.get('prediction') for f in active if f['fixture_id'] == fixture['fixture_id'])
        books = complete_books(fixture['offers'], OUTCOMES, timestamp(fixture['kickoff']), now)
        row['book_count'] = len(books)
        row['best_prices'] = []
        try:
            home = football_history_key(fixture['home_team'], known)
            away = football_history_key(fixture['away_team'], known)
            simulation = simulate(history, home, away, pd.Timestamp(now), runs,
                                  int(day.strftime('%Y%m%d')) + int(fixture['provider_match_id']))
            simulation['history_scope'] = 'Pooled supported competition results; not a fitted cross-league strength model'
            simulation['sampling_95_percent_intervals'] = {key: [max(0., p - 1.96 * math.sqrt(p * (1-p) / runs)),
                min(1., p + 1.96 * math.sqrt(p * (1-p) / runs))]
                for key, p in simulation['monte_carlo_probabilities'].items()}
            row['simulation'] = simulation
            probabilities = (fixture.get('prediction') or {}).get('probabilities', {})
            for selection in OUTCOMES if books else []:
                leg = max((book['legs'][selection] for book in books), key=lambda q: q['decimal_odds'])
                peers = [book for book in books if book['bookmaker'] != leg['bookmaker']]
                consensus = sum(b['fair_probabilities'][selection] for b in peers) / len(peers) if peers else None
                price = leg['decimal_odds']
                classifier = probabilities.get(selection)
                model_ev = classifier * price - 1 if classifier is not None else None
                sim_ev = simulation['probabilities'][selection] * price - 1
                stressed = max(0., classifier - .05) * price * .98 - 1 if classifier is not None else None
                sim_stressed = simulation['rate_stress_min_probability'][selection] * price * .98 - 1
                reference_times = [timestamp(book['legs'][selection]['observed_at']) for book in books]
                synchronized = (max(reference_times) - min(reference_times)).total_seconds() <= 120
                qualifies = (len(books) >= 3 and min(simulation['recent_team_games']) >= 10
                    and model_ev is not None and model_ev >= .05 and sim_ev >= .05
                    and stressed > 0 and sim_stressed > 0 and consensus is not None
                    and consensus * price > 1 and synchronized)
                row['best_prices'].append({**leg, 'model_probability': classifier,
                    'simulation_probability': simulation['probabilities'][selection], 'model_ev_fraction': model_ev,
                    'simulation_ev_fraction': sim_ev, 'other_book_probability': consensus,
                    'other_book_ev_fraction': consensus * price - 1 if consensus is not None else None,
                    'model_stress_ev_fraction': stressed, 'simulation_stress_ev_fraction': sim_stressed,
                    'qualifies_research_screen': bool(qualifies)})
        except ValueError as exc:
            simulation_errors.append({'fixture_id': fixture['fixture_id'], 'error': str(exc)})
        rows.append(row)
    prior = {}
    if previous is not None:
        previous_time = timestamp(json.loads((previous / 'source_report.json').read_text())['completed_at'])
        old_fixtures, _ = attach_quotes(previous, upcoming, previous_time)
        prior = {f['fixture_id']: complete_books(f['offers'], OUTCOMES, timestamp(f['kickoff']), previous_time)
                 for f in old_fixtures}
    for arb in candidate_market['arbitrage']:
        old = {book['bookmaker']: book for book in prior.get(arb['fixture_id'], [])}
        available = all(leg['bookmaker'] in old for leg in arb['legs'])
        previous_inverse = sum(1 / old[leg['bookmaker']]['legs'][leg['selection']]['decimal_odds']
                               for leg in arb['legs']) if available else None
        arb['same_legs_arbitrage_in_previous_capture'] = previous_inverse is not None and previous_inverse < 1
        arb['previous_inverse_sum'] = previous_inverse
        arb['hypothetical_2pct_payout_haircut_roi'] = .98 / arb['reciprocal_sum'] - 1
    result = {'generated_at': now.isoformat(), 'date_eat': str(day), 'capture': str(capture),
        'capture_sha256': hashlib.sha256((capture / 'odds_snapshots.jsonl').read_bytes()).hexdigest(),
        'form_capture': str(form), 'form_sha256': hashlib.sha256((form / 'form.json').read_bytes()).hexdigest(),
        'candidate': provenance, 'active_market': active_market, 'candidate_market': candidate_market,
        'fixtures': rows, 'collection': collection, 'active_errors': active_errors,
        'simulation_errors': simulation_errors, 'monte_carlo_draws': sum(r.get('simulation', {}).get('runs', 0) for r in rows),
        'active_model_changed': False, 'wagers_placed': False,
        'policy': {'max_quote_age_seconds': 900, 'max_cross_book_skew_seconds': 120,
                   'minimum_recent_games_for_screen': 10, 'lineups_verified': False}}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from scripts.report_champions_league import render
    render(output)
    print(json.dumps({'output': str(output), 'fixtures': len(rows), 'draws': result['monte_carlo_draws'],
                      'arbitrages': len(candidate_market['arbitrage']), 'simulation_errors': simulation_errors}, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'form', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--runs', type=int, default=1000000)
    args = parser.parse_args()
    run(args.capture, args.form, args.candidate, args.output, args.runs, args.previous)


if __name__ == '__main__':
    main()
