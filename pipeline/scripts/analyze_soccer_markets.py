"""Read-only FootballHeritage forecasts, Poisson rollouts and matched price checks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from config import MODEL_DIR
from models.data import canonical_matches
from models.features import FEATURE_NAMES
from models.import_sportsbook_odds import normalize_snapshots
from models.league_data import identity, identity_aliases, load_histories, COMPETITION_CODES
from models.predict_football_leagues import league_state
from models.run_soccer_simulation import baseline_rates
from models.training_resources import training_threads
from scripts.sync_bookmaker_grid import capture_cache_rejections

OUTCOMES = ['home_win', 'draw', 'away_win']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def score_probabilities(rates):
    axis = np.arange(41)
    matrix = poisson.pmf(axis, rates[0])[:, None]*poisson.pmf(axis, rates[1])[None, :]
    values = np.array([np.tril(matrix, -1).sum(), np.trace(matrix), np.triu(matrix, 1).sum()])
    return dict(zip(OUTCOMES, (values/values.sum()).tolist())), matrix


def simulate(history, home, away, now, runs, seed):
    recent = history[history.date.ge(now-pd.Timedelta(days=365)) & history.date.lt(now.normalize())]
    if recent.empty:
        raise ValueError('No recent league score history')
    baseline = {'means': np.array([recent.home_score.mean(), recent.away_score.mean()]), 'teams': {}}
    counts = []
    for key, team in enumerate([home, away]):
        matches = recent[recent.home_key.eq(team)|recent.away_key.eq(team)].tail(20)
        home_side = matches.home_key.eq(team)
        goals = np.where(home_side, matches.home_score, matches.away_score)
        allowed = np.where(home_side, matches.away_score, matches.home_score)
        baseline['teams'][key] = [float(goals.sum()), float(allowed.sum()), len(matches)]
        counts.append(len(matches))
    rates = baseline_rates(baseline, 0, 1)
    if not np.isfinite(rates).all() or (rates<=0).any():
        raise ValueError('Invalid historical goal rates')
    analytic, matrix = score_probabilities(rates)
    sample = np.random.default_rng(seed).poisson(rates, size=(runs, 2))
    delta = sample[:, 0]-sample[:, 1]
    empirical = dict(zip(OUTCOMES, [float((delta>0).mean()), float((delta==0).mean()), float((delta<0).mean())]))
    if max(abs(empirical[k]-analytic[k]) for k in OUTCOMES)>.01:
        raise ValueError('Simulation/analytic distribution check failed')
    variants = [score_probabilities(rates*np.array([h, a]))[0] for h in [.85, 1.15] for a in [.85, 1.15]]
    scores = np.dstack(np.unravel_index(np.argsort(matrix.ravel())[-3:][::-1], matrix.shape))[0]
    return {'kind': 'FootballHeritage historical-score Poisson baseline', 'runs': runs, 'seed': seed,
        'goal_rates': rates.tolist(), 'recent_team_games': counts, 'probabilities': analytic,
        'monte_carlo_probabilities': empirical, 'rate_stress_min_probability': {k: min(p[k] for p in variants) for k in OUTCOMES},
        'over_2_5': float((sample.sum(axis=1)>2).mean()), 'btts': float((sample.min(axis=1)>0).mean()),
        'top_scores': [{'score': f'{h}-{a}', 'probability': float(matrix[h, a])} for h, a in scores]}


def run(capture, form, output, runs=100000, max_age=900):
    now = pd.Timestamp.now(tz='UTC'); day = now.tz_convert('Africa/Kampala').date()
    aliases = identity_aliases(); official = read_json(form/'form.json')
    fixtures = [f for f in official['fixtures'] if pd.Timestamp(f['kickoff']).tz_convert('Africa/Kampala').date()==day
                and pd.Timestamp(f['kickoff'])>now]
    lookup = {(identity(f['home_team'], aliases), identity(f['away_team'], aliases), pd.Timestamp(f['kickoff'])): f for f in fixtures}
    rejected = capture_cache_rejections(capture); grouped = defaultdict(dict); exclusions = Counter()
    rows = [json.loads(line) for line in (capture/'odds_snapshots.jsonl').read_text(encoding='utf-8').splitlines()]
    for row in rows:
        key = identity(row['home_team'], aliases), identity(row['away_team'], aliases), pd.Timestamp(row['commence_time'])
        if key not in lookup:
            exclusions['not_exact_today_official_fixture'] += 1; continue
        age = (now-pd.Timestamp(row['observed_at'])).total_seconds()
        if not 0<=age<=max_age:
            exclusions['stale_quote'] += 1; continue
        if row['collection_route']=='direct_public_feed' and row['bookmaker'] in rejected:
            exclusions[rejected[row['bookmaker']]] += 1; continue
        if row['collection_route']=='provider_feed' and row.get('source_updated_at'):
            if not 0<=(now-pd.Timestamp(row['source_updated_at'])).total_seconds()<=max_age:
                exclusions['stale_provider_update'] += 1; continue
        try:
            normalized = normalize_snapshots([row]).iloc[0]
        except ValueError:
            exclusions['invalid_market_contract'] += 1; continue
        quote = {'bookmaker': row['bookmaker'], 'observed_at': row['observed_at'], 'route': row['collection_route'],
            'source_updated_at': row.get('source_updated_at'), 'source_url': row['source_url'],
            'market_status': row['market_status'], 'prices': {k: float(normalized[k]) for k in OUTCOMES}}
        previous = grouped[key].get(row['bookmaker'])
        if previous is None or pd.Timestamp(quote['observed_at'])>pd.Timestamp(previous['observed_at']):
            grouped[key][row['bookmaker']] = quote
    registry = MODEL_DIR/'league_models'; histories = load_histories(aliases=aliases)
    fresh = pd.read_csv(form/'history.csv', low_memory=False)
    fresh['competition'] = fresh.competition.map(COMPETITION_CODES)
    for side in ['home', 'away']:
        fresh[side+'_team'] = fresh[side+'_team'].map(lambda value: identity(value, aliases))
    for code, block in fresh.groupby('competition'):
        combined = canonical_matches([histories.get(code, pd.DataFrame()), block])
        histories[code] = combined[combined.date.lt(now.normalize()) & combined.result.notna()].reset_index(drop=True)
    serving = registry/read_json(registry/'serving.json')['run_directory']
    serving_report = read_json(serving/'report.json')
    forecasts = []; model_cache = {}; model_histories = {}; coverage = Counter()
    for fixture in fixtures:
        code = fixture['competition']; home = identity(fixture['home_team'], aliases); away = identity(fixture['away_team'], aliases)
        key = home, away, pd.Timestamp(fixture['kickoff']); quotes = list(grouped.get(key, {}).values())
        row = {**fixture, 'canonical_home': home, 'canonical_away': away,
            'kickoff_eat': pd.Timestamp(fixture['kickoff']).tz_convert('Africa/Kampala').isoformat(), 'quotes': quotes}
        if code not in model_cache:
            candidates = [registry_path.parent for registry_path in registry.glob(f'*/{code}/metrics.json')]
            directory = serving/code if code in serving_report['leagues'] else max(candidates, default=None,
                key=lambda p: pd.Timestamp(read_json(p/'metrics.json')['trained_at']))
            if directory is not None:
                metrics = read_json(directory/'metrics.json')
                for file in ['model.pkl', 'dataset.parquet']:
                    if sha(directory/file)!=metrics[file.replace('.', '_')+'_sha256']:
                        raise ValueError('League model checksum mismatch')
                if pd.Timestamp(metrics['trained_at'])>now:
                    raise ValueError('Future-trained league model')
                trained = pd.read_parquet(directory/'dataset.parquet')
                identity_file = directory.parent/'league_identities.json'
                root_report = read_json(directory.parent/'report.json')
                if sha(identity_file)!=root_report['identity_sha256']:
                    raise ValueError('Frozen league identity dictionary changed')
                frozen_aliases = identity_aliases(identity_file)
                if directory.parent not in model_histories:
                    live = load_histories(aliases=frozen_aliases)
                    raw_form = pd.read_csv(form/'history.csv', low_memory=False)
                    raw_form['competition'] = raw_form.competition.map(COMPETITION_CODES)
                    for side in ['home', 'away']:
                        raw_form[side+'_team'] = raw_form[side+'_team'].map(lambda value: identity(value, frozen_aliases))
                    for league, part in raw_form.groupby('competition'):
                        merged = canonical_matches([live.get(league, pd.DataFrame()), part])
                        live[league] = merged[merged.date.lt(now.normalize()) & merged.result.notna()].reset_index(drop=True)
                    model_histories[directory.parent] = live
                model_cache[code] = (joblib.load(directory/'model.pkl'), metrics, directory,
                                    set(trained.home_key)|set(trained.away_key), frozen_aliases)
            else:
                model_cache[code] = None
        saved = model_cache[code]; history = histories.get(code)
        if saved is None or history is None:
            row['model_status'] = 'unsupported_history'; forecasts.append(row); continue
        model, metrics, directory, known, frozen_aliases = saved
        model_home = identity(fixture['home_team'], frozen_aliases)
        model_away = identity(fixture['away_team'], frozen_aliases)
        history = model_histories[directory.parent].get(code)
        if model_home not in known or model_away not in known or history is None:
            row['model_status'] = 'team_missing_from_training'; forecasts.append(row); continue
        state = league_state(history, now)
        vector = pd.DataFrame([state.vector(model_home, model_away)], columns=FEATURE_NAMES)
        with training_threads(2):
            p = model.predict_proba(vector)[0]
        if not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(), 1):
            raise ValueError('Invalid league probabilities')
        forecast = dict(zip(metrics['classes'], p.tolist()))
        simulation = simulate(history, model_home, model_away, now, runs, 20261101+int(fixture['provider_match_id']))
        row.update(model_status='forecast', probabilities=forecast, model_directory=str(directory),
            model_sha256=sha(directory/'model.pkl'), model_trained_at=metrics['trained_at'],
            model_identity_sha256=sha(directory.parent/'league_identities.json'),
            model_home_key=model_home, model_away_key=model_away,
            model_test=metrics['test'], market_features_used=False,
            history_through=history.date.max().isoformat(), simulation=simulation,
            generated_at=pd.Timestamp.now(tz='UTC').isoformat())
        best = []
        if quotes:
            fairs = {q['bookmaker']: {k: (1/q['prices'][k])/sum(1/v for v in q['prices'].values()) for k in OUTCOMES} for q in quotes}
            for outcome in OUTCOMES:
                quote = max(quotes, key=lambda q: q['prices'][outcome]); price = quote['prices'][outcome]
                others = [fair[outcome] for name, fair in fairs.items() if name!=quote['bookmaker']]
                consensus = float(np.mean(others)) if others else None
                model_ev = forecast[outcome]*price-1; sim_ev = simulation['probabilities'][outcome]*price-1
                stress_model = max(0, forecast[outcome]-.05)*price*.98-1
                stress_sim = simulation['rate_stress_min_probability'][outcome]*price*.98-1
                market_ev = consensus*price-1 if consensus is not None else None
                qualifies = (len(quotes)>=3 and min(simulation['recent_team_games'])>=10 and model_ev>=.05
                    and sim_ev>=.05 and stress_model>0 and stress_sim>0 and market_ev is not None and market_ev>0)
                best.append({'outcome': outcome, 'bookmaker': quote['bookmaker'], 'odds': price,
                    'observed_at': quote['observed_at'], 'model_probability': forecast[outcome],
                    'simulation_probability': simulation['probabilities'][outcome], 'model_ev': model_ev,
                    'simulation_ev': sim_ev, 'leave_one_book_out_probability': consensus, 'consensus_ev': market_ev,
                    'model_stress_ev': stress_model, 'simulation_stress_ev': stress_sim,
                    'qualifies': qualifies, 'price_improvement_vs_other_best': price/max(
                        [q['prices'][outcome] for q in quotes if q['bookmaker']!=quote['bookmaker']] or [price])-1})
            inv = sum(1/entry['odds'] for entry in best)
            row['best_price_inverse_sum'] = inv; row['quote_level_arbitrage_roi'] = 1/inv-1
            row['arbitrage_2pct_payout_stress_roi'] = .98/inv-1
            row['market_consensus'] = {k: float(np.mean([p[k] for p in fairs.values()])) for k in OUTCOMES}
        row['best_prices'] = best; row['eligible_book_count'] = len(quotes)
        coverage[code] += 1; forecasts.append(row)
    report = {'generated_at': pd.Timestamp.now(tz='UTC').isoformat(), 'date_eat': str(day), 'capture': str(capture),
        'capture_sha256': sha(capture/'odds_snapshots.jsonl'), 'form_capture': str(form), 'form_sha256': sha(form/'history.csv'),
        'fixtures': forecasts, 'coverage': dict(coverage), 'exclusions': dict(exclusions), 'direct_cache_rejections': rejected,
        'policy': {'max_quote_age_seconds': max_age, 'max_direct_upstream_cache_seconds': 120,
            'model_probability_stress_absolute': .05, 'goal_rate_stress': .15, 'hypothetical_payout_haircut': .02,
            'lineups_verified': False, 'period': 'REGULATION_90_MIN', 'promotional_early_payout_markets_excluded': True},
        'limitations': ['No guaranteed wins or verified market-beating model.', 'Quotes are observations, not confirmed accepted wagers.',
            'Pinnacle provider feed can be delayed; bookmakers and jurisdictions differ.',
            'Poisson score simulation is a historical-goal baseline, not a current player/possession model.',
            'Simulation draws reduce sampling error, not model uncertainty; no injury/lineup adjustment.',
            'EV and quote-level arbitrage are before actual fees/taxes/limits/void risk; stress is hypothetical, not a tax rule.'],
        'database_writes': False, 'active_models_changed': False}
    output.mkdir(parents=True, exist_ok=False)
    (output/'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    concise = []
    for f in forecasts:
        if f.get('model_status')!='forecast':
            continue
        pick = max(f['best_prices'], key=lambda p:min(p['model_ev'], p['simulation_ev']), default=None)
        concise.append({'home': f['home_team'], 'away': f['away_team'], 'time': f['kickoff_eat'], 'books': f['eligible_book_count'],
            'model': f['probabilities'], 'simulation': f['simulation']['probabilities'], 'best_joint_candidate': pick,
            'arb_roi': f.get('quote_level_arbitrage_roi')})
    print(json.dumps({'coverage': dict(coverage), 'exclusions': dict(exclusions), 'fixtures': concise}, indent=2))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['capture', 'form', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--runs', type=int, default=100000)
    parser.add_argument('--max-age', type=int, default=900)
    args = parser.parse_args(); run(args.capture, args.form, args.output, args.runs, args.max_age)
