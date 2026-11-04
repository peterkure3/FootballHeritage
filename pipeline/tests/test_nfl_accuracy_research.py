import unittest

import numpy as np
import pandas as pd

from models.nfl_accuracy_research import nested_partitions


class NflAccuracyResearchTests(unittest.TestCase):
    def test_ties_and_delayed_labels_cannot_enter_supervised_partitions(self):
        dates = pd.date_range('2020-01-01', periods=40, tz='UTC')
        games = pd.DataFrame({'date': dates, 'result_available_at': dates+pd.Timedelta(days=2),
                              'result': ['away_win', 'home_win']*20})
        games.loc[[5, 20, 26, 35], 'result'] = 'draw'
        games.loc[[0, 19, 25], 'result_available_at'] = dates[39]
        splits = nested_partitions(games, np.arange(30), np.arange(30, 40))
        for index in splits.values():
            self.assertFalse(games.iloc[index].result.eq('draw').any())
        for name, boundary in [('train', dates[18]), ('tune', dates[24]), ('calibration', dates[30])]:
            self.assertTrue(games.iloc[splits[name]].result_available_at.lt(boundary).all())
        self.assertFalse(set(splits['train']) & set(splits['tune']))
        self.assertFalse(set(splits['calibration']) & set(splits['test']))
        self.assertEqual(len(games), 40)  # Ties remain available to feature-history construction.
