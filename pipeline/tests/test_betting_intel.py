import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock

from fastapi import HTTPException

from api.betting_intel import build_intelligence,sport_key
from api.routers.betting_intel import overview,sport_intelligence
from etl.betting_intel import merge_fixtures,raw_event,refresh
from etl.ingest_player_props import extract_player_props,write_player_props,fetch_player_props_for_sport

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def fixture(sport='nba'):
    return dict(fixture_id='fixture-1',sport=sport,competition='NBA' if sport=='nba' else 'League',
                home_team='Boston Celtics',away_team='New York Knicks',kickoff=(NOW+timedelta(hours=2)).isoformat(),
                settlement_rule='REGULATION_1X2' if sport=='football' else 'INCLUDING_OVERTIME',status='SCHEDULED',offers=[])


def quote(book='a',prices=(2.2,1.8),age=60,market='h2h',player=None,line=None):
    outcomes = ('home_win','away_win') if market=='h2h' else ('over','under')
    return [dict(bookmaker=book,selection=key,decimal_odds=price,observed_at=(NOW-timedelta(seconds=age)).isoformat(),
                 market=market,participant=player,line=line) for key,price in zip(outcomes,prices)]


def prediction(item):
    probabilities = {'home_win':.6,'away_win':.4}
    if item['sport']=='football':
        probabilities = {'home_win':.5,'draw':.3,'away_win':.2}
    return dict(probabilities=probabilities,generated_at=(NOW-timedelta(minutes=5)).isoformat(),
                settlement_rule=item['settlement_rule'],model_version='test-only',status='candidate_preview')


class IntelligenceTests(unittest.TestCase):
    def test_league_identity_never_mixes_nba_wnba_or_college(self):
        self.assertEqual(sport_key('basketball','NBA'),'nba')
        self.assertEqual(sport_key('basketball','basketball_wnba'),'wnba')
        self.assertEqual(sport_key('basketball','basketball_ncaab'),'ncaab')
        self.assertIsNone(sport_key('basketball','EuroLeague'))
        self.assertEqual(sport_key('Football','NFL'),'nfl')

    def test_devig_normalizes_one_book_without_inventing_ev(self):
        item=fixture(); item['offers']=quote(prices=(1.8,2.0))
        output=build_intelligence('nba',[item],NOW)
        book=output['devigged_odds'][0]
        self.assertAlmostEqual(sum(book['fair_probabilities'].values()),1)
        self.assertAlmostEqual(book['overround'],1/1.8+1/2-1)
        self.assertEqual(output['ev_bets'],[])
        self.assertEqual(output['ai_picks'],[])

    def test_candidate_predictions_and_model_ev_are_labeled(self):
        item=fixture(); item['prediction']=prediction(item); item['offers']=quote()
        item['prediction']['sport']='basketball'
        output=build_intelligence('nba',[item],NOW)
        bet=next(b for b in output['ev_bets'] if b['selection']=='home_win')
        self.assertAlmostEqual(bet['ev_pct'],.32)
        self.assertEqual(bet['model_status'],'candidate_preview')
        self.assertEqual(output['ai_picks'][0]['pick_type'],'model_value')
        self.assertEqual(output['predictions'][0]['sport'],'nba')

    def test_ambiguous_quote_timezone_and_conflicting_snapshots_rejected(self):
        item=fixture(); item['offers']=quote()
        item['offers'][0]['observed_at']=NOW.replace(tzinfo=None).isoformat()
        self.assertEqual(build_intelligence('nba',[item],NOW)['devigged_odds'],[])
        item['offers']=quote()+quote(prices=(2.5,1.8))
        self.assertEqual(build_intelligence('nba',[item],NOW)['devigged_odds'],[])

    def test_history_forecast_without_odds_has_no_invented_price(self):
        item=fixture(); item['prediction']=prediction(item)
        result=build_intelligence('nba',[item],NOW)
        self.assertIsNone(result['ai_picks'][0]['decimal_odds'])

    def test_consensus_excludes_the_target_book(self):
        item=fixture(); item['offers']=quote('a',(2.5,1.5))+quote('b',(1.8,2.0))+quote('c',(1.8,2.0))
        bets=build_intelligence('nba',[item],NOW)['ev_bets']
        bet=next(b for b in bets if b['bookmaker']=='a' and b['selection']=='home_win')
        self.assertEqual(bet['reference_books'],['b','c'])
        self.assertEqual(bet['probability_basis'],'other_book_consensus')
        self.assertAlmostEqual(bet['probability'],(1/1.8)/(1/1.8+1/2))

    def test_arbitrage_returns_equal_payout_not_reciprocal_margin(self):
        item=fixture(); item['offers']=quote('a',(2.2,1.8))+quote('b',(1.8,2.2))
        arb=build_intelligence('nba',[item],NOW)['arbitrage'][0]
        self.assertAlmostEqual(arb['gross_roi'],.1)
        self.assertAlmostEqual(sum(leg['reference_stake'] for leg in arb['legs']),100)
        for leg in arb['legs']:
            self.assertAlmostEqual(leg['reference_stake']*leg['decimal_odds'],110)
        self.assertFalse(arb['execution_verified'])

    def test_three_way_football_requires_draw(self):
        item=fixture('football'); item['offers']=quote()
        self.assertEqual(build_intelligence('football',[item],NOW)['devigged_odds'],[])
        item['offers']=[]
        for book in ('a','b'):
            item['offers'] += quote(book,(3.5,3.5))
            item['offers'].append(dict(bookmaker=book,selection='draw',decimal_odds=3.5,market='h2h',observed_at=NOW.isoformat()))
        result=build_intelligence('football',[item],NOW)
        self.assertEqual(len(result['devigged_odds']),2)

    def test_stale_future_invalid_incomplete_and_started_are_excluded(self):
        for offers in [quote(age=1801),quote(age=-10),quote(prices=(float('nan'),2.2)),quote()[:1]]:
            item=fixture(); item['offers']=offers
            self.assertEqual(build_intelligence('nba',[item],NOW)['devigged_odds'],[])
        item=fixture(); item['kickoff']=(NOW-timedelta(seconds=1)).isoformat(); item['offers']=quote()
        self.assertEqual(build_intelligence('nba',[item],NOW)['summary']['fixtures'],0)

    def test_latest_invalid_price_does_not_resurrect_older_offer(self):
        item=fixture(); item['offers']=quote(age=120)+quote(prices=(None,1.8),age=60)
        self.assertEqual(build_intelligence('nba',[item],NOW)['devigged_odds'],[])

    def test_timestamp_skew_blocks_false_cross_book_arbitrage(self):
        item=fixture(); item['offers']=quote('a',(2.2,1.8),age=60)+quote('b',(1.8,2.2),age=300)
        self.assertEqual(build_intelligence('nba',[item],NOW)['arbitrage'],[])

    def test_zero_wrong_sum_stale_and_settlement_mismatch_models_rejected(self):
        for field,value in [('probabilities',{'home_win':1.,'away_win':0.}),
                            ('probabilities',{'home_win':.7,'away_win':.7}),
                            ('generated_at',(NOW-timedelta(days=2)).isoformat()),('settlement_rule','REGULATION_ONLY')]:
            item=fixture(); item['prediction']={**prediction(item),field:value}
            self.assertEqual(build_intelligence('nba',[item],NOW)['predictions'],[])

    def test_props_never_pair_different_player_lines_or_markets(self):
        item=fixture()
        item['offers']=quote(market='player_points',player='Player A',line=20.5)[:1]+quote(market='player_points',player='Player B',line=20.5)[1:]
        self.assertEqual(build_intelligence('nba',[item],NOW)['player_props'],[])
        item['offers']=quote(market='player_points',player='Player A',line=20.5)[:1]+quote(market='player_points',player='Player A',line=21.5)[1:]
        self.assertEqual(build_intelligence('nba',[item],NOW)['player_props'],[])
        item['offers']=quote(market='player_points',player='Player A',line=20.5)
        self.assertEqual(len(build_intelligence('nba',[item],NOW)['player_props']),1)

    def test_push_markets_do_not_claim_ev_or_arbitrage(self):
        item=fixture(); item['offers']=quote('a',(2.2,1.8),market='player_points',player='Player',line=20)+quote('b',(1.8,2.2),market='player_points',player='Player',line=20)
        result=build_intelligence('nba',[item],NOW)
        self.assertTrue(result['player_props'][0]['push_probability_unmodeled'])
        self.assertEqual(result['arbitrage'],[]); self.assertEqual(result['ev_bets'],[])

    def test_snapshot_expires_on_read_without_refresh(self):
        item=fixture(); item['offers']=quote(); item['prediction']=prediction(item)
        self.assertEqual(build_intelligence('nba',[item],NOW+timedelta(minutes=31))['devigged_odds'],[])

    def test_cross_sport_and_live_fixtures_excluded(self):
        item=fixture('wnba'); self.assertEqual(build_intelligence('nba',[item],NOW)['summary']['fixtures'],0)
        item=fixture(); item['status']='LIVE'; self.assertEqual(build_intelligence('nba',[item],NOW)['summary']['fixtures'],0)

    def test_merge_exact_fixtures_preserves_distinct_games(self):
        item=fixture(); copy_item=copy.deepcopy(item); copy_item['fixture_id']='other-id'; copy_item['offers']=quote()
        self.assertEqual(len(merge_fixtures([item,copy_item])),1)
        copy_item['kickoff']=(NOW+timedelta(days=1)).isoformat()
        self.assertEqual(len(merge_fixtures([item,copy_item])),2)

    def test_all_sources_failed_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'snapshot.json'; path.write_text('previous')
            with patch('etl.betting_intel.load_football',side_effect=RuntimeError),patch('etl.betting_intel.load_heritage',side_effect=RuntimeError),patch('etl.betting_intel.load_raw',side_effect=RuntimeError),patch('etl.fetch_nba_public_odds.load_validated',side_effect=RuntimeError):
                with self.assertRaises(RuntimeError): refresh(path,include_candidates=False)
            self.assertEqual(path.read_text(),'previous')

    def test_router_overview_sport_and_missing_snapshot(self):
        with tempfile.TemporaryDirectory() as temp,patch('api.routers.betting_intel.SNAPSHOT_PATH',Path(temp)/'snapshot.json'):
            with self.assertRaises(HTTPException) as error: overview()
            self.assertEqual(error.exception.status_code,503)
            path=Path(temp)/'snapshot.json'
            path.write_text(json.dumps({'schema_version':1,'snapshot_at':NOW.isoformat(),'fixtures':[fixture()]}))
            self.assertEqual(len(overview()['sports']),6)
            self.assertEqual(sport_intelligence('nba',None)['sport'],'nba')
            with self.assertRaises(HTTPException) as error: sport_intelligence('bogus',None)
            self.assertEqual(error.exception.status_code,404)


def prop_event():
    return {'id':'provider-id','sport_key':'basketball_nba','home_team':'Boston Celtics','away_team':'New York Knicks',
            'commence_time':(NOW+timedelta(hours=2)).isoformat(),'bookmakers':[{'key':'a','markets':[{
                'key':'player_points','last_update':NOW.isoformat(),'outcomes':[
                    {'name':'Over','description':'Player A','point':20.5,'price':1.9},
                    {'name':'Under','description':'Player A','point':20.5,'price':1.95}]}]}]}


class PropIngestionTests(unittest.TestCase):
    def test_complete_pairs_preserve_fixture_and_market_timestamp(self):
        props=extract_player_props(prop_event())
        self.assertEqual(len(props),1)
        self.assertEqual(props[0]['provider_event_id'],'provider-id')
        self.assertEqual(props[0]['league'],'basketball_nba')
        self.assertEqual(props[0]['over_odds'],1.9); self.assertEqual(props[0]['under_odds'],1.95)

    def test_incomplete_and_nonfinite_props_rejected(self):
        event=prop_event(); event['bookmakers'][0]['markets'][0]['outcomes'].pop()
        self.assertEqual(extract_player_props(event),[])
        event=prop_event(); event['bookmakers'][0]['markets'][0]['outcomes'][0]['price']=float('nan')
        self.assertEqual(extract_player_props(event),[])

    def test_unmatched_or_ambiguous_events_never_receive_props(self):
        for matches in ([],['one','two']):
            engine=MagicMock(); conn=engine.begin.return_value.__enter__.return_value
            conn.execute.return_value.scalars.return_value.all.return_value=matches
            self.assertEqual(write_player_props(engine,extract_player_props(prop_event())),0)
            self.assertEqual(conn.execute.call_count,1)

    def test_additional_markets_use_event_endpoint_decimal_and_bound(self):
        session=MagicMock(); session.get.return_value.json.side_effect=[
            [{k:v for k,v in prop_event().items() if k!='bookmakers'}],prop_event()]
        with patch('etl.ingest_player_props.THE_ODDS_API_KEY','test-only'),patch('etl.ingest_player_props.get_requests_session',return_value=session):
            result=fetch_player_props_for_sport('basketball_nba',max_events=1)
        self.assertEqual(len(result),1)
        self.assertIn('/events/provider-id/odds',session.get.call_args.args[0])
        self.assertEqual(session.get.call_args.kwargs['params']['oddsFormat'],'decimal')

    def test_raw_nba_adapter_does_not_accept_wnba_as_nba(self):
        event=prop_event(); event['sport_key']='basketball_wnba'
        item=raw_event(event,NOW)
        self.assertEqual(item['sport'],'wnba')


if __name__=='__main__':
    unittest.main()
