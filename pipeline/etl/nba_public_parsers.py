"""Strict NBA moneyline adapters; no fuzzy team matching or regulation/OT mixing."""
from datetime import datetime,timezone
import math

NAMES = {
 'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BKN':'Brooklyn Nets','CHA':'Charlotte Hornets',
 'CHI':'Chicago Bulls','CLE':'Cleveland Cavaliers','DAL':'Dallas Mavericks','DEN':'Denver Nuggets',
 'DET':'Detroit Pistons','GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers',
 'LAC':'Los Angeles Clippers','LAL':'Los Angeles Lakers','MEM':'Memphis Grizzlies','MIA':'Miami Heat',
 'MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves','NOP':'New Orleans Pelicans','NYK':'New York Knicks',
 'OKC':'Oklahoma City Thunder','ORL':'Orlando Magic','PHI':'Philadelphia 76ers','PHX':'Phoenix Suns',
 'POR':'Portland Trail Blazers','SAC':'Sacramento Kings','SAS':'San Antonio Spurs','TOR':'Toronto Raptors',
 'UTA':'Utah Jazz','WAS':'Washington Wizards',
}
ALIASES={name.casefold():name for name in NAMES.values()}
ALIASES.update({name.casefold().replace('los angeles','la'):name for name in NAMES.values() if name.startswith('Los Angeles')})
ALIASES.update({'l.a. clippers':NAMES['LAC'],'l.a. lakers':NAMES['LAL']})
for abbr,name in NAMES.items():
    nickname = name.split(' ', 2)[-1] if abbr in ('GSW','LAC','LAL','NOP','NYK','OKC','SAS') else name.split(' ',1)[1]
    ALIASES[(abbr+' '+nickname).casefold()]=name
ALIASES.update({'ny knicks':NAMES['NYK'],'sa spurs':NAMES['SAS'],'gs warriors':NAMES['GSW'],
                'no pelicans':NAMES['NOP'],'la clippers':NAMES['LAC'],'la lakers':NAMES['LAL']})


def team(value):
    return ALIASES.get(str(value).strip().casefold())


def instant(value):
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def price(value):
    try:
        number=float(value)
        return number if math.isfinite(number) and number>1 else None
    except (ValueError,TypeError):
        return None


def fixture(book,event_id,home,away,kickoff,observed,prices,market_id,raw_ref,source_url):
    home,away=team(home),team(away)
    kickoff,observed=instant(kickoff),instant(observed)
    if not home or not away or home==away or not event_id or not kickoff or not observed or kickoff<=observed:
        return None
    if set(prices)!={'home_win','away_win'} or any(price(v) is None for v in prices.values()):
        return None
    # Reject clearly broken pairs, but retain genuine cross-book disagreement.
    overround=sum(1/float(p) for p in prices.values())-1
    if not -.02 <= overround <= .30:
        return None
    return {'fixture_id':book+':'+str(event_id),'sport':'nba','competition':'NBA','home_team':home,'away_team':away,
            'kickoff':kickoff.isoformat(),'status':'SCHEDULED','settlement_rule':'INCLUDING_OVERTIME',
            'offers':[{'market':'h2h','selection':key,'decimal_odds':float(value),'bookmaker':book,
                       'observed_at':observed.isoformat(),'provider_event_id':str(event_id),'provider_market_id':str(market_id),
                       'period':'FULL_GAME_INCLUDING_OVERTIME','source_url':source_url,'raw_capture_ref':raw_ref}
                      for key,value in prices.items()]}


def bovada(payload,observed,raw_ref):
    results=[]
    for group in payload:
        leagues=[p for p in group.get('path',[]) if p.get('type')=='LEAGUE']
        if len(leagues)!=1 or leagues[0].get('description')!='NBA' or leagues[0].get('sportCode')!='BASK':
            continue
        for event in group.get('events',[]):
            if event.get('type')!='GAMEEVENT' or event.get('sport')!='BASK' or event.get('live') is not False or event.get('status')!='U':
                continue
            home=[t for t in event.get('competitors',[]) if t.get('home') is True]
            away=[t for t in event.get('competitors',[]) if t.get('home') is False]
            if len(home)!=1 or len(away)!=1 or home[0].get('id')==away[0].get('id'):
                continue
            try: kickoff=datetime.fromtimestamp(float(event['startTime'])/1000,timezone.utc).isoformat()
            except (ValueError,TypeError,KeyError,OverflowError,OSError): continue
            for display in event.get('displayGroups',[]):
                for market in display.get('markets',[]):
                    period=market.get('period',{})
                    if (market.get('key')!='2W-12' or market.get('description')!='Moneyline' or market.get('status')!='O'
                        or str(period.get('id'))!='209' or period.get('description')!='Game' or period.get('main') is not True or period.get('live') is not False):
                        continue
                    prices={}
                    for leg in market.get('outcomes',[]):
                        key={'H':'home_win','A':'away_win'}.get(leg.get('type'))
                        competitor=home[0] if key=='home_win' else away[0]
                        if not key or key in prices or leg.get('status')!='O' or leg.get('competitorId')!=competitor.get('id'):
                            prices={};break
                        decimal=price(leg.get('price',{}).get('decimal'))
                        try:
                            american=float(leg['price']['american'])
                            converted=1+american/100 if american>0 else 1+100/abs(american)
                        except (KeyError,ValueError,TypeError,ZeroDivisionError): prices={};break
                        if decimal is None or not math.isfinite(american) or abs(american)<100 or abs(decimal-converted)>.001:
                            prices={};break
                        prices[key]=decimal
                    row=fixture('bovada',event.get('id'),home[0].get('name'),away[0].get('name'),kickoff,observed,prices,market.get('id'),raw_ref,
                                'https://www.bovada.lv/sports'+event.get('link','/basketball/nba'))
                    if row: results.append(row)
    return results


def cloudbet(payload,observed,raw_ref):
    if payload.get('key')!='basketball-usa-nba' or payload.get('sport',{}).get('key')!='basketball' or payload.get('blank'):
        return []
    results=[]
    for event in payload.get('events',[]):
        if event.get('type')!='EVENT_TYPE_EVENT' or event.get('status')!='TRADING' or event.get('metadata',{}).get('eventStatus')!='not_started' or event.get('blank'):
            continue
        market=event.get('markets',{}).get('basketball.moneyline',{}).get('submarkets',{}).get('period=ot&period=ft')
        if not market or market.get('blank'): continue
        prices={}
        for leg in market.get('selections',[]):
            key={'home':'home_win','away':'away_win'}.get(leg.get('outcome'))
            if (not key or key in prices or leg.get('status')!='SELECTION_ENABLED' or leg.get('side')!='BACK'
                or leg.get('params') or leg.get('marketUrl')!='basketball.moneyline/'+leg['outcome']):
                prices={};break
            if 'maxStake' in leg:
                try: available=float(leg['maxStake'])
                except (TypeError,ValueError): prices={};break
                if not math.isfinite(available) or available<=0: prices={};break
            prices[key]=leg.get('price')
        row=fixture('cloudbet',event.get('id'),(event.get('home') or {}).get('name'),(event.get('away') or {}).get('name'),
                    event.get('startTime'),observed,prices,'basketball.moneyline/period=ot&period=ft',raw_ref,
                    'https://www.cloudbet.com/en/sports/basketball/usa-nba')
        if row: results.append(row)
    return results


def betpawa(payload,observed,raw_ref):
    results=[]
    for batch in payload.get('responses',[]):
        for event in batch.get('responses',[]):
            if (event.get('category',{}).get('id')!='3' or event.get('region',{}).get('name')!='USA'
                or event.get('competition',{}).get('name')!='NBA' or event.get('additionalInfo',{}).get('live') is not False
                or event.get('scoreboard') or event.get('results')): continue
            if len(event.get('participants',[]))!=2: continue
            participants={p.get('position'):p for p in event.get('participants',[])}
            if set(participants)!={1,2}: continue
            for market in event.get('markets',[]):
                definition=market.get('marketType',{})
                if definition.get('name')!='Moneyline - FT incl OT' or 'overtime' not in definition.get('explainer','').lower(): continue
                if market.get('additionalInfo',{}).get('boosted'): continue
                for group in market.get('row',[]):
                    prices={}
                    for leg in group.get('prices',[]):
                        key={'1':'home_win','2':'away_win'}.get(leg.get('name'))
                        if (not key or key in prices or leg.get('suspended') is not False
                            or leg.get('additionalInfo',{}).get('suspended') or leg.get('status') in ('SUSPENDED','CLOSED')):
                            prices={};break
                        prices[key]=leg.get('odds')
                    row=fixture('betpawa:UG',event.get('id'),participants[1].get('name'),participants[2].get('name'),
                                event.get('startTime'),observed,prices,group.get('id'),raw_ref,
                                'https://www.betpawa.ug/events?categoryId=3')
                    if row: results.append(row)
    return results


def validate_fixtures(fixtures,games,now):
    """A bookmaker fixture must exactly match an independent NBA schedule entry."""
    index={}
    for game in games:
        kickoff=instant(game.get('datetime'))
        home=team(game.get('home_team',{}).get('full_name'))
        away=team(game.get('visitor_team',{}).get('full_name'))
        if not kickoff or not home or not away: continue
        index.setdefault((home,away,kickoff),[]).append(game)
    accepted,rejected=[],[]
    for row in fixtures:
        matches=index.get((row['home_team'],row['away_team'],instant(row['kickoff'])),[])
        reason=None
        if len(matches)!=1: reason='no_unique_independent_fixture'
        elif matches[0].get('postponed') or matches[0].get('status_state')!='scheduled' or matches[0].get('period')!=0: reason='independent_fixture_not_scheduled'
        elif instant(row['kickoff'])<=now: reason='already_started'
        if reason:
            rejected.append({'fixture_id':row['fixture_id'],'home_team':row['home_team'],'away_team':row['away_team'],'kickoff':row['kickoff'],'reason':reason})
        else:
            accepted.append({**row,'independent_validation':{'provider':'balldontlie','game_id':matches[0]['id'],
                'checks':['NBA team identity','home_away_orientation','exact_UTC_kickoff','scheduled_status']}})
    return accepted,rejected
