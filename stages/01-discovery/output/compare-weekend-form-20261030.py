"""Compare independently measured league form with the earlier market simulation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CUTOFF = pd.Timestamp('2026-10-30T19:26:00Z')
ALIASES = {'Manchester United': 'Man United', 'Manchester City': 'Man City',
           'Nottingham Forest': 'Forest', 'Tottenham Hotspur': 'Tottenham',
           'Brighton & Hove Albion': 'Brighton', 'Aston Villa': 'Villa',
           'Hull City': 'Hull', 'Coventry City': 'Coventry', 'Ipswich Town': 'Ipswich',
           'Leeds United': 'Leeds', 'Crystal Palace': 'Palace', 'AFC Bournemouth': 'Bournemouth'}


def canonical(name):
    name = str(name).strip()
    for suffix in [' FC', ' AFC']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return ALIASES.get(name, name)


def load_history():
    processed = max((ROOT / 'pipeline/data/processed').glob('matches_processed*.parquet'), key=lambda p: p.stat().st_mtime)
    sources = [ROOT / 'pipeline/data/raw/historical/team_form_20261019.csv',
               ROOT / 'pipeline/data/raw/historical/team_form_leagues_20261025.csv', processed]
    frames, manifest = [], []
    for path in sources:
        f = pd.read_parquet(path) if path.suffix == '.parquet' else pd.read_csv(path)
        f = f[f.competition.isin(['PL', 'Premier League'])].copy()
        f['date'] = pd.to_datetime(f.date, utc=True)
        f = f[(f.date >= pd.Timestamp('2026-08-01', tz='UTC')) & (f.date < CUTOFF)]
        f['home_score'] = pd.to_numeric(f.home_score, errors='coerce')
        f['away_score'] = pd.to_numeric(f.away_score, errors='coerce')
        f = f.dropna(subset=['home_score', 'away_score'])
        f['home'] = f.home_team.map(canonical)
        f['away'] = f.away_team.map(canonical)
        f['day'] = f.date.dt.strftime('%Y-%m-%d')
        frames.append(f[['date', 'day', 'home', 'away', 'home_score', 'away_score']])
        manifest.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'eligible_rows': len(f)})
    combined = pd.concat(frames, ignore_index=True)
    keys = ['day', 'home', 'away']
    conflicts = combined.groupby(keys)[['home_score', 'away_score']].nunique().max(axis=1)
    if (conflicts > 1).any():
        raise ValueError('Conflicting result sources; cannot silently choose one')
    return combined.drop_duplicates(keys, keep='last').sort_values('date'), manifest


def stats(frame, team, venue=None, last=None):
    f = frame[(frame.home == team) | (frame.away == team)].copy()
    if venue:
        f = f[f[venue] == team]
    if last:
        f = f.tail(last)
    home = f.home == team
    gf = np.where(home, f.home_score, f.away_score).astype(int)
    ga = np.where(home, f.away_score, f.home_score).astype(int)
    outcomes = ['W' if a > b else 'D' if a == b else 'L' for a, b in zip(gf, ga)]
    return {'matches': len(f), 'form_oldest_to_newest': ''.join(outcomes),
            'wins': outcomes.count('W'), 'draws': outcomes.count('D'), 'losses': outcomes.count('L'),
            'points': outcomes.count('W') * 3 + outcomes.count('D'), 'goals_for': int(gf.sum()),
            'goals_against': int(ga.sum()), 'over25': int(((gf + ga) >= 3).sum()),
            'match_dates': f.day.tolist()}


def fit(frame, penalty):
    teams = sorted(set(frame.home) | set(frame.away))
    lookup = {team: i for i, team in enumerate(teams)}
    h = frame.home.map(lookup).to_numpy()
    a = frame.away.map(lookup).to_numpy()
    hg, ag = frame.home_score.to_numpy(), frame.away_score.to_numpy()
    n = len(teams)
    weights = np.exp(-np.log(2) * (CUTOFF - frame.date).dt.total_seconds().to_numpy() / (30 * 86400))
    weights /= weights.mean()
    # Opponent-adjusted goal model; attacks and defence weaknesses shrink to zero.
    def objective(params):
        attack = params[2:2+n] - params[2:2+n].mean()
        defence = params[2+n:] - params[2+n:].mean()
        lh = params[0] + params[1] + attack[h] + defence[a]
        la = params[0] + attack[a] + defence[h]
        loss = np.sum(weights * (np.exp(lh) - hg * lh + np.exp(la) - ag * la))
        return loss + penalty * (np.sum(attack**2) + np.sum(defence**2)) / 2
    initial = np.zeros(2 + 2*n)
    initial[0] = np.log(max(.1, ag.mean()))
    initial[1] = np.log(max(.1, hg.mean()) / max(.1, ag.mean()))
    result = minimize(objective, initial, method='L-BFGS-B', bounds=[(-2, 2)] * len(initial))
    if not result.success:
        raise ValueError('Optimizer did not converge')
    params = result.x
    attack = params[2:2+n] - params[2:2+n].mean()
    defence = params[2+n:] - params[2+n:].mean()
    def predict(home, away):
        rates = np.exp([params[0] + params[1] + attack[lookup[home]] + defence[lookup[away]],
                        params[0] + attack[lookup[away]] + defence[lookup[home]]])
        p = poisson.pmf(np.arange(35), rates[0])[:, None] * poisson.pmf(np.arange(35), rates[1])[None, :]
        assert abs(p.sum() - 1) < 1e-8
        assert (rates > 0).all()
        return {'goal_rates': rates.tolist(), 'home': float(np.tril(p, -1).sum()),
                'draw': float(np.trace(p)), 'away': float(np.triu(p, 1).sum()),
                'over25': float(poisson.sf(2, rates.sum()))}
    return predict


def main():
    frame, manifest = load_history()
    teams = sorted(set(frame.home) | set(frame.away))
    counts = {team: stats(frame, team)['matches'] for team in teams}
    print('COVERAGE', len(frame), counts)
    # Eight completed rounds are independently reported in contemporary previews.
    complete = len(frame) == 80 and len(teams) == 20 and set(counts.values()) == {8}
    frame.to_csv(OUT / 'weekend-form-results-20261030.csv', index=False)
    simulations = json.loads((OUT / 'weekend-simulation-20261030.json').read_text())
    models = {str(p): fit(frame, p) for p in [2, 4, 8]} if complete else {}
    fixtures = []
    for baseline in simulations['fixtures']:
        home, away = baseline['match'].split('\u2013')
        item = {'match': baseline['match'], 'home_last5': stats(frame, home, last=5),
                'away_last5': stats(frame, away, last=5), 'home_season': stats(frame, home),
                'away_season': stats(frame, away), 'home_at_home': stats(frame, home, venue='home'),
                'away_on_road': stats(frame, away, venue='away'),
                'market_baseline': baseline['probabilities'], 'market_goal_rates': baseline['goal_rates'],
                'independent_goal_form_models': {key: model(home, away) for key, model in models.items()}}
        fixtures.append(item)
        values = list(item['independent_goal_form_models'].values())
        print(json.dumps({'match': item['match'],
            'last5': [item['home_last5']['form_oldest_to_newest'], item['away_last5']['form_oldest_to_newest']],
            'last5_goals': [[item['home_last5']['goals_for'], item['home_last5']['goals_against']],
                            [item['away_last5']['goals_for'], item['away_last5']['goals_against']]],
            'home_win_range': [min(v['home'] for v in values), max(v['home'] for v in values)] if values else None,
            'away_win_range': [min(v['away'] for v in values), max(v['away'] for v in values)] if values else None,
            'total_goals_range': [min(sum(v['goal_rates']) for v in values), max(sum(v['goal_rates']) for v in values)] if values else None,
            'over25_range': [min(v['over25'] for v in values), max(v['over25'] for v in values)] if values else None}))
    output = {'created_at': datetime.now(timezone.utc).isoformat(), 'cutoff': CUTOFF.isoformat(),
              'sources': manifest, 'complete_eight_rounds': complete, 'team_match_counts': counts,
              'limits': ['No current shot-based xG available in these verified local result files.',
                         'Cup/European results excluded from quantitative model; considered separately from previews.',
                         'Current-season goal-form Poisson model is an exploratory cross-check, not validated betting probabilities.',
                         'Model jointly estimates attack/defence versus opponents, home advantage, 30-day recency half-life.',
                         'Ridge penalties 2,4,8 are sensitivity settings; none chosen by profitability or fixture outcomes.',
                         'Lineup and weather remain as prior scenario notes; no independent numerical player or weather adjustments.',
                         'Last-five summaries are descriptive; opponent strength is adjusted only in the exploratory goal model.',
                         'Incomplete coverage disables model fitting; missing games cannot be treated as absent results.'],
              'fixtures': fixtures}
    target = OUT / 'weekend-form-comparison-20261030.json'
    target.write_text(json.dumps(output, indent=2, allow_nan=False), encoding='utf-8')
    lines = ['# Premier League form comparison — 30 October 2026', '',
             'Verified coverage: 80 unique completed league results, eight per team. No conflicting source scores.',
             'Last-five sequences run oldest to newest. Cup/European results are excluded from quantitative comparisons.', '',
             'The form model is independent of bookmaker prices. It uses current-season goals, opponent-adjusted attack and defence, estimated home advantage and a 30-day recency half-life.',
             'Ranges show ridge-penalty sensitivity (2,4,8), not confidence intervals. Eight matches per team is too small to claim calibrated win probabilities or profitable edges.',
             'No independently verified current shot-level xG data was available; expected-goal estimates below are goal-model means, not measured chance quality.', '',
             '| Match | Home last 5 | Away last 5 | Earlier market total | Form total range | Earlier over 2.5 | Form over 2.5 range |',
             '|---|---|---|---:|---:|---:|---:|']
    for item in fixtures:
        values = list(item['independent_goal_form_models'].values())
        totals = [sum(v['goal_rates']) for v in values]
        overs = [v['over25'] * 100 for v in values]
        if values:
            lines.append(f"| {item['match']} | {item['home_last5']['form_oldest_to_newest']} | {item['away_last5']['form_oldest_to_newest']} | {sum(item['market_goal_rates']):.1f} | {min(totals):.1f}–{max(totals):.1f} | {item['market_baseline']['over25']*100:.0f}% | {min(overs):.0f}–{max(overs):.0f}% |")
    lines += ['', 'Qualitative cross-checks: Bournemouth have five consecutive wins across competitions, but only the latest two are league wins. Leeds have conceded six in eight league games, making an automatic goals-over call weak. Liverpool’s cup streak does not erase Arsenal’s strong league form.',
              '', 'Contemporary chance-creation check for City–Brighton: Sports Mole reports season xG 16.7 and 16.2 respectively, versus actual goals 20 and 23. This supports attacking quality but also warns that goals alone overstate finishing sustainability.',
              'Source: https://www.sportsmole.co.uk/football/man-city/feature/43-goals-in-eight-games-why-man-city-vs-brighton-could-be-premier-leagues-ultimate-attacking-test_608084.html',
              '', 'Updated team news: the Tottenham preview updated 30 October 18:42 reports Maddison available, superseding the earlier doubtful tag. This was not assigned a fabricated numerical effect.',
              'Source: https://www.sportsmole.co.uk/football/spurs/preview/spurs-vs-crystal-palace-prediction-team-news-lineups_607925.html',
              '', 'Results source provider: football-data.org, merged from the local manifests in the JSON report. Fresh Football-Data CSV and Understat requests both failed with connection errors; no claim of refreshed xG coverage.',
              'Full source hashes, match dates, venue splits and all model settings are in weekend-form-comparison-20261030.json.']
    (OUT / 'weekend-form-comparison-20261030.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('SAVED', target)


if __name__ == '__main__':
    main()
