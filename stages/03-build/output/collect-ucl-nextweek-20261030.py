"""Capture fresh UCL history, form and public sportsbook evidence without DB writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline'))
OUT = ROOT/'pipeline/data/raw/ucl_nextweek_20261030'
OUT.mkdir(parents=True, exist_ok=True)

def save(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

def official(phase):
    from config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL
    from etl.fetch_raw_data import FootballDataOrgFetcher
    client = FootballDataOrgFetcher(FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_ORG_BASE_URL)
    directory = ROOT/'pipeline/data/raw/league_training/ucl_nextweek_20261030'
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory/'manifest.json' if phase == 'history' else OUT/'form-sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'sources': []}
    def fetch(name, route, params, target):
        path = target/(name+'.json')
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        url = client.base_url+route
        try:
            response = client.session.get(url, headers=client.headers, params=params, timeout=30)
            entry = {'filename': path.name, 'url': url, 'params': params,
                     'observed_at': datetime.now(timezone.utc).isoformat(), 'http_status': response.status_code,
                     'status': 'collected' if response.ok else 'unavailable'}
            payload = response.json() if response.ok else {}
            if response.ok:
                save(path, payload)
                entry['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest['sources'].append(entry)
            save(manifest_path, manifest)
            print(json.dumps(entry | {'matches': len(payload.get('matches', []))}), flush=True)
            return payload
        finally:
            time.sleep(7)
    if phase == 'history':
        for year in [2018, 2019, 2020, 2021, 2022, 2026]:
            payload = fetch('CL_'+str(year), '/competitions/CL/matches', {'season': year}, directory)
            if year == 2026:
                fixtures = [m for m in payload.get('matches', []) if '2026-11-03' <= m['utcDate'][:10] <= '2026-11-04']
                save(OUT/'fixtures.json', fixtures)
    else:
        fixtures = json.loads((OUT/'fixtures.json').read_text(encoding='utf-8'))
        teams = {str(m[side]['id']): m[side]['name'] for m in fixtures for side in ['homeTeam', 'awayTeam']}
        for tid, team in teams.items():
            fetch('team_'+tid, '/teams/'+tid+'/matches',
                  {'dateFrom': '2026-07-01', 'dateTo': '2026-10-30', 'status': 'FINISHED', 'limit': 50}, OUT)
        save(manifest_path, manifest)

def markets():
    from etl.scrape_sportsbooks import collect_target, utc_now
    from etl.scrapling_transport import ScraplingTransport
    from etl.regional_sportsbooks import normalize_fortebet, normalize_cloudbet, normalize_betpawa, normalize_sportpesa
    folder = OUT/'sportsbooks'
    (folder/'raw').mkdir(parents=True, exist_ok=True)
    targets = json.loads((ROOT/'_config/bookmakers.json').read_text(encoding='utf-8'))['sportsbooks']
    parsers = {'fortebet': normalize_fortebet, 'cloudbet': normalize_cloudbet,
               'betpawa': normalize_betpawa, 'sportpesa': normalize_sportpesa}
    http = ScraplingTransport()
    sources, records = [], []
    for target in targets:
        book = target['bookmaker']
        if book not in parsers:
            continue
        source = collect_target(target, folder, http)
        if source.get('http_status') in [200, 206]:
            try:
                payload = json.loads((folder/source['raw_capture_ref']).read_text(encoding='utf-8'))
                parsed = parsers[book](payload, source['observed_at'], source['raw_capture_ref'], 'ucl_nextweek_20261030')
                records.extend(parsed)
                source.update(status='collected', snapshots=len(parsed))
            except Exception as exc:
                source.update(status='parser_failed', error_type=type(exc).__name__)
        sources.append(source)
        print(json.dumps(source), flush=True)
    for book, url in [('stake', 'https://stake.com/sports/soccer'),
                      ('fortebet_desktop', 'https://desktop.fortebet.ug/prematch/sports')]:
        sources.append(collect_target({'bookmaker':book, 'source_url':url, 'region':'UG'}, folder, http))
    save(folder/'source_report.json', {'observed_at':utc_now(), 'sources':sources, 'snapshots':len(records)})
    (folder/'odds_snapshots.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in records), encoding='utf-8')
    print('MARKETS_SAVED',len(records), flush=True)

def archives():
    import importlib.util
    import re
    from concurrent.futures import ThreadPoolExecutor
    import pandas as pd
    from lxml import html
    from etl.scrapling_transport import ScraplingTransport
    from models.league_data import identity, identity_aliases
    spec = importlib.util.spec_from_file_location('archive_parser', Path(__file__).with_name('collect-ucl-history-20261020.py'))
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    parser.START = pd.Timestamp('2026-07-01', tz='UTC')
    parser.CUTOFF = pd.Timestamp('2026-10-30', tz='UTC')
    aliases = identity_aliases()
    http = ScraplingTransport()
    folder = OUT/'archives'
    folder.mkdir(exist_ok=True)
    page = http.get('https://terrikon.com/en/champions-league', timeout=25)
    page.raise_for_status()
    (folder/'directory.html').write_bytes(page.content)
    names = {}
    for anchor in html.fromstring(page.content).xpath('//a[@href]'):
        match = re.fullmatch(r'/en/football/teams/(\d+)', anchor.get('href'))
        if match:
            names[' '.join(anchor.text_content().split())] = match[1]
    save(folder/'directory.json', names)
    extra = {'Bayern':'Bayern Munich', 'Sporting':'Sp Lisbon', 'Betis':'Betis',
             'Borussia D':'Dortmund','PSG':'Paris SG','Man United':'Man United',
             'Sabah FC':'Sabah FK','Slovan B':'Slovan Bratislava','Shakhtar':'Shakhtar Donetsk',
             'Bodo/Glimt':'Bodø/Glimt','Leipzig':'RB Leipzig'}
    by_key = {}
    for name, tid in names.items():
        by_key.setdefault(identity(extra.get(name,name), aliases), set()).add(tid)
    fixtures = json.loads((OUT/'fixtures.json').read_text(encoding='utf-8'))
    teams = sorted({m[side]['name'] for m in fixtures for side in ['homeTeam','awayTeam']})
    def collect(team):
        tids = by_key.get(identity(team,aliases), set())
        if len(tids) != 1:
            return {'team':team,'status':'identity_unresolved','results':[]}
        tid = next(iter(tids))
        url = f'https://terrikon.com/en/football/teams/{tid}/gamesarchive'
        try:
            response = http.get(url,timeout=25)
            response.raise_for_status()
            path = folder/('team_'+tid+'.html')
            path.write_bytes(response.content)
            rows, rejected = parser.parse_archive(response.content,url)
            time.sleep(1)
            return {'team':team,'status':'collected','url':url,
                    'observed_at':datetime.now(timezone.utc).isoformat(),
                    'sha256':hashlib.sha256(response.content).hexdigest(), 'results':rows,'excluded':rejected}
        except Exception as exc:
            return {'team':team,'status':type(exc).__name__,'results':[]}
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as executor:
        for row in executor.map(collect,teams):
            rows.append(row)
            print(json.dumps({'team':row['team'],'status':row['status'],'matches':len(row['results'])}),flush=True)
    save(folder/'results.json',rows)

def stake():
    from bs4 import BeautifulSoup
    from etl.scrapling_transport import ScraplingTransport
    url = 'https://stake.com/sports/soccer/international-clubs/uefa-champions-league'
    response = ScraplingTransport().get(url,timeout=30)
    response.raise_for_status()
    folder = OUT/'sportsbooks'
    (folder/'raw/stake-ucl.html').write_bytes(response.content)
    soup = BeautifulSoup(response.text, 'html.parser')
    data = [json.loads(json.loads(s.string)['body']) for s in soup.select('script[data-sveltekit-fetched]') if s.string]
    todo, fixtures = list(data), {}
    while todo:
        value = todo.pop()
        if isinstance(value,dict):
            if value.get('__typename') == 'SportFixture':
                fixtures[value['id']] = value
            todo.extend(value.values())
        elif isinstance(value,list): todo.extend(value)
    save(folder/'stake-fixtures.json',{'url':url,'observed_at':datetime.now(timezone.utc).isoformat(),'fixtures':list(fixtures.values())})
    print('STAKE_FIXTURES',len(fixtures), flush=True)
    if fixtures: print(json.dumps(next(iter(fixtures.values())))[:6500],flush=True)

def viking():
    from etl.scrapling_transport import ScraplingTransport
    url = 'https://www.vikingfotball.no/resultater'
    response = ScraplingTransport().get(url,timeout=30)
    response.raise_for_status()
    path = OUT/'archives/viking-official.html'
    path.write_bytes(response.content)
    save(path.with_suffix('.provenance.json'), {'url':url,'observed_at':datetime.now(timezone.utc).isoformat(),
         'sha256':hashlib.sha256(response.content).hexdigest()})
    print('VIKING_CAPTURED',len(response.content),flush=True)

def domestic():
    from etl.scrapling_transport import ScraplingTransport
    http=ScraplingTransport()
    sources=[]
    folder=OUT/'domestic'
    folder.mkdir(exist_ok=True)
    for name,url in [('slovan.html','https://en.skslovan.com/zapasy/?liga=NL'),
                     ('G1.csv','https://www.football-data.co.uk/mmz4281/2627/G1.csv'),
                     ('NOR.csv','https://www.football-data.co.uk/new/NOR.csv'),
                     ('SVK.csv','https://www.football-data.co.uk/new/SVK.csv')]:
        try:
            if (folder/name).exists():continue
            r=http.get(url,timeout=25)
            entry={'filename':name,'url':url,'status':r.status_code,'observed_at':datetime.now(timezone.utc).isoformat()}
            if r.status_code==200:
                (folder/name).write_bytes(r.content)
                entry['sha256']=hashlib.sha256(r.content).hexdigest()
            sources.append(entry)
            print(json.dumps(entry),flush=True)
        except Exception as exc:sources.append({'filename':name,'url':url,'error':type(exc).__name__})
    save(folder/'sources.json',sources)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['history', 'form', 'markets', 'archives', 'stake', 'viking', 'domestic'])
    phase = parser.parse_args().phase
    if phase == 'markets': markets()
    elif phase == 'archives': archives()
    elif phase == 'stake': stake()
    elif phase == 'viking': viking()
    elif phase == 'domestic': domestic()
    else: official(phase)
