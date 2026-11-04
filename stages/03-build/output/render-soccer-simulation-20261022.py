"""Verify a larger Monte Carlo sample and export offline distribution charts."""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from etl.fetch_soccer_events import DEFAULT_ROOT
sys.path.insert(0, str(DEFAULT_ROOT / '_tools'))
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from etl.soccer_event_dataset import load_match
from models.run_soccer_simulation import read_model
from models.soccer_players import roster_scenario
from models.soccer_possessions import summarize


def main() -> None:
    output = DEFAULT_ROOT / 'simulation-baseline'
    demo = json.loads((output / 'demo.json').read_text())
    inventory = json.loads((DEFAULT_ROOT / 'normalized/index.json').read_text())
    item = next(m for m in inventory['matches'] if m['match_id'] == demo['fixture_id'])
    record = load_match(DEFAULT_ROOT / 'normalized', item)
    teams = {t['side']: t['teamId'] for t in record['match']['teamsData'].values()}
    model, _ = read_model(output / 'England-model.json.gz')
    result = model.simulate(teams['home'], teams['away'], item['date'], 50000, 20261023)
    summary = summarize(result['samples'])
    comparison = {}
    for key, probability in summary['outcome'].items():
        small = demo['team_distribution']['outcome'][key]
        se = np.sqrt(probability * (1 - probability) * (1 / 50000 + 1 / 10000))
        comparison[key] = dict(probability_10000=small, probability_50000=probability,
                               absolute_difference=abs(small - probability),
                               approximate_difference_95_half_width=1.96 * se)
    verification = dict(fixture_id=item['match_id'], seed=20261023, runs=50000,
                        probabilities=summary, convergence=comparison,
                        limitation='Sampling-noise comparison only; model uncertainty and calibration are separate')
    (output / 'convergence.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
    with (output / 'distributions.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['distribution', 'outcome', 'probability'])
        for name in ['goal_difference', 'total_goals']:
            writer.writerows((name, outcome, probability) for outcome, probability in summary[name]['pmf'].items())
        writer.writerows(('scoreline', outcome, probability) for outcome, probability in summary['scorelines'].items())
    fig = make_subplots(rows=2, cols=2, subplot_titles=[
        'Scoreline probabilities', 'Home minus away goals', 'Total goals', 'Player shots — 250 trajectories'])
    max_goals = int(result['samples'][:, :, 0].max())
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for key, probability in summary['scorelines'].items():
        home, away = map(int, key.split('-'))
        matrix[home, away] = probability
    fig.add_trace(go.Heatmap(z=matrix, x=list(range(max_goals + 1)), y=list(range(max_goals + 1)),
                             colorscale='Blues', showscale=False,
                             hovertemplate='Home %{y}–%{x} Away<br>%{z:.2%}<extra></extra>'), row=1, col=1)
    for name, row, col in [('goal_difference', 1, 2), ('total_goals', 2, 1)]:
        pmf = summary[name]['pmf']
        fig.add_trace(go.Bar(x=[int(x) for x in pmf], y=list(pmf.values()),
                             marker_color='#176a61', showlegend=False,
                             hovertemplate='%{x}: %{y:.2%}<extra></extra>'), row=row, col=col)
    ranked = sorted(demo['player_distribution']['players'], key=lambda p:
                    demo['player_distribution']['players'][p]['shots']['mean'], reverse=True)[:8]
    for i, pid in enumerate(ranked):
        pmf = demo['player_distribution']['players'][pid]['shots']['pmf']
        name = demo['players'][pid]['name']
        fig.add_trace(go.Bar(x=[int(x) for x in pmf], y=list(pmf.values()), name=name,
                             visible=i == 0, marker_color='#b77928', showlegend=False,
                             hovertemplate='%{x} shots: %{y:.2%}<extra></extra>'), row=2, col=2)
    buttons = []
    for i, pid in enumerate(ranked):
        visible = [True, True, True] + [j == i for j in range(len(ranked))]
        buttons.append(dict(label=demo['players'][pid]['name'], method='restyle', args=['visible', visible]))
    fig.update_layout(height=850, width=1150, template='plotly_white',
                      title=dict(text=f"Historical simulation: {demo['label'].split(',')[0]}<br>"
                                 '<sup>50,000 team runs; player sample 250. Research baseline; distributions are not calibrated.</sup>'),
                      updatemenus=[dict(buttons=buttons, x=1, y=.5, xanchor='right')],
                      margin=dict(t=120, b=80))
    fig.update_xaxes(title_text='Away goals', row=1, col=1)
    fig.update_yaxes(title_text='Home goals', row=1, col=1)
    fig.update_xaxes(title_text='Goal difference', row=1, col=2)
    fig.update_xaxes(title_text='Total goals', row=2, col=1)
    fig.update_xaxes(title_text='Player shots', row=2, col=2)
    for row, col in [(1, 2), (2, 1), (2, 2)]:
        fig.update_yaxes(tickformat='.0%', title_text='Probability', row=row, col=col)
    fig.write_html(output / 'distributions.html', include_plotlyjs=True, full_html=True)
    # Explicit fixture inputs for exercising the batch CLI independently.
    players = json.loads((DEFAULT_ROOT / 'normalized/players.json').read_text())
    scenarios = roster_scenario(record['match'], players)
    fixtures = [dict(fixture_id=item['match_id'], kickoff=item['date'],
                     home_team_id=teams['home'], away_team_id=teams['away'], lineups=scenarios)]
    (output / 'example-fixtures.json').write_text(json.dumps(fixtures, indent=2), encoding='utf-8')
    print(json.dumps(dict(fixture_id=item['match_id'], convergence=comparison,
                         html=str(output / 'distributions.html')), indent=2))


if __name__ == '__main__':
    main()
