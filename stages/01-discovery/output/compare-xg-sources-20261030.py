import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from lxml import html

OUT = Path(__file__).resolve().parent
RAW = OUT / 'xg-sources-20261030'
ALIASES = {'Manchester United': 'Man United', 'Manchester City': 'Man City', 'Nottingham Forest': 'Forest',
           'Tottenham Hotspur': 'Tottenham', 'Brighton & Hove Albion': 'Brighton', 'Aston Villa': 'Villa',
           'Hull City': 'Hull', 'Coventry City': 'Coventry', 'Ipswich Town': 'Ipswich', 'Leeds United': 'Leeds',
           'Crystal Palace': 'Palace', 'AFC Bournemouth': 'Bournemouth'}


def canonical(name):
    for suffix in [' FC', ' AFC']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return ALIASES.get(name, name)


def first_number(text):
    return float(re.match(r'[-+]?\d+(?:\.\d+)?', text.strip()).group())


def main():
    document = html.fromstring((RAW / 'understat-rendered.html').read_bytes())
    tables = document.xpath('//table')
    understat = {}
    for row in tables[0].xpath('.//tbody/tr'):
        c = [' '.join(x.text_content().split()) for x in row.xpath('./td')]
        if len(c) != 12:
            raise ValueError('Unexpected Understat table schema')
        understat[canonical(c[1])] = {'matches': int(c[2]), 'goals': int(c[6]), 'conceded': int(c[7]),
            'xg_total': first_number(c[9]), 'xga_total': first_number(c[10]), 'xpoints': first_number(c[11])}
    assert len(understat) == 20 and {x['matches'] for x in understat.values()} == {8}
    # Every xG for must also be an opponent xGA, allowing rounding to two decimals.
    imbalance = sum(x['xg_total'] - x['xga_total'] for x in understat.values())
    assert abs(imbalance) <= .21
    footystats = {}
    for row in json.loads((RAW / 'footystats-table-rows.json').read_text(encoding='utf-8')):
        c = row['cells']
        name = row['team_label'][0]
        v = c[-7:]
        footystats[canonical(name)] = {'matches': int(v[0]), 'xg_per_match': float(v[1]),
            'xga_per_match': float(v[2]), 'goals_per_match': float(v[4]), 'conceded_per_match': float(v[5])}
    assert set(footystats) == set(understat)
    original = json.loads((OUT / 'weekend-form-comparison-20261030.json').read_text(encoding='utf-8'))
    previews = json.loads((RAW / 'xgstat-previews.json').read_text(encoding='utf-8'))
    fixtures = []
    for prior, preview in zip(original['fixtures'], previews):
        assert prior['match'] == preview['match']
        home, away = prior['match'].split('\u2013')
        for team, side in [(home, 'home'), (away, 'away')]:
            season = prior[side + '_season']
            assert understat[team]['goals'] == season['goals_for']
            assert understat[team]['conceded'] == season['goals_against']
        fixtures.append({'match': prior['match'], 'understat': {home: understat[home], away: understat[away]},
            'footystats': {home: footystats[home], away: footystats[away]}, 'xgstat': preview,
            'previous_market_probabilities': prior['market_baseline'],
            'previous_goals_only_models': prior['independent_goal_form_models']})
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'season': '2026/27',
        'checks': {'understat_teams': 20, 'matches_per_team': 8, 'xg_xga_total_imbalance': imbalance,
                   'goals_reconciled_with_all_18_fixture_teams': True},
        'sources': {'understat': 'https://understat.com/league/EPL',
                    'footystats': 'https://footystats.org/england/premier-league/xg'},
        'manifest': [{'path': str(p.relative_to(OUT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in [RAW / 'understat-rendered.html', RAW / 'footystats.html', RAW / 'xgstat-previews.json']],
        'limits': ['Provider xG models differ: totals are not interchangeable and are not averaged.',
                   'Understat and FootyStats table values describe historical chance creation; not fixture forecasts.',
                   'FootyStats upcoming fixture Home XG/Away XG values match historical venue averages, so not used as projected matchup means.',
                   'xgstat probabilities are third-party model outputs, not independently calibrated probabilities.',
                   'xgstat direct access returned 429/403; public previews verified through web retrieval.',
                   'Earlier goals-only probability ranges are not reliable after considering finishing regression; withdrawn as betting guidance.',
                   'No new lineup/weather adjustment or fresh bookmaker price refresh performed in this source comparison.'],
        'fixtures': fixtures}
    (OUT / 'weekend-xg-source-comparison-20261030.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# Premier League xG source comparison — 30 October 2026', '',
        'Understat rendered current-season table verified: 20 teams, eight games each. Goals reconcile with local records; xG and xGA totals differ by only 0.02 from rounding.',
        'FootyStats numeric table extracted; explanatory narrative contradicts some rankings. Provider values remain separate.',
        'xgstat public fixture previews provide projected goal means and published outcome probabilities. These have not been independently calibrated.', '',
        '| Match | xgstat projected goals H–A | xgstat published H/D/A | Understat season xG H/A | Understat season xGA H/A |',
        '|---|---:|---:|---:|---:|']
    for item in fixtures:
        home, away = item['match'].split('\u2013')
        h, a = item['understat'][home], item['understat'][away]
        preview = item['xgstat']
        goals = '–'.join(f'{x:.1f}' for x in preview['projected_goals'])
        probs = '/'.join(str(x) for x in preview['published_1x2_percent'])
        lines.append(f"| [{item['match']}]({preview['url']}) | {goals} | {probs}% | {h['xg_total']:.2f}/{a['xg_total']:.2f} | {h['xga_total']:.2f}/{a['xga_total']:.2f} |")
    lines += ['', 'These xgstat projections should not be relabelled as our simulation. Rounded outcome percentages may sum to 99 or 101.',
        '', '## Corrections to earlier conclusions', '',
        '- Withdraw Chelsea 62–74%, Brentford 57–66% and Tottenham 67–74% as betting guidance. Results-only fitting strongly rewards recent finishing and penalizes underperforming attacks.',
        '- Manchester City return to the favourite position in the xgstat projection. Understat season xG difference is City +8.97 and Brighton +6.69: both strong, unlike a confident Brighton preference from goals only.',
        '- United and Forest are creating substantially more than their goal totals imply; their poor results do not justify treating their attacks as intrinsically weak.',
        '- Keep source disagreement visible. No consensus average is manufactured and no robust betting edge is claimed.',
        '', 'Historical sources: https://understat.com/league/EPL and https://footystats.org/england/premier-league/xg',
        'Earlier studies retained unchanged for audit; this source comparison supersedes their confident outcome interpretations.']
    (OUT / 'weekend-xg-source-comparison-20261030.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(report['checks']))
    for item in fixtures:
        print(item['match'], item['xgstat']['projected_goals'], item['xgstat']['published_1x2_percent'])
    print('SAVED', OUT / 'weekend-xg-source-comparison-20261030.md')


if __name__ == '__main__':
    main()
