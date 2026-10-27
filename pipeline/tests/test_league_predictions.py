"""League forecast integrity, fixture identity, freshness and causal state checks."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from api.league_predictions import fixture_prediction, load_predictions
from models.predict_football_leagues import league_state
from models.league_data import identity, identity_aliases, openfootball_portugal


class LeaguePredictionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.row = {'match_id': 1, 'competition': 'Primera Division', 'home_team': 'FC Barcelona',
                    'away_team': 'Real Madrid CF', 'date': (self.now+timedelta(days=1)).replace(tzinfo=None)}
        self.forecast = {**self.row, 'kickoff': (self.now+timedelta(days=1)).isoformat(),
            'trained_at': (self.now-timedelta(hours=2)).isoformat(),
            'feature_cutoff': (self.now-timedelta(hours=1)).isoformat(),
            'generated_at': (self.now-timedelta(minutes=1)).isoformat(),
            'probabilities': {'home_win': .5, 'draw': .3, 'away_win': .2}, 'winner': 'home_win'}
        self.forecast.pop('date')

    def test_current_candidate_is_explicitly_separate_from_active_model(self):
        prediction = fixture_prediction(self.row, {1: self.forecast}, self.now)
        self.assertEqual(prediction['status'], 'current')
        self.assertFalse(prediction['active'])

    def test_rejects_rescheduled_swapped_cross_league_and_future_information(self):
        for changes in [{'competition':'Serie A'}, {'home_team':'Real Madrid CF'},
                        {'kickoff':(self.now+timedelta(days=2)).isoformat()},
                        {'trained_at':(self.now+timedelta(minutes=1)).isoformat()},
                        {'probabilities':{'home_win':float('nan'),'draw':.3,'away_win':.2}}]:
            self.assertIsNone(fixture_prediction(self.row, {1:{**self.forecast, **changes}}, self.now))

    def test_stale_forecasts_are_not_current(self):
        old = self.now-timedelta(days=2)
        forecast = {**self.forecast, **{key:old.isoformat() for key in ['trained_at','feature_cutoff','generated_at']}}
        self.assertEqual(fixture_prediction(self.row,{1:forecast},self.now)['status'],'stale')

    def test_duplicate_snapshot_ids_are_rejected(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'predictions.json'
            path.write_text(json.dumps({'schema_version':1,'predictions':[self.forecast,self.forecast]}),encoding='utf-8')
            self.assertEqual(load_predictions(path),{})

    def test_state_excludes_same_day_and_future_results(self):
        day = pd.Timestamp('2026-10-25T15:00:00Z')
        rows = pd.DataFrame([{'date': date,'home_key':'home','away_key':'away','home_score':3,
            'away_score':0,'result':'home_win'} for date in [day-pd.Timedelta(days=1),day,day+pd.Timedelta(days=1)]])
        state = league_state(rows,day)
        self.assertEqual(len(state.history['home']),1)

    def test_reviewed_identity_pairs_share_history(self):
        aliases=identity_aliases()
        for left,right in [('Barcelona','FC Barcelona'),('Real Madrid','Real Madrid CF'),
                           ('Athletico-PR','CA Paranaense'),('Norwich','Norwich City FC'),
                           ('Cambuur','SC Cambuur-Leeuwarden'),('Estoril','GD Estoril Praia')]:
            self.assertEqual(identity(left,aliases),identity(right,aliases))

    def test_portugal_source_is_scoped_and_uses_regulation_score(self):
        payload={'name':'Portuguese Primeira Liga 2022/23','matches':[{'date':'2022-08-05',
            'team1':'SL Benfica','team2':'FC Arouca','score':{'ft':[4,0],'ht':[3,0]}}]}
        frame=openfootball_portugal(payload)
        self.assertEqual(frame.iloc[0].home_score,4)
        self.assertEqual(frame.iloc[0].home_team,'Sport Lisboa e Benfica')
        self.assertEqual(frame.iloc[0].competition,'PPL')
        payload['matches'][0]['score']['ft']=[True,0]
        with self.assertRaises(ValueError):
            openfootball_portugal(payload)
        payload['name']='Another league'
        with self.assertRaises(ValueError):
            openfootball_portugal(payload)
