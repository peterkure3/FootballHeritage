import json
import unittest

import pandas as pd
from bs4 import BeautifulSoup

from etl.regional_sportsbooks import normalize_bookmaker
from scripts.sync_bookmaker_grid import matched_grid_quotes

URL = 'https://lines.bookmaker.eu/en/sports/soccer/uefa-champions-league/'
OBSERVED = '2026-10-14T05:00:00Z'


def page():
    metadata = json.dumps({'@graph': [{'@type': 'WebPage', '@id': URL + '#webpage',
                                     'dateModified': '2026-10-14T04:27:05Z'}]})
    rows = ''
    path = '/en/sports/soccer/uefa-champions-league/liverpool-vs-lask/'
    for name, price in [('Liverpool FC', '-339'), ('LASK Linz', '+809'), ('Draw', '+534')]:
        team = f'<a href="{path}"><span>{name}</span></a>' if name != 'Draw' else name
        rows += f'<tr><th class="bm-team">{team}</th><td class="bm-c"></td><td class="bm-c"></td><td class="bm-c"><span class="bm-chip"><b>{price}</b><sup>up</sup></span></td></tr>'
    return f'''<link rel="canonical" href="{URL}">
      <h1>UEFA Champions League Live Betting Odds</h1>
      <script type="application/ld+json">{metadata}</script>
      <table><caption>UEFA Champions League games betting lines</caption>
      <thead><tr><th>Time</th><th>Team</th><th>Spread</th><th>Total</th><th><abbr>ML</abbr><span>Moneyline</span></th></tr></thead>
      <tbody data-game-row data-live="0" data-starts="2026-10-14T16:45:00Z">{rows}</tbody></table>'''


class BookmakerHtmlTests(unittest.TestCase):
    def parse(self, html):
        return normalize_bookmaker(str(html), OBSERVED, 'raw/bookmaker.html', 'run')

    def test_american_prices_provider_timestamp_and_fixture_orientation(self):
        records = self.parse(page())
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertEqual(row['source_updated_at'], '2026-10-14T04:27:05+00:00')
        self.assertEqual(row['observed_at'], OBSERVED)
        self.assertAlmostEqual(row['outcomes'][0]['odds_decimal'], 1 + 100 / 339)
        self.assertAlmostEqual(row['outcomes'][1]['odds_decimal'], 6.34)
        self.assertAlmostEqual(row['outcomes'][2]['odds_decimal'], 9.09)
        fixtures = pd.DataFrame([{'match_id': 1, 'date': '2026-10-14T16:45:00Z',
            'competition': 'UEFA Champions League', 'home_team': 'LASK Linz', 'away_team': 'Liverpool FC'}])
        matched = matched_grid_quotes(fixtures, records)
        self.assertEqual(len(matched), 1)
        self.assertAlmostEqual(matched.iloc[0].home_win, 9.09)
        self.assertAlmostEqual(matched.iloc[0].away_win, 1 + 100 / 339)
        self.assertTrue(matched_grid_quotes(fixtures.assign(date='2026-10-14T17:45:00Z'), records).empty)
        self.assertTrue(matched_grid_quotes(pd.concat([fixtures, fixtures.assign(match_id=2)]), records).empty)

    def test_rejects_live_past_suspended_missing_and_invalid_moneylines(self):
        for case in ['live', 'past', 'naive', 'suspended', 'title', 'missing', 'price', 'draw', 'link']:
            soup = BeautifulSoup(page(), 'html.parser')
            group = soup.select_one('tbody')
            chip = soup.select_one('.bm-chip')
            if case == 'live': group['data-live'] = '1'
            if case == 'past': group['data-starts'] = '2026-10-13T16:45:00Z'
            if case == 'naive': group['data-starts'] = '2026-10-14T16:45:00'
            if case == 'suspended': chip['class'] = 'bm-chip is-off'
            if case == 'title': chip['title'] = 'Suspended. Opened +100'
            if case == 'missing': chip.decompose()
            if case == 'price': chip.b.string = '0'
            if case == 'draw': group.select('tr')[-1].decompose()
            if case == 'link': soup.select('th.bm-team a')[1]['href'] = '/unrelated/'
            self.assertEqual(self.parse(soup), [], case)

    def test_schema_and_provider_time_must_be_verified(self):
        for case in ['header', 'league', 'metadata', 'future']:
            soup = BeautifulSoup(page(), 'html.parser')
            if case == 'header': soup.select('thead th')[-1].string = 'Draw No Bet'
            if case == 'league': soup.h1.string = 'Other League'
            if case == 'metadata': soup.script.decompose()
            if case == 'future': soup.script.string = soup.script.string.replace('04:27:05', '06:27:05')
            self.assertEqual(self.parse(soup), [], case)

    def test_even_money_is_supported(self):
        soup = BeautifulSoup(page(), 'html.parser')
        soup.select_one('.bm-chip b').string = 'EV'
        self.assertEqual(self.parse(soup)[0]['outcomes'][0]['odds_decimal'], 2)
