from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import os
from unittest.mock import patch
import requests

import pandas as pd

from etl.regional_sportsbooks import normalize_ababet, normalize_fortebet, normalize_betpawa, normalize_sportpesa
from etl.load_to_db import prepare_dataframe
from models.paper_trial import dashboard, import_trial, settle, settle_directory
from models.import_sportsbook_odds import normalize_snapshots
from models.data import match_odds_to_fixtures
from sqlalchemy import text
from api.db import get_db_connection
from scripts.record_edge_trial import price_analysis
from scripts import refresh_regional_pipeline as refresh


class RegionalPipelineTests(unittest.TestCase):
    def setUp(self):
        self.observed = '2026-10-08T10:00:00Z'
        self.feed = {'status':'OK','data':{
            'market_list': {'1': {'1': {'name':'Full Time Result','template':'3WAY','outcome':{'1':{'short':'1'},'2':{'short':'X'},'3':{'short':'2'}}}}},
            'category': {'1':{'sportId':1,'name':'England'}},
            'tournament': {'TO1':{'categoryId':1,'name':'Premier League'}},
            'competitors': {'1':{'name':'Arsenal'},'2':{'name':'Leeds United'}},
            'event': {'MA1':{'tournamentId':'TO1','competitors':[1,2],'startTs':'2026-10-08T11:30:00Z','eventStatusId':0,'scoreboard':{'status':{}},'results':{}}},
            'markets': {'m1':{'eventId':'MA1','marketId':1,'marketStatusId':1,'odds':{str(i):{'outcomeId':i,'locked':0,'odds':p} for i,p in [(1,2.0),(2,3.5),(3,4.0)]}}}}}

    def test_fortebet_full_time_order_and_locked_market(self):
        row = normalize_fortebet(self.feed,self.observed,'raw.json','run')[0]
        self.assertEqual([o['selection'] for o in row['outcomes']], ['HOME','DRAW','AWAY'])
        self.assertEqual(row['region'], 'UG')
        self.feed['data']['markets']['m1']['odds']['2']['locked'] = 1
        self.assertEqual(normalize_fortebet(self.feed,self.observed,'raw.json','run'), [])

    def test_fortebet_excludes_started_and_other_sports(self):
        self.assertEqual(normalize_fortebet(self.feed,'2026-10-08T12:00:00Z','raw.json','run'), [])
        self.feed['data']['category']['1']['sportId'] = 2
        self.assertEqual(normalize_fortebet(self.feed,self.observed,'raw.json','run'), [])

    def test_ababet_local_kickoff_and_live_rejection(self):
        buttons = ''.join(f'<button class="bet" data-market="Match Result" data-live_status="0" data-bet="{s}" data-odds="{p}" data-id="{s}"></button>' for s,p in [('1',2),('X',3.5),('2',4)])
        html = '<select name="date"><option selected value="2026-10-08">Today</option></select><table><tr class="event" data-period="-1" data-id="e1"><td>England - Premier League</td><td id="time_e1">14:30</td><td class="home">Arsenal</td><td class="away">Leeds United</td><td>' + buttons + '</td></tr></table>'
        row = normalize_ababet(html,self.observed,'raw.html','run')[0]
        self.assertEqual(row['commence_time'], '2026-10-08T11:30:00+00:00')
        self.assertEqual(normalize_ababet(html.replace('data-live_status="0"','data-live_status="1"'),self.observed,'raw.html','run'), [])
        champions = html.replace('England - Premier League', 'Europe - UEFA Champions League')
        champion = normalize_ababet(champions, self.observed, 'raw.html', 'run')[0]
        self.assertEqual(champion['competition'], 'UEFA Champions League')
        self.assertEqual(champion['country'], 'Europe')
        for competition in ['Asia - AFC Champions League Elite', 'Europe - UEFA Europa League']:
            self.assertEqual(normalize_ababet(html.replace('England - Premier League', competition),
                                             self.observed, 'raw.html', 'run'), [])

    def test_loader_preserves_utc_when_timezone_is_removed(self):
        frame = prepare_dataframe(pd.DataFrame({'match_id':[1], 'date':['2026-10-10T14:30:00+03:00']}), 'match_id', ['date'])
        self.assertEqual(frame.iloc[0].date, pd.Timestamp('2026-10-10T11:30:00'))
        self.assertIsNone(frame.iloc[0].date.tzinfo)

    def test_betpawa_requires_regulation_time_complete_open_market(self):
        event = {'id':'e1','category':{'id':'2'},'region':{'name':'England'},
            'competition':{'name':'Premier League'},'startTime':'2026-10-08T11:30:00Z',
            'participants':[{'position':i,'id':str(i),'name':name} for i,name in [(1,'Arsenal'),(2,'Leeds United')]],
            'markets':[{'marketType':{'name':'1X2 - FT','explainer':'regular playing time'},
                'row':[{'id':'m1','prices':[{'id':str(i),'name':name,'odds':price} for i,name,price in [(1,'1',2),(2,'X',3.5),(3,'2',4)]]}]}]}
        payload = {'responses':[{'responses':[event]}]}
        rows = normalize_betpawa(payload,self.observed,'raw.json','run')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['provider_home_team_id'],'1')
        self.assertEqual(normalize_betpawa(payload,'2026-10-08T12:00:00Z','raw.json','run'),[])
        event['markets'][0]['row'][0]['prices'][0]['status'] = 'SUSPENDED'
        self.assertEqual(normalize_betpawa(payload,self.observed,'raw.json','run'),[])
        event['markets'][0]['row'][0]['prices'][0].pop('status')
        event['category']['id'] = 'efootball'
        self.assertEqual(normalize_betpawa(payload,self.observed,'raw.json','run'),[])

    def test_reviewed_identity_metadata_preserves_original_names(self):
        record = normalize_fortebet(self.feed,self.observed,'raw.json','run')[0]
        record['away_team'] = 'Ipswich'
        record['canonical_away_team'] = 'Ipswich Town FC'
        frame = normalize_snapshots([record])
        fixtures = pd.DataFrame([{'match_id':1,'date':'2026-10-08T11:30:00Z',
            'home_team':'Arsenal FC','away_team':'Ipswich Town FC'}])
        joined = match_odds_to_fixtures(fixtures,frame,exact_kickoff=True)
        self.assertEqual(len(joined),1)
        self.assertEqual(frame.iloc[0].away_team,'Ipswich')
        fixtures['date'] = '2026-10-08T14:30:00Z'
        self.assertEqual(len(match_odds_to_fixtures(fixtures,frame,exact_kickoff=True)),0)

    def test_betpawa_accepts_champions_league_but_rejects_other_competitions(self):
        event = {'id':'e1','category':{'id':'2'},'region':{'name':'International'},
            'competition':{'name':'UEFA Champions League'},'startTime':'2026-10-08T11:30:00Z',
            'participants':[{'position':i,'id':str(i),'name':name} for i,name in [(1,'Arsenal'),(2,'Barcelona')]],
            'markets':[{'marketType':{'name':'1X2 - FT','explainer':'regular playing time'},
                'row':[{'id':'m1','prices':[{'id':str(i),'name':name,'odds':price} for i,name,price in [(1,'1',2),(2,'X',3.5),(3,'2',4)]]}]}]}
        payload = {'responses':[{'responses':[event]}]}
        rows = normalize_betpawa(payload,self.observed,'raw.json','run')
        self.assertEqual(rows[0]['competition'], 'UEFA Champions League')
        self.assertEqual(rows[0]['country'], 'International')
        event['competition']['name'] = 'AFC Champions League'
        self.assertEqual(normalize_betpawa(payload,self.observed,'raw.json','run'), [])

    def sportpesa_feed(self):
        return [{'id':1,'sport':{'id':1},'country':{'name':'England'},
            'competition':{'id':70,'name':'Premier League'},'state':{},
            'date':'2026-10-08T11:30:00Z','dateTimestamp':int(pd.Timestamp('2026-10-08T11:30:00Z').timestamp()*1000),
            'competitors':[{'id':1,'name':'Arsenal'},{'id':2,'name':'Leeds United'}],
            'markets':[{'id':10,'name':'1X2','selections':[
                {'id':i,'shortName':key,'name':name,'odds':price,'specValue':0}
                for i,key,name,price in [(1,'1','Arsenal','2.00'),(2,'X','Draw','3.50'),(3,'2','Leeds United','4.00')]]}]}]

    def test_sportpesa_global_identity_and_standard_market_only(self):
        feed = self.sportpesa_feed()
        rows = normalize_sportpesa(feed,self.observed,'raw.json','run')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['region'],'GLOBAL')
        self.assertEqual(rows[0]['market_status'],'UNKNOWN')
        self.assertEqual(normalize_snapshots(rows).iloc[0].draw,3.5)
        feed[0]['markets'][0]['id'] = 972
        self.assertEqual(normalize_sportpesa(feed,self.observed,'raw.json','run'),[])

    def test_sportpesa_rejects_started_suspended_mislabeled_and_conflicting_dates(self):
        feed = self.sportpesa_feed()
        self.assertEqual(normalize_sportpesa(feed,'2026-10-08T12:00:00Z','raw.json','run'),[])
        mutations = [lambda event:event.update(state={'status':'live'}),
            lambda event:event['markets'][0]['selections'][0].update(status='SUSPENDED'),
            lambda event:event['markets'][0]['selections'][0].update(name='Leeds United'),
            lambda event:event.update(dateTimestamp=event['dateTimestamp']+3600000)]
        for mutation in mutations:
            changed = deepcopy(feed)
            mutation(changed[0])
            self.assertEqual(normalize_sportpesa(changed,self.observed,'raw.json','run'),[])

    def trial(self):
        return {'status':'prospective_paper_trial','profitable_edge_established':False,'candidate_id':'test',
            'policy':{'payout_haircut':.02},'limits':[], 'fixtures':[{'home':'Arsenal','away':'Leeds United',
            'kickoff':'2026-10-08T11:30:00Z','observed_at':self.observed,'generated_at':'2026-10-08T10:05:00Z',
            'bookmaker':'bovada','status':'recorded_pregame','selected_outcome':'home_win',
            'outcomes':price_analysis({'home_win':.6,'draw':.2,'away_win':.2},{'home_win':2.,'draw':3.5,'away_win':4.})}]}

    def result(self):
        return {'home_team':'Arsenal FC','away_team':'Leeds United FC','commence_time':'2026-10-08T11:30:00Z',
                'home_score':2,'away_score':1,'status':'FINISHED','settlement_rule':'REGULATION_TIME',
                'observed_at':'2026-10-08T14:00:00Z','source_url':'https://example.com/results'}

    def test_settlement_math_and_pending_denominator(self):
        pending = settle(self.trial(), [])
        self.assertIsNone(pending['roi'])
        settled = settle(self.trial(), [self.result()])
        self.assertEqual(settled['profit_units'], 1.)
        self.assertAlmostEqual(settled['stressed_roi'], .96)
        self.assertFalse(settled['profitable_edge_established'])
        self.assertEqual(settled['model_metrics']['samples'], 1)

    def test_ambiguous_result_and_wrong_kickoff_cannot_settle(self):
        result = self.result()
        self.assertEqual(settle(self.trial(), [result,result])['settled_selections'], 0)
        result['commence_time'] = '2026-10-08T14:30:00Z'
        self.assertEqual(settle(self.trial(), [result])['settled_selections'], 0)

    def test_reviewed_bournemouth_result_identity(self):
        trial, result = self.trial(), self.result()
        trial['fixtures'][0]['away'] = 'Bournemouth'
        result['away_team'] = 'AFC Bournemouth'
        self.assertEqual(settle(trial,[result])['settled_selections'],1)

    def test_dashboard_rejects_settlement_from_other_trial(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'source.json'
            source.write_text(json.dumps(self.trial()))
            destination = import_trial(source,root/'trials')
            settle_directory(destination,[])
            latest = next(destination.glob('settlement_*.json'))
            report = json.loads(latest.read_text())
            report['trial_sha256'] = 'different-trial'
            latest.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                dashboard(root/'trials')
        result = self.result(); result['status'] = 'IN_PLAY'
        self.assertEqual(settle(self.trial(), [result])['settled_selections'], 0)

    def test_trial_import_integrity_and_postkickoff_rejection(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'source.json'
            trial = self.trial()
            source.write_text(json.dumps(trial))
            destination = import_trial(source, root/'trials')
            self.assertEqual(destination, import_trial(source, root/'trials'))
            trial['fixtures'][0]['generated_at'] = '2026-10-08T12:00:00Z'
            source.write_text(json.dumps(trial))
            with self.assertRaises(ValueError):
                import_trial(source, root/'trials')

    def test_refresh_checks_past_trial_dates_and_preserves_evidence_on_failure(self):
        trial = settle(self.trial(),[]) | {'trial_sha256':'test-trial'}
        with patch.object(refresh,'dashboard',return_value={'trials':[trial]}), \
             patch.object(refresh,'collect_results',side_effect=requests.ConnectionError) as collect, \
             patch.object(refresh,'settle_directory') as write:
            report = refresh.refresh_trial_results()
            collect.assert_called_once_with('2026-10-08')
            write.assert_not_called()
            self.assertEqual(report['provider_errors'],{'2026-10-08':'ConnectionError'})

    def test_refresh_settles_past_trial_after_official_results_arrive(self):
        trial = settle(self.trial(),[]) | {'trial_sha256':'test-trial'}
        with patch.object(refresh,'dashboard',return_value={'trials':[trial]}), \
             patch.object(refresh,'collect_results',return_value=[self.result()]), \
             patch.object(refresh,'settle_directory',return_value={'settled_selections':1}) as write:
            report = refresh.refresh_trial_results()
            self.assertEqual(report['settlements'][0]['settled_selections'],1)
            self.assertEqual(write.call_args.args[1],[self.result()])


@unittest.skipUnless(os.environ.get('RUN_PREDICTION_DB_TESTS') == '1', 'Rollback-only PostgreSQL timezone regression')
class LoaderTimezoneIntegrationTests(unittest.TestCase):
    def test_utc_naive_load_survives_non_utc_database_session(self):
        with get_db_connection().connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET LOCAL TIME ZONE 'Africa/Nairobi'"))
                connection.execute(text('CREATE TEMP TABLE regional_utc_test (match_id INTEGER, date TIMESTAMP) ON COMMIT DROP'))
                frame = prepare_dataframe(pd.DataFrame({'match_id':[1],'date':['2026-10-10T14:30:00+03:00']}),'match_id',['date'])
                frame.to_sql('regional_utc_test',connection,if_exists='append',index=False)
                actual = connection.execute(text('SELECT date FROM regional_utc_test')).scalar_one()
                self.assertEqual(pd.Timestamp(actual),pd.Timestamp('2026-10-10T11:30:00'))
            finally:
                transaction.rollback()


if __name__ == '__main__':
    unittest.main()
