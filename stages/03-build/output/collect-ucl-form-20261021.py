"""Collect current-season senior archives for today's 18 UCL teams."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,importlib.util,json,sys
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
OUT=ROOT/'pipeline/data/raw/ucl_today_20261021_form';OUT.mkdir(parents=True,exist_ok=True)
http=ScraplingTransport();sources=[]
def capture(name,url):
    path=OUT/(name+'.raw')
    if path.exists():
        content=path.read_bytes()
        sources.append({'name':name,'url':url,'captured_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'sha256':hashlib.sha256(content).hexdigest(),'file':path.name,'cached_local':True})
        return content
    response=http.get(url,timeout=25);response.raise_for_status()
    path=OUT/(name+'.raw');path.write_bytes(response.content)
    sources.append({'name':name,'url':url,'captured_at':datetime.now(timezone.utc).isoformat(),
                    'status':response.status_code,'sha256':hashlib.sha256(response.content).hexdigest(),'file':path.name})
    return response.content
body=capture('terrikon_cl','https://terrikon.com/en/champions-league')
tree=html.fromstring(body)
identities={}
import re
for a in tree.xpath('//a[@href]'):
    match=re.fullmatch(r'/en/football/teams/(\d+)',a.get('href'))
    if match: identities[' '.join(a.text_content().split())]=match[1]
print(json.dumps({'discovered_teams':identities}),flush=True)
aliases={
 'Como':['Como','Como 1907'],'Man United':['Man United','Manchester Utd','Manchester United'],
 'Lille':['Lille'],'Galatasaray':['Galatasaray'],'Aston Villa':['Aston Villa'],'Viking':['Viking','Viking FK'],
 'Club Brugge':['Club Brugge','Brugge'],'Lens':['Lens'],'Bayern Munich':['Bayern','Bayern Munich'],
 'Arsenal':['Arsenal'],'Inter':['Inter'],'Shakhtar':['Shakhtar'],'Real Madrid':['Real','Real Madrid'],
 'RB Leipzig':['Leipzig','RB Leipzig'],'Betis':['Betis','Real Betis'],'Feyenoord':['Feyenoord'],
 'Sp Lisbon':['Sporting','Sporting CP','Sporting Lisbon','Sp Lisbon'],'LASK':['LASK','LASK Linz'],
}
spec=importlib.util.spec_from_file_location('archive_parser',ROOT/'stages/03-build/output/collect-ucl-history-20261020.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
import pandas as pd
parser.START=pd.Timestamp('2026-07-01',tz='UTC');parser.CUTOFF=pd.Timestamp('2026-10-21',tz='UTC')
rows=[];exclusions=[];coverage=[]
def run(item):
    name,variants=item
    ids={identities[v] for v in variants if v in identities}
    if len(ids)!=1:return {'team':name,'error':'ambiguous_or_missing_identity','variants':variants},[],[]
    tid=next(iter(ids));url=f'https://terrikon.com/en/football/teams/{tid}/gamesarchive'
    try:
        content=capture('team_'+tid,url);matches,rejected=parser.parse_archive(content,url)
        return {'team':name,'provider_id':tid,'source_names':[v for v in variants if v in identities],'results':len(matches)},matches,rejected
    except Exception as exc:return {'team':name,'error':type(exc).__name__},[],[]
with ThreadPoolExecutor(max_workers=3) as executor:
    for info,matches,rejected in executor.map(run,aliases.items()):
        coverage.append(info);rows.extend(matches);exclusions.extend(rejected);print(json.dumps(info),flush=True)
report={'captured_at':datetime.now(timezone.utc).isoformat(),'sources':sources,'coverage':coverage,'results':rows,'exclusions':exclusions,
        'note':'Simple archive scores only; regulation-time basis for cup games is not independently proven. No database writes.'}
(OUT/'archives.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'output':str(OUT),'rows':len(rows),'coverage':coverage}),flush=True)
