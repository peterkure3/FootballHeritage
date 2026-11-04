import json
from pathlib import Path
import tempfile
import unittest

from scripts.analyze_soccer_markets import read_json, score_probabilities


class SoccerMarketAnalysisTests(unittest.TestCase):
    def test_official_accented_names_survive_json_loading(self):
        names = ['1. FC Köln', 'CS Marítimo', 'Académico de Viseu FC', 'Real Sociedad de Fútbol', 'FC Famalicão']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixtures.json'
            path.write_text(json.dumps(names, ensure_ascii=False), encoding='utf-8')
            self.assertEqual(read_json(path), names)

    def test_goal_rate_orientation_and_normalization(self):
        p, _ = score_probabilities([2., .5])
        reverse, _ = score_probabilities([.5, 2.])
        self.assertAlmostEqual(sum(p.values()), 1)
        self.assertGreater(p['home_win'], p['away_win'])
        self.assertAlmostEqual(p['home_win'], reverse['away_win'])
