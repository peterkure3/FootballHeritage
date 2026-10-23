from copy import deepcopy
from datetime import datetime,timedelta,timezone
from email.utils import format_datetime
import hashlib,json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from etl.nba_public_parsers import bovada,cloudbet,betpawa,validate_fixtures,team
from etl.fetch_nba_public_odds import check_price_response,load_validated
from etl.betting_intel import add_candidate_predictions

NOW=datetime(2026,10,20,21,0,tzinfo=timezone.utc)
KICK=NOW+timedelta(hours=2)
OBSERVED=NOW.isoformat()


def bovada_payload():
    market={'id':'m1','key':'2W-12','description':'Moneyline','status':'O',
      'period':{'id':'209','description':'Game','main':True,'live':False},'outcomes':[
          {'type':'A','competitorId':'away-id','status':'O','price':{'decimal':'2.45','american':'+145'}},
          {'type':'H','competitorId':'home-id','status':'O','price':{'decimal':'1.588235','american':'-170'}}]}
    return [{'path':[{'type':'LEAGUE','description':'NBA','sportCode':'BASK'}],'events':[{
        'id':'game1','type':'GAMEEVENT','sport':'BASK','status':'U','live':False,'startTime':KICK.timestamp()*1000,
        'competitors':[{'id':'away-id','name':'Philadelphia 76ers','home':False},
                       {'id':'home-id','name':'New York Knicks','home':True}],
        'displayGroups':[{'markets':[market]}]}]}]


def cloud_payload():
    return {'key':'basketball-usa-nba','sport':{'key':'basketball'},'events':[{
        'id':'cloud1','type':'EVENT_TYPE_EVENT','status':'TRADING','metadata':{'eventStatus':'not_started'},
        'home':{'name':'NY Knicks'},'away':{'name':'PHI 76ers'},'startTime':KICK.isoformat(),
        'markets':{'basketball.moneyline':{'submarkets':{'period=ot&period=ft':{'selections':[
            {'outcome':'home','marketUrl':'basketball.moneyline/home','params':'','status':'SELECTION_ENABLED','side':'BACK','price':1.57},
            {'outcome':'away','marketUrl':'basketball.moneyline/away','params':'','status':'SELECTION_ENABLED','side':'BACK','price':2.45}]}}}}}]}


def pawa_payload():
    return {'responses':[{'responses':[{'id':'pawa1','category':{'id':'3'},'region':{'name':'USA'},'competition':{'name':'NBA'},
        'additionalInfo':{'live':False},'startTime':KICK.isoformat(),'participants':[
            {'position':1,'name':'New York Knicks'},{'position':2,'name':'Philadelphia 76ers'}],
        'markets':[{'marketType':{'name':'Moneyline - FT incl OT','explainer':'Any overtime played counts.'},
                    'row':[{'id':'moneyline','prices':[{'name':'1','odds':1.51,'suspended':False},
                                                    {'name':'2','odds':2.5,'suspended':False}]}]}]}]}]}


def schedule():
    return [{'id':123,'home_team':{'full_name':'New York Knicks'},'visitor_team':{'full_name':'Philadelphia 76ers'},
             'datetime':KICK.isoformat(),'status_state':'scheduled','period':0,'postponed':False}]


class NbaPublicOddsTests(unittest.TestCase):
    def test_bovada_home_away_comes_from_ids_not_display_order(self):
        row=bovada(bovada_payload(),OBSERVED,'test.raw')[0]
        self.assertEqual(row['home_team'],'New York Knicks')
        self.assertEqual(next(o['decimal_odds'] for o in row['offers'] if o['selection']=='away_win'),2.45)
        self.assertEqual(row['settlement_rule'],'INCLUDING_OVERTIME')

    def test_bovada_non_nba_live_and_wrong_period_rejected(self):
        for field,value in [('live',True),('sport','SOCC'),('type','OUTRIGHT')]:
            payload=bovada_payload();payload[0]['events'][0][field]=value
            self.assertEqual(bovada(payload,OBSERVED,'test.raw'),[])
        payload=bovada_payload();payload[0]['events'][0]['displayGroups'][0]['markets'][0]['period']['id']='1'
        self.assertEqual(bovada(payload,OBSERVED,'test.raw'),[])

    def test_bovada_price_format_suspension_duplicate_and_wrong_competitor_rejected(self):
        for field,value in [('status','S'),('competitorId','home-id'),('price',{'decimal':'2.45','american':'-145'})]:
            payload=bovada_payload();payload[0]['events'][0]['displayGroups'][0]['markets'][0]['outcomes'][0][field]=value
            self.assertEqual(bovada(payload,OBSERVED,'test.raw'),[])
        payload=bovada_payload();outcomes=payload[0]['events'][0]['displayGroups'][0]['markets'][0]['outcomes'];outcomes.append(deepcopy(outcomes[0]))
        self.assertEqual(bovada(payload,OBSERVED,'test.raw'),[])

    def test_cloud_requires_full_game_ot_back_enabled_pair(self):
        self.assertEqual(len(cloudbet(cloud_payload(),OBSERVED,'test.raw')),1)
        for field,value in [('side','LAY'),('status','SELECTION_DISABLED'),('params','period=q1')]:
            payload=cloud_payload();payload['events'][0]['markets']['basketball.moneyline']['submarkets']['period=ot&period=ft']['selections'][0][field]=value
            self.assertEqual(cloudbet(payload,OBSERVED,'test.raw'),[])
        payload=cloud_payload();markets=payload['events'][0]['markets']['basketball.moneyline']['submarkets'];markets['period=ft']=markets.pop('period=ot&period=ft')
        self.assertEqual(cloudbet(payload,OBSERVED,'test.raw'),[])

    def test_cloud_outrights_and_live_games_rejected(self):
        for field,value in [('type','EVENT_TYPE_OUTRIGHT'),('status','TRADING_LIVE')]:
            payload=cloud_payload();payload['events'][0][field]=value
            self.assertEqual(cloudbet(payload,OBSERVED,'test.raw'),[])

    def test_zero_stake_quotes_and_ambiguous_participants_rejected(self):
        payload=cloud_payload();payload['events'][0]['markets']['basketball.moneyline']['submarkets']['period=ot&period=ft']['selections'][0]['maxStake']=0
        self.assertEqual(cloudbet(payload,OBSERVED,'test.raw'),[])
        payload=pawa_payload();participants=payload['responses'][0]['responses'][0]['participants'];participants.append(deepcopy(participants[0]))
        self.assertEqual(betpawa(payload,OBSERVED,'test.raw'),[])

    def test_pawa_rejects_suspended_and_regulation_markets(self):
        self.assertEqual(len(betpawa(pawa_payload(),OBSERVED,'test.raw')),1)
        payload=pawa_payload();payload['responses'][0]['responses'][0]['markets'][0]['row'][0]['prices'][0]['suspended']=True
        self.assertEqual(betpawa(payload,OBSERVED,'test.raw'),[])
        payload=pawa_payload();payload['responses'][0]['responses'][0]['markets'][0]['marketType']['name']='Moneyline - FT'
        self.assertEqual(betpawa(payload,OBSERVED,'test.raw'),[])

    def test_unknown_teams_and_different_leagues_not_fuzzily_matched(self):
        self.assertEqual(team('NY Knicks'),'New York Knicks')
        self.assertEqual(team('LA Clippers'),'Los Angeles Clippers')
        self.assertIsNone(team('New York Liberty'));self.assertIsNone(team('New York Knick'))
        payload=pawa_payload();payload['responses'][0]['responses'][0]['competition']['name']='WNBA'
        self.assertEqual(betpawa(payload,OBSERVED,'test.raw'),[])

    def test_independent_identity_orientation_kickoff_and_status_must_match(self):
        fixtures=cloudbet(cloud_payload(),OBSERVED,'test.raw')
        accepted,rejected=validate_fixtures(fixtures,schedule(),NOW)
        self.assertEqual(len(accepted),1);self.assertEqual(rejected,[])
        self.assertEqual(accepted[0]['independent_validation']['game_id'],123)
        for field,value in [('datetime',(KICK+timedelta(minutes=1)).isoformat()),('status_state','in_progress'),('postponed',True),('period',1)]:
            games=schedule();games[0][field]=value
            self.assertEqual(validate_fixtures(fixtures,games,NOW)[0],[])
        games=schedule();games[0]['home_team'],games[0]['visitor_team']=games[0]['visitor_team'],games[0]['home_team']
        self.assertEqual(validate_fixtures(fixtures,games,NOW)[0],[])

    def test_duplicate_independent_games_quarantined(self):
        fixtures=cloudbet(cloud_payload(),OBSERVED,'test.raw')
        self.assertEqual(validate_fixtures(fixtures,schedule()+schedule(),NOW)[0],[])

    def test_cached_stale_future_and_nonfinite_responses_rejected(self):
        check_price_response({'Age':'10','Date':format_datetime(NOW)},NOW)
        for headers in [{'Age':'452'},{'Age':'NaN'},{'Age':'-1'},
                        {'Date':format_datetime(NOW-timedelta(minutes=10))},
                        {'Date':format_datetime(NOW+timedelta(minutes=2))}]:
            with self.assertRaises(ValueError):check_price_response(headers,NOW)

    def test_capture_checksums_and_expiry_are_enforced(self):
        fixtures=cloudbet(cloud_payload(),OBSERVED,'source.raw')
        with tempfile.TemporaryDirectory() as temp,patch('etl.fetch_nba_public_odds.ROOT',Path(temp)):
            root=Path(temp)/'20261020T210000Z';root.mkdir()
            raw=root/'source.raw';raw.write_text('source evidence')
            data=root/'validated_fixtures.json';data.write_text(json.dumps(fixtures))
            manifest={'schema_version':1,'validated_moneylines':1,'completed_at':OBSERVED,
                      'fixtures_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
                      'captures':[{'file':raw.name,'sha256':hashlib.sha256(raw.read_bytes()).hexdigest()}]}
            (root/'manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(len(load_validated(NOW)),1)
            self.assertEqual(load_validated(NOW+timedelta(minutes=31)),[])
            raw.write_text('changed evidence')
            with self.assertRaises(ValueError):load_validated(NOW)

    def test_public_string_kickoff_and_candidate_aliases_are_supported(self):
        fixtures=cloudbet(cloud_payload(),OBSERVED,'test.raw')
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);(directory/'metrics.json').write_text(json.dumps({'training_leagues':['basketball_nba']}))
            with patch('models.sport_predict.catalog',return_value=[{'candidate_id':'test','sports':{'basketball':{'status':'candidate'}}}]),patch('models.sport_predict.candidate_directory',return_value=directory),patch('models.sport_predict.candidate_teams',return_value=['New York Knicks','Philadelphia 76ers']),patch('models.sport_predict.predict_candidate',return_value={'model_version':'test-only','probabilities':{'home_win':.6,'away_win':.4}}) as predict:
                self.assertEqual(add_candidate_predictions(fixtures,NOW),[])
                self.assertEqual(predict.call_args.args[4],KICK.isoformat())
                self.assertEqual(fixtures[0]['prediction']['status'],'candidate_preview')


if __name__=='__main__': unittest.main()
