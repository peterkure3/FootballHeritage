"""Scrapling public NBA moneylines, independently checked against BALLDONTLIE."""
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
import hashlib,json,os,math
from pathlib import Path
import time

import requests

from config import RAW_DATA_DIR
from etl.nba_public_parsers import bovada,cloudbet,betpawa,validate_fixtures

ROOT=RAW_DATA_DIR/'nba_public'


def check_price_response(headers,observed):
    age=float(headers.get('Age','0'))
    if not math.isfinite(age) or not 0<=age<=120:
        raise ValueError('Cached price response exceeds freshness allowance')
    if headers.get('Date'):
        age=(observed-parsedate_to_datetime(headers['Date'])).total_seconds()
        if not -60<=age<=180:
            raise ValueError('HTTP price response date is stale or in the future')


def collect(output=None):
    from etl.scrapling_transport import ScraplingTransport,USER_AGENT
    now=datetime.now(timezone.utc)
    output=Path(output or ROOT/now.strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(parents=True,exist_ok=False)
    transport=ScraplingTransport()
    captures,failures,unvalidated=[],[],[]

    def capture(name,url,params=None,headers=None):
        response=transport.get(url,params=params,headers={'User-Agent':USER_AGENT,'Accept':'application/json,text/html',
            'Cache-Control':'no-cache',**(headers or {})},timeout=25)
        observed=datetime.now(timezone.utc)
        path=output/(name+'.raw');path.write_bytes(response.content)
        entry={'name':name,'url':response.url,'http_status':response.status_code,'captured_at':observed.isoformat(),
               'file':path.name,'sha256':hashlib.sha256(response.content).hexdigest(),
               'http_date':response.headers.get('Date'),'cache_age':response.headers.get('Age')}
        captures.append(entry)
        response.raise_for_status()
        if not name.endswith('-feed'):
            return response,entry
        check_price_response(response.headers,observed)
        return response,entry

    pages={'bovada':'https://www.bovada.lv/sports/basketball/nba',
           'cloudbet':'https://www.cloudbet.com/en/sports/basketball',
           'betpawa':'https://www.betpawa.ug/'}
    for book,page in pages.items():
        try:
            capture(book+'-page',page)
            if book=='bovada':
                response,entry=capture('bovada-feed','https://www.bovada.lv/services/sports/event/coupon/events/A/description/basketball/nba',
                                       {'marketFilterId':'def','preMatchOnly':'true'})
                payload=response.json();rows=bovada(payload,entry['captured_at'],entry['file'])
                entry['event_count']=sum(len(group.get('events',[])) for group in payload)
            elif book=='cloudbet':
                response,entry=capture('cloudbet-feed','https://www.cloudbet.com/sports-api/c/v6/sports/competitions/basketball-usa-nba/events',
                    {'from':str(int(now.timestamp())),'limit':100,'locale':'en','markets':'basketball.moneyline','sports':'basketball',
                     'include-all-event-types':'false','include-pretrading':'false'}, {'x-cloudbet-version':'v1.2.27'})
                payload=response.json();rows=cloudbet(payload,entry['captured_at'],entry['file'])
                entry['event_count']=len(payload.get('events',[]))
                entry['response_limit_reached']=entry['event_count']>=100
            else:
                headers={'X-Pawa-Brand':'betpawa-uganda','X-Pawa-Language':'en'}
                response,_=capture('betpawa-directory','https://www.betpawa.ug/api/sportsbook/v4/categories/list/3',headers=headers)
                ids=[comp['competition']['id'] for category in response.json().get('withRegions',[]) if category.get('category',{}).get('id')=='3'
                     for region in category.get('regions',[]) if region.get('region',{}).get('name')=='USA'
                     for comp in region.get('competitions',[]) if comp.get('competition',{}).get('name')=='NBA']
                if len(ids)!=1: raise ValueError('NBA competition directory is ambiguous')
                query={'queries':[{'query':{'eventType':'UPCOMING','categories':['3'],'zones':{'competitions':ids},'hasOdds':True},
                                   'sort':{'startTime':'ASC'},'take':100}]}
                response,entry=capture('betpawa-feed','https://www.betpawa.ug/api/sportsbook/v4/events/lists/by-queries',
                                       {'q':json.dumps(query)},headers)
                payload=response.json();rows=betpawa(payload,entry['captured_at'],entry['file'])
                entry['event_count']=sum(len(batch.get('responses',[])) for batch in payload.get('responses',[]))
                entry['response_limit_reached']=entry['event_count']>=100
            entry['parsed_complete_moneylines']=len(rows)
            unvalidated.extend(rows)
            print(json.dumps({'bookmaker':book,'parsed_complete_moneylines':len(rows)}),flush=True)
        except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
            failures.append({'source':book,'reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
            print(json.dumps(failures[-1]),flush=True)

    # The independent schedule is authoritative for identities and start times,
    # not for bookmaker price correctness or executable availability.
    key=os.getenv('BALLDONTLIE_API_KEY')
    games=[];cursor=None;seen=set()
    try:
        if not key: raise ValueError('BALLDONTLIE key is not configured')
        for page in range(5):
            params={'start_date':(now-timedelta(days=1)).date().isoformat(),
                    'end_date':(now+timedelta(days=7)).date().isoformat(),'per_page':100}
            if cursor is not None: params['cursor']=cursor
            response=requests.get('https://api.balldontlie.io/v1/games',params=params,headers={'Authorization':key},timeout=35)
            safe=response.text.replace(key,'[REDACTED]').encode()
            path=output/f'balldontlie-games-{page+1}.json';path.write_bytes(safe)
            captures.append({'name':'balldontlie-games','url':'https://api.balldontlie.io/v1/games','params':params,
                'http_status':response.status_code,'captured_at':datetime.now(timezone.utc).isoformat(),
                'file':path.name,'sha256':hashlib.sha256(safe).hexdigest()})
            response.raise_for_status()
            payload=json.loads(safe)
            games.extend(payload.get('data',[]))
            cursor=payload.get('meta',{}).get('next_cursor')
            if cursor is None: break
            if cursor in seen: raise ValueError('Repeated schedule cursor')
            seen.add(cursor);time.sleep(13)
        else: raise ValueError('Schedule pagination limit exceeded')
        if len({g['id'] for g in games})!=len(games): raise ValueError('Duplicate schedule game IDs')
    except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
        failures.append({'source':'independent_schedule','reason':type(exc).__name__})
        games=[]
    accepted,rejected=validate_fixtures(unvalidated,games,datetime.now(timezone.utc))
    fixtures_path=output/'validated_fixtures.json'
    fixtures_path.write_text(json.dumps(accepted,indent=2,allow_nan=False),encoding='utf-8')
    (output/'quarantined_fixtures.json').write_text(json.dumps(rejected,indent=2),encoding='utf-8')
    by_book={}
    for row in accepted:
        book=row['offers'][0]['bookmaker'];by_book[book]=by_book.get(book,0)+1
    manifest={'schema_version':1,'transport':'scrapling','started_at':now.isoformat(),
        'completed_at':datetime.now(timezone.utc).isoformat(),'captures':captures,'source_errors':failures,
        'independent_games':len(games),'parsed_moneylines':len(unvalidated),'validated_moneylines':len(accepted),
        'quarantined_moneylines':len(rejected),'bookmakers':by_book,'fixtures_file':fixtures_path.name,
        'fixtures_sha256':hashlib.sha256(fixtures_path.read_bytes()).hexdigest(),
        'execution_verified':False,'scope':'Bounded public NBA full-game moneylines including overtime; not all bookmaker markets.',
        'validation':'Independent game identity, orientation, exact UTC kickoff and scheduled state; complete open bookmaker market and price format checks.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'capture_dir':str(output),**{k:v for k,v in manifest.items() if k!='captures'}},indent=2),flush=True)
    if not accepted: raise RuntimeError('No independently validated NBA prices; nothing eligible for publication')
    return manifest


def load_validated(now):
    """Only fresh, checksummed successful captures may enter intelligence."""
    candidates=[]
    for path in sorted(ROOT.glob('*/manifest.json'),reverse=True):
        manifest=json.loads(path.read_text(encoding='utf-8'))
        if manifest.get('schema_version')!=1 or not manifest.get('validated_moneylines'): continue
        completed=datetime.fromisoformat(manifest['completed_at'])
        if not 0<=(now-completed).total_seconds()<=1800: continue
        data=path.parent/'validated_fixtures.json'
        if hashlib.sha256(data.read_bytes()).hexdigest()!=manifest['fixtures_sha256']:
            raise ValueError('NBA normalized capture checksum mismatch')
        for capture in manifest['captures']:
            raw=path.parent/capture['file']
            if hashlib.sha256(raw.read_bytes()).hexdigest()!=capture['sha256']:
                raise ValueError('NBA source evidence checksum mismatch')
        candidates.extend(json.loads(data.read_text(encoding='utf-8')))
        break
    return candidates


def source_status(now):
    for path in sorted(ROOT.glob('*/manifest.json'),reverse=True):
        manifest=json.loads(path.read_text(encoding='utf-8'))
        if manifest.get('schema_version')!=1: continue
        completed=datetime.fromisoformat(manifest['completed_at'])
        if 0<=(now-completed).total_seconds()<=1800:
            return [{'source':'nba_public:'+error['source'],'reason':error['reason']} for error in manifest.get('source_errors',[])]
    return []


def current_schedule(now):
    """The same fresh independent schedule also checks older stored fixtures."""
    for path in sorted(ROOT.glob('*/manifest.json'),reverse=True):
        manifest=json.loads(path.read_text(encoding='utf-8'))
        if manifest.get('schema_version')!=1 or not manifest.get('independent_games'): continue
        completed=datetime.fromisoformat(manifest['completed_at'])
        if not 0<=(now-completed).total_seconds()<=1800: continue
        games=[]
        for capture in manifest['captures']:
            if capture['name']!='balldontlie-games': continue
            raw=path.parent/capture['file']
            if hashlib.sha256(raw.read_bytes()).hexdigest()!=capture['sha256']:
                raise ValueError('Independent NBA schedule checksum mismatch')
            games.extend(json.loads(raw.read_text(encoding='utf-8'))['data'])
        return games
    return []


if __name__=='__main__':
    collect()
