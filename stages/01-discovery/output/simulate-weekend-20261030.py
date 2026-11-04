"""Reproducible market-anchored scenario analysis; no production model changes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'weekend-market-scan-20261030-evening.json'
RUNS = 100_000
SEED = 20261030
# Secondary match forecasts displayed by RotoWire, retrieved through web tool.
# Page crawled 29 October; forecast issue times are unavailable.
SECONDARY_WEATHER = [(56, 5), (55, 7), (57, 5), (53, 3), (53, 6),
                     (52, 4), (53, 4), (47, 2), (54, 7)]
VENUES = [
    ('Stamford Bridge', 51.4817, -.1910, '2026-10-31T12:30:00+00:00'),
    ('Vitality Stadium', 50.7352, -1.8380, '2026-10-31T15:00:00+00:00'),
    ('Gtech Community Stadium', 51.4908, -.2887, '2026-10-31T15:00:00+00:00'),
    ('Coventry Building Society Arena', 52.5090, -1.4950, '2026-10-31T15:00:00+00:00'),
    ('MKM Stadium', 53.7460, -.3680, '2026-10-31T15:00:00+00:00'),
    ('Etihad Stadium', 53.4830, -2.2004, '2026-10-31T15:00:00+00:00'),
    ('Tottenham Hotspur Stadium', 51.6043, -.0664, '2026-10-31T17:30:00+00:00'),
    ('Villa Park', 52.5092, -1.8848, '2026-10-31T20:00:00+00:00'),
    ('Anfield', 53.4308, -2.9608, '2026-11-01T16:30:00+00:00'),
]
LINEUPS = [
    'Predicted only. Palmer expected back in newer previews; Starting11 suspension claim conflicts. Caicedo uncertain; James/Pedro absent. United Sesko/Shaw/Ugarte/Dorgu absent.',
    'Predicted only. Bournemouth midfield absences; Leeds Calvert-Lewin availability uncertain. Sources disagree on some midfield starters.',
    'Predicted only. Thiago and Delap projected up front. Yarmolyuk suspended; Forest Ndoye/Williams uncertain.',
    'Predicted only. Coventry Wright absent and Thomas uncertain; Sunderland Mukiele/Isidor uncertain.',
    'Predicted only. McBurnie and Emersonn projected up front. Hull defensive availability and Ipswich Lukic uncertain.',
    'Predicted only. Haaland projected to start; City Nunes and Brighton Kadioglu uncertain. Sources differ on Brighton attack.',
    'Predicted only. Marmoush and Mateta projected. Maddison uncertain; source disagreement on Palace goalkeeper.',
    'Predicted only. Jackson projected; Fulham striker selection differs between sources. Onana absent, Sessegnon suspended.',
    'Predicted only. Isak projected; Arsenal striker choice differs. Rice uncertain; Saka/Saliba reported absent.',
]
LINEUP_SOURCES = [
    'https://www.rotowire.com/soccer/lineups.php?week=31',
    'https://starting11.com/premier-league/gameweek/9',
    'https://www.sportsmole.co.uk/football/chelsea/injury-news/team-news/chelsea-vs-man-united-injury-suspension-list-predicted-xis_607953.html',
    'https://www.sportsmole.co.uk/football/chelsea/news/he-is-smart-alonso-backs-chelsea-star-palmer-to-deliver-positive-response-after-spurs-red_608086.html',
]


def probabilities(prices):
    inverse = 1 / np.asarray(prices, dtype=float)
    return inverse / inverse.sum()


def exact(rates):
    axis = np.arange(35)
    matrix = poisson.pmf(axis, rates[0])[:, None] * poisson.pmf(axis, rates[1])[None, :]
    assert abs(matrix.sum() - 1) < 1e-9
    return {'home': float(np.tril(matrix, -1).sum()), 'draw': float(np.trace(matrix)),
            'away': float(np.triu(matrix, 1).sum()),
            'over25': float(1 - poisson.cdf(2, sum(rates))),
            'btts': float((1 - np.exp(-rates[0])) * (1 - np.exp(-rates[1])))}


def fit_rates(row):
    over = np.mean([probabilities(p)[0] for p in row['totals25']['prices']])
    lo, hi = .01, 10.
    for _ in range(70):
        mid = (lo + hi) / 2
        if poisson.sf(2, mid) < over:
            lo = mid
        else:
            hi = mid
    total = (lo + hi) / 2
    target = np.mean([probabilities(p) for p in row['result']['prices']], axis=0)
    lo, hi = .001, total - .001
    for _ in range(70):
        mid = (lo + hi) / 2
        if exact([mid, total - mid])['home'] < target[0]:
            lo = mid
        else:
            hi = mid
    rates = np.array([(lo + hi) / 2, total - (lo + hi) / 2])
    assert abs(poisson.sf(2, total) - over) < 1e-9
    return rates, target.tolist()


def get_weather():
    params = {'latitude': ','.join(str(v[1]) for v in VENUES),
              'longitude': ','.join(str(v[2]) for v in VENUES),
              'hourly': 'temperature_2m,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m',
              'start_date': '2026-10-31', 'end_date': '2026-11-01', 'timezone': 'UTC'}
    try:
        response = requests.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=35)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) != len(VENUES):
            raise ValueError('Expected nine location forecasts')
        evidence = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'source_url': response.url,
                    'response': payload}
        (ROOT / 'weekend-weather-20261030.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        return payload, None
    except (requests.RequestException, ValueError) as exc:
        return None, type(exc).__name__


def main():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    weather, weather_error = get_weather()
    rng = np.random.default_rng(SEED)
    result = []
    for index, (row, venue) in enumerate(zip(data['fixtures'], VENUES)):
        rates, market_probs = fit_rates(row)
        conditions = None
        severe = False
        if weather:
            hourly = weather[index]['hourly']
            kickoff = datetime.fromisoformat(venue[3])
            available = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in hourly['time']]
            # Include the three hourly grid points nearest kickoff and the match window.
            positions = [i for i, time in enumerate(available) if -1800 <= (time - kickoff).total_seconds() <= 7200]
            conditions = {key: [values[i] for i in positions] for key, values in hourly.items()}
            severe = max(conditions['wind_speed_10m']) >= 25 or max(conditions['precipitation']) >= 2
        else:
            temperature_f, wind_mph = SECONDARY_WEATHER[index]
            conditions = {'source': LINEUP_SOURCES[0], 'quality': 'secondary_match_forecast_issue_time_unknown',
                          'page_crawled': '2026-10-29', 'temperature_c': round((temperature_f - 32) * 5 / 9, 1),
                          'wind_kmh': round(wind_mph * 1.609344, 1), 'displayed_rain_probability_pct': 0,
                          'hourly_grid_available': False}
        # Expected weather and known absences already influence public prices.
        # No unsupported deterministic adjustment or extra stadium boost is applied.
        draws = rng.poisson(rates, size=(RUNS, 2))
        totals = draws.sum(axis=1)
        metrics = {'home': float(np.mean(draws[:, 0] > draws[:, 1])),
                   'draw': float(np.mean(draws[:, 0] == draws[:, 1])),
                   'away': float(np.mean(draws[:, 0] < draws[:, 1])),
                   'over25': float(np.mean(totals >= 3)),
                   'btts': float(np.mean(np.all(draws > 0, axis=1)))}
        reference = exact(rates)
        assert abs(sum(metrics[k] for k in ['home', 'draw', 'away']) - 1) < 1e-12
        assert max(abs(metrics[k] - reference[k]) for k in metrics) < .008
        scores, counts = np.unique(draws, axis=0, return_counts=True)
        order = np.argsort(-counts)[:3]
        score_modes = [{'score': f'{scores[j, 0]}-{scores[j, 1]}', 'probability': float(counts[j] / RUNS)} for j in order]
        # These are transparent stress tests, not fitted player/weather effects.
        scenarios = {'home_attack_minus_10pct': [.9, 1], 'home_attack_plus_10pct': [1.1, 1],
                     'away_attack_minus_10pct': [1, .9], 'away_attack_plus_10pct': [1, 1.1],
                     'both_attack_minus_10pct': [.9, .9], 'both_attack_plus_10pct': [1.1, 1.1],
                     'adverse_weather_both_minus_5pct': [.95, .95]}
        if index == 0:
            scenarios['unexpected_Palmer_absence_illustrative'] = [.9, 1]
        if index == 5:
            scenarios['unexpected_Haaland_absence_illustrative'] = [.85, 1]
        if index == 6:
            scenarios['Maddison_absence_illustrative'] = [.9, 1]
        if index == 8:
            scenarios['unexpected_Isak_absence_illustrative'] = [.9, 1]
            scenarios['Rice_absence_opponent_attack_plus_5pct_illustrative'] = [1.05, 1]
        scenario_results = {name: {'goal_rates': (rates * factors).tolist(),
                                 'probabilities': exact(rates * factors)} for name, factors in scenarios.items()}
        result.append({'match': row['match'], 'stadium': venue[0], 'kickoff_utc': venue[3],
                       'coordinates_approximate': venue[1:3], 'lineup_status': 'predicted_unconfirmed',
                       'lineup_notes': LINEUPS[index], 'goal_rates': rates.tolist(), 'market_1x2': market_probs,
                       'probabilities': metrics, 'exact_check': reference,
                       'poisson_draw_residual_vs_market': reference['draw'] - market_probs[1],
                       'goal_total_90pct_predictive_interval': np.quantile(totals, [.05, .95]).tolist(),
                       'top_scores': score_modes, 'weather': conditions, 'adverse_weather_flag': severe,
                       'sensitivity': scenario_results,
                       'total_goal_sensitivity_range': [float(.9 * rates.sum()), float(1.1 * rates.sum())]})
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'runs_per_fixture': RUNS, 'seed': SEED,
              'input_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'method': 'Independent Poisson goals. Total fitted to mean devig O/U2.5; home rate fitted to mean devig home-win probability. Away/draw need not exactly match market. Central simulation retains market home advantage and known team-news/weather assumptions.',
              'lineup_sources': LINEUP_SOURCES,
              'fixture_source': 'https://www.premierleague.com/en/news/4688862/fixture-amendments-for-premier-league-matches-in-october-and-november',
              'weather_source': 'https://api.open-meteo.com/v1/forecast' if weather else LINEUP_SOURCES[0],
              'primary_weather_error': weather_error,
              'limits': ['Not an independently calibrated predictive model or evidence of an edge.',
                         'Starting XIs unconfirmed; named player effects and scenario probabilities not estimated.',
                         'Lineup attack +/-10% and adverse-weather -5% are illustrative stress assumptions, not empirically fitted effects.',
                         'Home advantage already in odds; stadium coordinates used for weather, no extra home boost.',
                         'Primary weather connection failed: secondary RotoWire match forecasts used, issue times unknown. No verified hourly stadium forecast; no deterministic weather adjustment.',
                         'Input market quotes from 30 October 22:25-22:26 EAT; Stake source timestamps unconfirmed.',
                         'Simulation count reduces numerical sampling error, not uncertainty in the assumptions.'],
              'fixtures': result}
    target = ROOT / 'weekend-simulation-20261030.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    for item in result:
        print(json.dumps({k: item[k] for k in ['match', 'stadium', 'goal_rates', 'probabilities', 'top_scores', 'weather', 'adverse_weather_flag']}))
    print('SAVED', target, 'WEATHER_ERROR', weather_error, 'CHECKS_PASSED', len(result))


if __name__ == '__main__':
    main()
