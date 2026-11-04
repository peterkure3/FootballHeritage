"""Paired pregame recording contract; synthetic rows are not accuracy evidence."""
import unittest

import numpy as np
import pandas as pd

from models.data import canonical_matches
from scripts.record_accuracy_shadow import forecast_pair
from scripts.evaluate_accuracy_shadow import assess


class FixedModel:
    def predict_proba(self, frame):
        return np.tile([.3, .3, .4], (len(frame), 1))


class AccuracyShadowTests(unittest.TestCase):
    def history(self):
        return canonical_matches([pd.DataFrame([{'date':'2026-01-01T12:00:00Z',
            'home_team':'A','away_team':'B','home_score':1,'away_score':0}])])

    def fixture(self):
        return {'id':1,'utcDate':'2099-01-01T12:00:00Z','status':'TIMED',
                'homeTeam':{'name':'A'},'awayTeam':{'name':'B'},'competition':{'code':'PL'}}

    def test_both_arms_share_fixture_and_record_feature_cutoff(self):
        now=pd.Timestamp.now(tz='UTC')
        rows,excluded=forecast_pair(self.history(),FixedModel(),FixedModel(),{},[self.fixture()],now)
        self.assertEqual(len(rows),1)
        self.assertEqual(excluded,[])
        self.assertEqual(set(rows[0]['probabilities']),{'original','reviewed'})
        self.assertLess(pd.Timestamp(rows[0]['generated_at']),pd.Timestamp(rows[0]['kickoff']))
        self.assertEqual(rows[0]['features']['original']['odds_missing'],1)

    def test_started_and_unknown_history_are_excluded_from_both_arms(self):
        first=self.fixture();first['utcDate']='2020-01-01T12:00:00Z'
        second=self.fixture();second['id']=2;second['homeTeam']={'name':'Unknown'}
        rows,excluded=forecast_pair(self.history(),FixedModel(),FixedModel(),{},[first,second],pd.Timestamp.now(tz='UTC'))
        self.assertEqual(rows,[])
        self.assertEqual(len(excluded),2)

    def test_duplicate_provider_id_is_not_silently_overwritten(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            forecast_pair(self.history(),FixedModel(),FixedModel(),{},[self.fixture(),self.fixture()],pd.Timestamp.now(tz='UTC'))

    def test_assessment_requires_exact_final_result(self):
        trial={'classes':['away_win','draw','home_win'],'status':'prospective_accuracy_shadow','alias_map':{},
            'policy':{'minimum_settled_for_assessment':200,'minimum_distinct_match_days':20},
            'fixtures':[{'id':'1','home':'A','away':'B','kickoff':'2026-01-02T12:00:00Z',
                'generated_at':'2026-01-01T12:00:00Z','probabilities':{'original':[.3,.3,.4],'reviewed':[.2,.3,.5]}}]}
        result={'id':1,'utcDate':'2026-01-02T12:00:00Z','homeTeam':{'name':'A'},'awayTeam':{'name':'B'},
            'status':'TIMED','score':{'duration':'REGULAR','fullTime':{'home':1,'away':0}}}
        now=pd.Timestamp('2026-01-03T12:00:00Z')
        self.assertEqual(assess(trial,[result],now)['settled'],0)
        result['status']='FINISHED'
        report=assess(trial,[result],now)
        self.assertEqual(report['settled'],1)
        self.assertFalse(report['promotion_authorized'])
        self.assertEqual(report['status'],'collecting_evidence')
        self.assertEqual(assess(trial,[result,result],now)['settled'],0)
        result['utcDate']='2026-01-02T13:00:00Z'
        self.assertEqual(assess(trial,[result],now)['fixtures'][0]['status'],'fixture_mismatch')
        trial['fixtures'][0]['generated_at']='2026-01-02T13:00:00Z'
        with self.assertRaisesRegex(ValueError,'post-kickoff'):
            assess(trial,[result],now)
