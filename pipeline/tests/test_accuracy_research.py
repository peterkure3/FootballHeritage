"""Causality checks for isolated accuracy experiments; not model-quality evidence."""
import unittest

import pandas as pd

from models.accuracy_research import context_features, estimator
from models.features import build_feature_frame


class AccuracyResearchTests(unittest.TestCase):
    def frame(self):
        rows=[]
        for day in range(1,9):
            rows.append({'date':f'2026-01-{day:02}T12:00:00Z','home_team':'A','away_team':'B',
                         'home_score':day%3,'away_score':1,'competition':'PL'})
        return build_feature_frame(pd.DataFrame(rows))[1]

    def test_current_and_future_scores_do_not_change_earlier_features(self):
        fixtures=self.frame()
        original=context_features(fixtures)
        changed=fixtures.copy()
        changed.loc[4:,'home_score']=9
        changed.loc[4:,'result']='home_win'
        actual=context_features(changed)
        pd.testing.assert_frame_equal(original.iloc[:5],actual.iloc[:5])

    def test_same_day_results_are_not_shared(self):
        fixtures=self.frame()
        fixtures.loc[1,'date']=fixtures.loc[0,'date']
        fixtures.loc[1,'fixture_day']=fixtures.loc[0,'fixture_day']
        original=context_features(fixtures)
        fixtures.loc[0,'home_score']=100
        fixtures.loc[0,'result']='home_win'
        changed=context_features(fixtures)
        pd.testing.assert_frame_equal(original.iloc[:2],changed.iloc[:2])

    def test_configuration_uses_training_only_preprocessing(self):
        model=estimator('context_logistic',['home_elo'],['home_rest_days'])
        self.assertEqual(model.steps[-1][1].C,.01)
        self.assertFalse(hasattr(model.steps[0][1],'transformers_'))


if __name__=='__main__':
    unittest.main()
