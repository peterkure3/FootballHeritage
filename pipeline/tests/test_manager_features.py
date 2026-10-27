"""Chronology and missing-information gates for manager research features."""
import unittest
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

import numpy as np
import pandas as pd

from models.data import canonical_matches
from models.manager_features import ManagerState, build_manager_frame, coach_key
from scripts.assess_manager_impact import LEAGUES, load_matches


class ManagerFeatureTests(unittest.TestCase):
    def fixtures(self):
        return canonical_matches([pd.DataFrame([
            {'date':f'2018-01-0{index}T12:00:00Z','home_team':'Home','away_team':'Away',
             'home_score':score,'away_score':0,'result':None,'status':'FINISHED',
             'home_coach_id':11 if index < 3 else 33,'away_coach_id':22}
            for index,score in [(1,1),(2,0),(3,2),(4,1)]])])

    def test_unknown_managers_are_neutral_with_explicit_missingness(self):
        vector=ManagerState().vector('home','away')
        self.assertEqual(vector['home_manager_known'],0)
        self.assertEqual(vector['home_manager_smoothed_ppg'],1.3)
        self.assertEqual(vector['home_manager_elo_adjusted_result'],0)
        self.assertEqual(vector['manager_pair_home_score'],.5)
        for invalid in [None,0,-1,True,'unknown',float('nan')]:
            self.assertIsNone(coach_key(invalid))

    def test_first_match_coach_does_not_enter_its_own_inputs(self):
        _,extra,_=build_manager_frame(self.fixtures())
        self.assertEqual(extra.iloc[0].home_manager_known,0)
        self.assertEqual(extra.iloc[1].home_manager_prior_games_observed,1)
        self.assertEqual(extra.iloc[0].manager_pair_games,0)

    def test_coach_change_is_only_observed_after_the_change_match(self):
        _,extra,_=build_manager_frame(self.fixtures())
        self.assertEqual(extra.iloc[2].home_manager_stint_games_observed,2)
        self.assertEqual(extra.iloc[2].home_manager_recent_change_observed,0)
        self.assertEqual(extra.iloc[3].home_manager_stint_games_observed,1)
        self.assertEqual(extra.iloc[3].home_manager_recent_change_observed,1)

    def test_future_results_and_coaches_cannot_change_earlier_vectors(self):
        fixtures=self.fixtures()
        original=build_manager_frame(fixtures)
        fixtures.loc[2:,'home_coach_id']=999
        fixtures.loc[2:,'home_score']=8
        changed=build_manager_frame(fixtures)
        np.testing.assert_array_equal(original[0].iloc[:3],changed[0].iloc[:3])
        np.testing.assert_array_equal(original[1].iloc[:3],changed[1].iloc[:3])

    def test_same_day_results_and_coaches_are_not_exposed(self):
        fixtures=self.fixtures()
        fixtures.loc[1,'date']=fixtures.loc[0,'date']+pd.Timedelta(hours=3)
        _,extra,_=build_manager_frame(fixtures)
        self.assertEqual(extra.iloc[1].home_manager_known,0)
        self.assertEqual(extra.iloc[1].home_manager_prior_games_observed,0)

    def test_pair_orientation_is_consistent_and_smoothed(self):
        state=ManagerState()
        state.update({'home_key':'home','away_key':'away','home_coach_id':11,'away_coach_id':22,
                      'home_score':2,'away_score':0},.5)
        forward=state.vector('home','away')
        reverse=state.vector('away','home')
        self.assertEqual(forward['manager_pair_games'],1)
        self.assertAlmostEqual(forward['manager_pair_home_score']+reverse['manager_pair_home_score'],1)

    def test_unfinished_results_are_rejected(self):
        fixtures=self.fixtures()
        fixtures.loc[0,'result']=None
        with self.assertRaises(ValueError):
            build_manager_frame(fixtures)

    def test_source_conflicts_are_quarantined_and_checksum_tampering_fails(self):
        match={'status':'Played','duration':'Regular','dateutc':'2018-01-01 12:00:00',
            'wyId':1,'winner':10,'teamsData':{'10':{'teamId':10,'side':'home','score':1,'coachId':100},
                                          '20':{'teamId':20,'side':'away','score':0,'coachId':200}}}
        with TemporaryDirectory() as directory:
            root=Path(directory)
            with zipfile.ZipFile(root/'matches.zip','w') as archive:
                for league in LEAGUES:
                    archive.writestr('matches_'+league+'.json',json.dumps([match,{**match,'wyId':2,'winner':0}] if league=='England' else []))
            digest=hashlib.sha256((root/'matches.zip').read_bytes()).hexdigest()
            (root/'manifest.json').write_text(json.dumps({'captures':{'matches.zip':{'sha256':digest}}}),encoding='utf-8')
            frame,source=load_matches(root)
            self.assertEqual(len(frame),1)
            self.assertEqual(source['exclusions'],[{'match_id':2,'reason':'score_winner_disagreement'}])
            (root/'matches.zip').write_bytes((root/'matches.zip').read_bytes()+b' ')
            with self.assertRaises(ValueError):
                load_matches(root)
