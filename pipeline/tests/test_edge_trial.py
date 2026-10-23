import unittest

from scripts.record_edge_trial import price_analysis


class EdgeTrialTests(unittest.TestCase):
    def test_positive_ev_is_reduced_by_payout_stress(self):
        result = price_analysis({'home_win': .6, 'away_win': .4}, {'home_win': 2., 'away_win': 2.})
        self.assertAlmostEqual(result['home_win']['estimated_ev'], .2)
        self.assertAlmostEqual(result['home_win']['stressed_estimated_ev'], .176)
        self.assertAlmostEqual(result['home_win']['break_even_probability'], .5)

    def test_margin_removed_baseline_sums_to_one(self):
        result = price_analysis({'home_win': .5, 'draw': .3, 'away_win': .2},
                                {'home_win': 1.8, 'draw': 3., 'away_win': 4.})
        self.assertAlmostEqual(sum(row['bookmaker_margin_removed_probability'] for row in result.values()), 1.)

    def test_rejects_invalid_distribution_or_quotes(self):
        for probabilities, prices in [({'home_win': .5}, {'home_win': 2.}),
                                     ({'home_win': 1.}, {'away_win': 2.}),
                                     ({'home_win': 1.}, {'home_win': float('nan')}),
                                     ({'home_win': 1.}, {'home_win': 1.})]:
            with self.subTest(prices=prices), self.assertRaises(ValueError):
                price_analysis(probabilities, prices)


if __name__ == '__main__':
    unittest.main()
