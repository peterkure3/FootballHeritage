"""Render captured UCL analysis and conservative research screens without fetching data."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import pandas as pd

OUTCOMES = ('home_win', 'draw', 'away_win')


def screen_price(pick: dict, simulation: dict) -> float | None:
    p = pick['model_probability']
    consensus = pick['other_book_probability']
    if p is None or p <= .05 or consensus is None:
        return None
    s = pick['simulation_probability']
    stress = simulation['rate_stress_min_probability'][pick['selection']]
    return max(1.05 / p, 1.05 / s, 1 / ((p - .05) * .98), 1 / (stress * .98), 1 / consensus)


def probabilities(values: dict | None) -> str:
    return '/'.join(f'{100 * values[k]:.1f}' for k in OUTCOMES) if values else 'Insufficient history'


def render(directory: Path) -> None:
    result = json.loads((directory / 'analysis.json').read_text(encoding='utf-8'))
    generated = pd.Timestamp(result['generated_at']).tz_convert('Africa/Kampala').isoformat()
    rows = result['fixtures']
    lines = [f"# Champions League analysis - {result['date_eat']}", '',
        f'Analysis time: {generated} (East Africa Time). Quotes are timestamped observations, not accepted wagers.', '',
        f"{len(rows)} official upcoming fixtures; {result['monte_carlo_draws']:,} seeded simulated score pairs.",
        f"Qualified research-screen picks: {sum(p['qualifies_research_screen'] for f in rows for p in f['best_prices'])}. "
        f"Fresh cross-book arbitrages: {len(result['candidate_market']['arbitrage'])}.", '',
        '## Forecasts', '', 'H/D/A means home win / draw / away win. All percentages use regulation time.', '',
        '| Fixture | Kickoff EAT | Books | Candidate H/D/A % | Monte Carlo H/D/A % | Recent games H/A |',
        '|---|---|---:|---|---|---|']
    for fixture in rows:
        simulation = fixture.get('simulation', {})
        lines.append(f"| {fixture['home_team']} - {fixture['away_team']} | "
            f"{pd.Timestamp(fixture['kickoff']).tz_convert('Africa/Kampala').strftime('%H:%M')} | "
            f"{fixture['book_count']} | {probabilities((fixture.get('prediction') or {}).get('probabilities'))} | "
            f"{probabilities(simulation.get('monte_carlo_probabilities'))} | "
            f"{'/'.join(map(str, simulation.get('recent_team_games', [])))} |")
    lines.extend(['', '## Observed prices and estimated edge', '',
        'A positive candidate EV is an unvalidated model estimate. The screen also requires simulation agreement,',
        'positive stress results, at least three books, ten recent games per team, synchronized quotes and positive other-book consensus EV.', '',
        '| Fixture | Selection | Best book | Odds | Candidate EV % | Simulation EV % | Other-book EV % | Screen | Watch price* |',
        '|---|---|---|---:|---:|---:|---:|---|---:|'])
    csv_rows = []
    for fixture in rows:
        for pick in fixture['best_prices']:
            threshold = screen_price(pick, fixture['simulation'])
            watch = math.ceil((threshold + 1e-10) * 100) / 100 if threshold is not None else None
            ev = lambda key: f"{100 * pick[key]:+.2f}" if pick[key] is not None else '-'
            lines.append(f"| {fixture['home_team']} - {fixture['away_team']} | {pick['selection']} | "
                f"{pick['bookmaker']} | {pick['decimal_odds']:.3f} | {ev('model_ev_fraction')} | "
                f"{ev('simulation_ev_fraction')} | {ev('other_book_ev_fraction')} | "
                f"{'Pass' if pick['qualifies_research_screen'] else 'No pick'} | {watch if watch else '-'} |")
            csv_rows.append({'home': fixture['home_team'], 'away': fixture['away_team'],
                'kickoff': fixture['kickoff'], 'selection': pick['selection'], 'bookmaker': pick['bookmaker'],
                'decimal_odds': pick['decimal_odds'], 'observed_at': pick['observed_at'],
                'model_ev_fraction': pick['model_ev_fraction'], 'simulation_ev_fraction': pick['simulation_ev_fraction'],
                'other_book_ev_fraction': pick['other_book_ev_fraction'], 'watch_price': watch,
                'qualifies_research_screen': pick['qualifies_research_screen']})
    fields = list(csv_rows[0]) if csv_rows else ['home', 'away', 'selection', 'decimal_odds']
    with (directory / 'markets.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    lines.extend(['', '*Watch prices hold all other inputs fixed and are rounded up to the next cent. They are numerical',
        'research-screen thresholds, not executable recommendations. Missing history or book coverage still disqualifies a fixture.', '',
        '## Arbitrage', ''])
    arbs = result['candidate_market']['arbitrage']
    if not arbs:
        lines.append('No arbitrage passed the existing identity, market, freshness and cross-book timing gates.')
    for arb in arbs:
        lines.append(f"- {arb['home_team']} - {arb['away_team']}: gross ROI {100 * arb['gross_roi']:.3f}%; "
            f"also present with the same legs in the prior capture: {arb['same_legs_arbitrage_in_previous_capture']}.")
        for leg in arb['legs']:
            lines.append(f"  - {leg['selection']}: {leg['bookmaker']} at {leg['decimal_odds']}; stake {leg['reference_stake']:.4f} per 100 total.")
    metrics = result['candidate']['test']
    manifest_path = next(Path(result['candidate']['bundle']).glob('metrics_v*.json'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    comparison = manifest.get('market_comparison', {})
    max_mc_error = max((abs(f['simulation']['monte_carlo_probabilities'][k] - f['simulation']['probabilities'][k])
        for f in rows if 'simulation' in f for k in OUTCOMES), default=0.)
    lines.extend(['', '## Training, checks and limitations', '',
        f"- New isolated candidate: {metrics['samples']:,} held-out fixtures, accuracy {metrics['accuracy']:.2%}, log loss {metrics['log_loss']:.5f}. No model promotion.",
        f"- Training corpus: {manifest['data_report']['fixtures']:,} completed fixtures; trained at {manifest['trained_at']}.",
        '- Current quoted prices are outside the candidate history-expert inputs. Active-model forecasts are separately stored in analysis.json.',
        f'- Maximum absolute Monte Carlo versus analytic Poisson probability difference: {100 * max_mc_error:.3f} percentage points.',
        '- Simulations use pooled supported-competition results from the prior 365 days and up to 20 games per team. They are not a fitted cross-league-strength or lineup-aware model.',
        '- Teams with three or eight observed games have sparse coverage; one million draws cannot fix missing history. Candidate forecasts require at least ten history matches per team.',
        '- Monte Carlo sampling intervals quantify draw noise only, not forecast uncertainty. The classifier and simulation share history and are not independent confirmations.',
        '- Scenario checks reduce classifier probability by five percentage points, vary each scoring rate by +/-15%, and apply a hypothetical 2% payout haircut. This is not a statement of actual tax.',
        '- Lineups, actual fees, taxes, account eligibility, limits and executable liquidity are unverified. No guaranteed return or proven betting advantage.',
        f"- Collection exclusions: `{json.dumps(result['collection']['excluded'])}`.",
        f"- Candidate exclusions: `{json.dumps(result['candidate']['exclusions'])}`.",
        f"- Capture: `{result['capture']}`; SHA-256 `{result['capture_sha256']}`.",
        f"- Candidate model SHA-256: `{result['candidate']['model_sha256']}`; dataset SHA-256: `{result['candidate']['dataset_sha256']}`.",
        '- [UEFA official fixture list](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-phase-fixtures/). Bookmaker source URLs and observation times are retained in analysis.json.',
        '- Source exclusions include reversed listings, stale caches and availability that is not explicitly open. These prices are not used to manufacture an arbitrage.',
        '- No wager was placed and the serving model was not changed.'])
    if comparison:
        lines.extend(['', f"On {comparison['model']['samples']} matched held-out fixtures, candidate log loss was "
            f"{comparison['model']['log_loss']:.5f} versus bookmaker {comparison['market']['log_loss']:.5f} "
            '(lower is better). This small comparison does not establish a betting advantage.'])
    (directory / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    render(parser.parse_args().directory)
