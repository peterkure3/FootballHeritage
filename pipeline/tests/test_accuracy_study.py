from copy import deepcopy
import unittest

from scripts.assess_accuracy_study import combine


class AccuracyStudyTests(unittest.TestCase):
    def trial(self):
        return {'model_hashes':{'original':'a','reviewed':'b'},'alias_map':{},
                'classes':['away_win','draw','home_win'],'policy':{'frozen':True},
                'fixtures':[{'id':'1','kickoff':'2026-11-01T12:00:00Z','generated_at':'2026-10-31T10:00:00Z','probabilities':{'original':[.3,.3,.4]}}]}

    def test_later_recapture_does_not_replace_first_prediction(self):
        first=self.trial();later=deepcopy(first)
        later['fixtures'][0]['generated_at']='2026-10-31T11:00:00Z'
        later['fixtures'][0]['probabilities']['original']=[.1,.1,.8]
        study,duplicates=combine([later,first])
        self.assertEqual(duplicates,1)
        self.assertEqual(study['fixtures'],first['fixtures'])

    def test_changed_model_or_policy_cannot_join_study(self):
        for key,value in [('model_hashes',{'original':'changed'}),('policy',{'frozen':False})]:
            other=deepcopy(self.trial());other[key]=value
            with self.assertRaisesRegex(ValueError,'separate study'):
                combine([self.trial(),other])

    def test_distinct_fixtures_accumulate(self):
        other=deepcopy(self.trial());other['fixtures'][0]['id']='2'
        study,duplicates=combine([self.trial(),other])
        self.assertEqual(len(study['fixtures']),2)
        self.assertEqual(duplicates,0)
