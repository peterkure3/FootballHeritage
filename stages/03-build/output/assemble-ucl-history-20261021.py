"""Reconcile public senior history; retain provenance and quarantine conflicts."""
import ast,sys,json,re,hashlib,importlib.util,collections
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
from lxml import html
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;RAW=ROOT/'pipeline/data/raw/ucl_history_20261021'
sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from models.data import team_key
spec=importlib.util.spec_from_file_location('repair',OUT/'recalibrate-ucl-20261020.py');repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
groups=''
for node in ast.parse((OUT/'analyze-ucl-20261021.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='groups' for t in node.targets):groups=ast.literal_eval(node.value)
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='groups':groups+=ast.literal_eval(node.value)
aliases={team_key(v):line.split('|')[0] for line in groups.splitlines() for v in line.split('|')}
aliases[team_key('Internazionale')]='Inter'
aliases.update({team_key('LOSC Lille'):'Lille',team_key('FC Bayern Munich'):'Bayern Munich'})
def name(s):return aliases.get(team_key(s),repair.reviewed_name(s))
TEAMS=list(dict.fromkeys(line.split('|')[0] for line in groups.splitlines()))[:18]
IDS={'Como':2572,'Man United':360,'Lille':166,'Galatasaray':432,'Aston Villa':362,'Viking':510,'Club Brugge':570,'Lens':175,'Bayern Munich':132,'Arsenal':359,'Inter':110,'Shakhtar Donetsk':493,'Real Madrid':86,'RB Leipzig':11420,'Betis':244,'Feyenoord':142,'Sp Lisbon':2250,'LASK Linz':4411}
assert set(TEAMS)==set(IDS)
START=pd.Timestamp('2023-07-01',tz='UTC');CUTOFF=pd.Timestamp('2026-10-21',tz='UTC')
rows=[];excluded=[];pages=[];source_files={}
def add(row):
    competition=str(row.get('competition','')).lower()
    if any(x in competition for x in ['friendly','friendlies','emirates cup','all-star','summer series','audi cup','sela cup','florida cup','soccer champions tour']):return
    row=row.copy();row['date']=pd.Timestamp(row['date']);row['date']=row['date'].tz_localize('UTC') if row['date'].tzinfo is None else row['date'].tz_convert('UTC')
    row['home_team']=name(row['home_team']);row['away_team']=name(row['away_team'])
    touched=sorted(set([row['home_team'],row['away_team']])&set(TEAMS))
    start=pd.Timestamp('2023-01-01',tz='UTC') if touched==['Viking'] else START
    if not touched or not start<=row['date']<CUTOFF:return
    if row['home_score'] is not None and row['away_score'] is not None:
        row['home_score']=int(row['home_score']);row['away_score']=int(row['away_score'])
        assert row['home_score']>=0 and row['away_score']>=0
    else:assert not row['training_eligible']
    assert row['home_team']!=row['away_team']
    row['date']=row['date'].isoformat();row['target_teams']=touched
    row['result']=None if row['home_score'] is None else 'home_win' if row['home_score']>row['away_score'] else 'away_win' if row['home_score']<row['away_score'] else 'draw'
    rows.append(row)
def state(body):
    tree=html.fromstring(body)
    for s in tree.xpath('//script'):
        txt=s.text or '';m=re.search(r"window\[['\"]__espnfitt__['\"]\]\s*=\s*",txt)
        if m:return json.JSONDecoder().raw_decode(txt[m.end():])[0]['page']['content']['results']
    raise ValueError('ESPN state missing')
def note_file(path,url):
    source_files[str(path.relative_to(ROOT))]={'url':url,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'captured_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()}
for team,tid in IDS.items():
    for season in range(2023,2027):
        path=RAW/f'espn_{tid}_{season}.raw';url=f'https://www.espn.com/soccer/team/results/_/id/{tid}/season/{season}/league/all'
        if not path.exists():pages.append({'team':team,'season':season,'error':'capture_missing'});continue
        note_file(path,url)
        try:
            p=state(path.read_bytes());assert str(p['team']['id'])==str(tid)
            if name(p['team']['displayName'])!=team:raise ValueError('Unreviewed provider identity: '+p['team']['displayName'])
            info={'team':team,'season':season,'events':len(p['events']),'competitions':dict(collections.Counter(e['league'] for e in p['events'])),'provider_team_name':p['team']['displayName']};pages.append(info)
            for e in p['events']:
                if not e.get('completed') or e.get('status',{}).get('state')!='post':continue
                league=e['league'];detail=e['status']['detail'];score=re.fullmatch(r'\s*(\d+)\s*-\s*(\d+)\s*',str(e.get('score','')))
                cs=e['competitors'];hs=[c for c in cs if c.get('isHome')];aws=[c for c in cs if not c.get('isHome')]
                if len(hs)!=1 or len(aws)!=1 or str(tid) not in {str(c['id']) for c in cs}:raise ValueError('Unverified event orientation')
                if 'friendly' in league.lower() or 'friendlies' in league.lower():continue
                if not score:
                    excluded.append({'provider':'espn','event_id':e['id'],'reason':'non-simple score','event':e});continue
                add({'date':e['date'],'home_team':hs[0]['displayName'],'away_team':aws[0]['displayName'],'home_score':int(score[1]),'away_score':int(score[2]),'competition':league,'data_source':'espn:public-results','source_url':'https://www.espn.com'+e['link'],'archive_url':url,'provider_match_id':e['id'],'home_provider_id':hs[0]['id'],'away_provider_id':aws[0]['id'],'status':'FINISHED','score_basis':'regulation_ft' if detail=='FT' else 'final_score_unverified_regulation','training_eligible':detail=='FT','status_detail':detail,'source_file':str(path.relative_to(ROOT))})
        except Exception as exc:pages.append({'team':team,'season':season,'error':str(exc)})
# Reuse the full raw archives rather than the earlier current-season-only extract.
safe_leagues={'AUS','BEL','BNDL','EPL','ESP','FRA','ITA','ITA2','NED','POR','TUR','UKR'}
for path in (ROOT/'pipeline/data/raw/ucl_today_20261021_form').glob('team_*.raw'):
    tid=path.stem.split('_')[1];url=f'https://terrikon.com/en/football/teams/{tid}/gamesarchive';note_file(path,url)
    tree=html.fromstring(path.read_bytes())
    for tr in tree.xpath('//tr[td[@class="leftteam"]]'):
        def fld(cls):return ' '.join(tr.xpath('./td[@class="'+cls+'"]')[0].text_content().split())
        d,home,away,score,comp=[fld(c) for c in ['date','leftteam','rightteam','score','abr']]
        date=pd.to_datetime(d,format='%d.%m.%Y',utc=True,errors='coerce')
        if pd.isna(date) or not START<=date<CUTOFF or comp=='FRND':continue
        match=re.fullmatch(r'(\d+):(\d+)',score)
        links=tr.xpath('./td[@class="score"]//a/@href');match_url='https://terrikon.com'+links[0] if links else url
        if not match:
            if score and score!='-:-':excluded.append({'provider':'terrikon','date':str(date),'home':home,'away':away,'score':score,'source_url':match_url,'reason':'extra-time/penalties or non-simple score'})
            continue
        add({'date':date,'home_team':home,'away_team':away,'home_score':int(match[1]),'away_score':int(match[2]),'competition':comp,'data_source':'terrikon:senior-archive','source_url':match_url,'archive_url':url,'status':'FINISHED','score_basis':'domestic_league_regulation' if comp in safe_leagues else 'archive_simple_score_unverified_regulation','training_eligible':comp in safe_leagues,'source_file':str(path.relative_to(ROOT))})
# Add complete competition inventories, including cups omitted by ESPN.
tmids={'Como':1047,'Man United':985,'Lille':1082,'Galatasaray':141,'Aston Villa':405,'Viking':239,'Club Brugge':2282,'Lens':826,'Bayern Munich':27,'Arsenal':11,'Inter':46,'Shakhtar Donetsk':660,'Real Madrid':418,'RB Leipzig':23826,'Betis':150,'Feyenoord':234,'Sp Lisbon':336,'LASK Linz':413}
tm_expected=[]
for team,tid in tmids.items():
    for season in range(2022 if team=='Viking' else 2023,2027):
        path=RAW/f'tm_{tid}_{season}.raw';url=f'https://www.transfermarkt.com/club/spielplan/verein/{tid}/saison_id/{season}'
        if not path.exists():continue
        note_file(path,url);tree=html.fromstring(path.read_bytes())
        canonical=tree.xpath('//link[@rel="canonical"]/@href');assert canonical and f'/verein/{tid}' in canonical[0]
        title=tree.xpath('//title/text()')[0].split(' - Schedule')[0]
        assert name(title)==team,('Wrong Transfermarkt team',team,title)
        for tr in tree.xpath('//tr[.//a[contains(@class,"ergebnis-link")]]'):
            links=tr.xpath('.//a[contains(@class,"ergebnis-link")]')
            if len(links)!=1:continue
            texts=[' '.join(td.text_content().split()) for td in tr.xpath('./td')]
            dates=[re.search(r'(\d{2}/\d{2}/\d{4})',s) for s in texts];dates=[m[1] for m in dates if m]
            venues=[s for s in texts if s in ['H','A']]
            opp=tr.xpath('./td[contains(@class,"no-border-links")]//a[contains(@href,"/verein/")]')
            if len(dates)!=1 or len(venues)!=1 or not opp:continue
            opponent=' '.join(opp[0].text_content().split());oppid=re.search(r'/verein/(\d+)',opp[0].get('href'))[1]
            opponent=next((n for n,i in tmids.items() if str(i)==oppid),opponent)
            headline=tr.xpath('ancestor::table[1]/preceding::h2[1]')
            comp=' '.join(headline[0].text_content().split()) if headline else 'unresolved_competition'
            if 'friendly' in comp.lower() or 'all-star' in comp.lower():continue
            score=' '.join(links[0].text_content().split());match=re.match(r'^(\d+):(\d+)',score)
            if not match:continue
            h,a=(team,opponent) if venues[0]=='H' else (opponent,team)
            row={'date':pd.to_datetime(dates[0],format='%d/%m/%Y',utc=True),'home_team':h,'away_team':a,'home_score':int(match[1]),'away_score':int(match[2]),'competition':comp,'data_source':'transfermarkt:public-schedule','source_url':'https://www.transfermarkt.com'+links[0].get('href'),'archive_url':url,'provider_match_id':links[0].get('id'),'status':'FINISHED','score_basis':'regulation_ft' if re.fullmatch(r'\d+:\d+',score) else 'final_score_unverified_regulation','training_eligible':bool(re.fullmatch(r'\d+:\d+',score)),'status_detail':score,'source_file':str(path.relative_to(ROOT))}
            if 'on pens' in score.lower():
                row.update(penalty_home_score=row['home_score'],penalty_away_score=row['away_score'],home_score=None,away_score=None,score_basis='shootout_only_regulation_missing',training_eligible=False)
            before=len(rows);add(row)
            if len(rows)>before:tm_expected.append(rows[-1])
# Club official results supplement Norway's current cup, including Madla.
path=RAW/'viking_official.raw';tree=html.fromstring(path.read_bytes());note_file(path,'https://www.vikingfotball.no/resultater')
for tr in tree.xpath('//tr[contains(@class,"schedule__match--played")]'):
    def cell(suffix):
        found=tr.xpath('./td[contains(@class,"schedule__match__item--'+suffix+'")]');return ' '.join(found[0].text_content().split()) if found else ''
    teams=cell('teams');m=re.search(r'^[SUT]\s+(.+?)\s+-\s+(.+?)\s+\((\d+)-(\d+)\)',teams);d=re.search(r'(\d{2}\.\d{2}\.\d{4})',cell('date'))
    if not m or not d:continue
    league=tr.xpath('./td[contains(@class,"--league")]//img/@alt');comp=league[0] if league else cell('league')
    if 'trenings' in comp.lower() or 'friendly' in comp.lower():continue
    link=re.search(r"'(https[^']+)'",tr.get('onclick',''));url=link[1] if link else 'https://www.vikingfotball.no/resultater'
    add({'date':pd.to_datetime(d[1],format='%d.%m.%Y',utc=True),'home_team':m[1],'away_team':m[2],'home_score':int(m[3]),'away_score':int(m[4]),'competition':comp,'data_source':'viking:official-results','source_url':url,'status':'FINISHED','score_basis':'official_final_score','training_eligible':comp=='Eliteserien','source_file':str(path.relative_to(ROOT))})
# Norway's cup archive independently covers calendar years and the transition season.
for cupyear in range(2022,2027):
    path=RAW/f'norway_cup_{cupyear}.raw';url=f'https://www.rsssf.no/{cupyear}/Cup.html';note_file(path,url)
    text=html.fromstring(path.read_bytes()).text_content();current=None;lastmonth=0;actualyear=cupyear
    for line in text.splitlines():
        d=re.match(r'^\s*(\d{1,2})/(\d{1,2}):\s*(.*)',line)
        if d:
            day,month=int(d[1]),int(d[2])
            if cupyear==2026:actualyear=2025 if month>=8 else 2026
            elif cupyear==2022 and lastmonth and month<lastmonth:actualyear=2023
            lastmonth=month;current=pd.Timestamp(year=actualyear,month=month,day=day,tz='UTC');line=d[3]
        if current is None:continue
        m=re.fullmatch(r'\s*(.+?)\s+[-–]\s+(.+?)\s+(\d+)-(\d+)(.*?)\s*',line)
        if not m or 'Viking' not in [m[1],m[2]]:continue
        extra=m[5].strip();eligible=not extra
        add({'date':current,'home_team':m[1],'away_team':m[2],'home_score':int(m[3]),'away_score':int(m[4]),'competition':'Norwegian Cup','data_source':'rsssf:Norway-cup','source_url':url,'status':'FINISHED','score_basis':'regulation_ft' if eligible else 'final_score_unverified_regulation','training_eligible':eligible,'status_detail':extra or 'FT','source_file':str(path.relative_to(ROOT))})
# Existing vetted league data supplies baseline and independent score evidence.
dataset=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020/dataset.parquet'
metadata=json.loads((dataset.parent/'metrics_v2.1.0.json').read_text())
assert hashlib.sha256(dataset.read_bytes()).hexdigest()==metadata['dataset_sha256']
note_file(dataset,'local-reviewed-candidate')
df=pd.read_parquet(dataset);baseline=[]
for row in df.to_dict('records'):
    if pd.isna(row.get('home_score')) or pd.isna(row.get('away_score')):continue
    row={k:row.get(k) for k in ['date','home_team','away_team','home_score','away_score','competition','data_source','source_url','provider_match_id']}
    row.update(training_eligible=True,score_basis='reviewed_candidate_regulation',source_file=str(dataset.relative_to(ROOT)),status='FINISHED')
    before=len(rows);add(row)
    if len(rows)>before:baseline.append(rows[-1])
official=ROOT/'pipeline/data/raw/team_form/ucl_20261021/history.csv';note_file(official,'https://api.football-data.org/v4/competitions/CL/matches')
for row in pd.read_csv(official).to_dict('records'):
    row={k:row.get(k) for k in ['date','home_team','away_team','home_score','away_score','competition','data_source','provider_match_id']};row.update(training_eligible=True,score_basis='provider_regulation',source_file=str(official.relative_to(ROOT)),status='FINISHED');add(row)
# New complete Belgian/Austrian/Serie B league CSVs (where publicly available).
for path in RAW.glob('fd_*.raw'):
    try:
        df=pd.read_csv(path);assert {'Date','HomeTeam','AwayTeam','FTHG','FTAG'}.issubset(df)
        _,season,league=path.stem.split('_');url=f'https://www.football-data.co.uk/mmz4281/{season}/{league}.csv';note_file(path,url)
        for e in df.to_dict('records'):
            if pd.isna(e['FTHG']) or pd.isna(e['FTAG']):continue
            add({'date':pd.to_datetime(e['Date'],dayfirst=True,utc=True),'home_team':e['HomeTeam'],'away_team':e['AwayTeam'],'home_score':e['FTHG'],'away_score':e['FTAG'],'competition':league,'source_url':url,'data_source':'football-data.co.uk:verified-csv','status':'FINISHED','score_basis':'domestic_league_regulation','training_eligible':True,'source_file':str(path.relative_to(ROOT))})
    except Exception as exc:excluded.append({'source_file':str(path),'reason':str(exc)})
def key(r):
    anchor=r['target_teams'][0]
    return (r['date'][:10],anchor,anchor==r['home_team'])
clusters=collections.defaultdict(list)
for row in rows:clusters[key(row)].append(row)
conflicts=[];accepted=[]
for k,items in clusters.items():
    # This fixture was abandoned at 1–0 and awarded 3–0; neither is a 90-minute result.
    if k[:2] in {('2025-02-09','Galatasaray'),('2024-04-07','Galatasaray')}:
        for item in items:item['training_eligible']=False
        chosen=next((i for i in items if i['home_score']==3 and i['away_score']==0),items[0]).copy()
        adjudication='https://www.galatasaray.org/haber/futbol/galatasaray-adana-demirspor-maci-tatil-edildi/57198' if k[0]=='2025-02-09' else 'https://www.galatasaray.org/haber/futbol/tff-super-kupa/maca-dogru-galatasaray-fenerbahce/59252'
        chosen.update(training_eligible=False,status='AWARDED',score_basis='awarded_not_regulation',adjudication_source=adjudication,evidence=items)
        accepted.append(chosen);continue
    eligible=[r for r in items if r['training_eligible']]
    # Regulation and extra-time final scores are different quantities, not conflicting labels.
    scores={(r['home_score'],r['away_score']) for r in eligible}
    opponents={r['away_team'] if k[2] else r['home_team'] for r in items}
    if len(scores)>1:
        conflicts.append({'key':k,'reason':'regulation_score_conflict','rows':items});continue
    priority={'espn:public-results':6,'viking:official-results':5,'transfermarkt:public-schedule':5,'football-data.org:team-form':4,'football-data.co.uk:verified-csv':3,'terrikon:senior-archive':2}
    pool=eligible or items
    best=max(pool,key=lambda r:priority.get(r['data_source'],1)).copy()
    best['evidence_count']=len(items);best['evidence_sources']=sorted({r['data_source'] for r in items});best['opponent_aliases']=sorted(opponents)
    best['evidence']=[{k:v for k,v in r.items() if k not in ['target_teams','result']} for r in items]
    accepted.append(best)
accepted.sort(key=lambda r:(r['date'],r['home_team']))
training=[r for r in accepted if r['training_eligible']]
def clean(row):return {k:v for k,v in row.items() if k not in ['evidence','target_teams','opponent_aliases','evidence_sources']}
pd.DataFrame([clean(r) for r in training]).to_csv(RAW/'regulation_history.csv',index=False)
pd.DataFrame([clean(r) for r in accepted]).to_csv(RAW/'all_results.csv',index=False)
(RAW/'teams').mkdir(exist_ok=True)
for team in TEAMS:
    pd.DataFrame([clean(r) for r in accepted if team in r['target_teams']]).to_csv(RAW/'teams'/(team_key(team).replace(' ','_')+'.csv'),index=False)
(RAW/'all_results.json').write_text(json.dumps(accepted,indent=2,default=str),encoding='utf-8')
(RAW/'conflicts.json').write_text(json.dumps(conflicts,indent=2,default=str),encoding='utf-8')
(RAW/'excluded.json').write_text(json.dumps(excluded,indent=2,default=str),encoding='utf-8')
coverage=[]
for team in TEAMS:
    teamrows=[r for r in accepted if team in r['target_teams']];base=[r for r in baseline if team in r['target_teams']]
    basekeys={key(r) for r in base};byseason=collections.Counter()
    for r in teamrows:
        d=pd.Timestamp(r['date']);y=d.year if team=='Viking' else d.year-(d.month<7);label=str(y) if team=='Viking' else f'{y}/{str(y+1)[-2:]}'
        byseason[label]+=1
    recent=teamrows[-5:];sequence=''.join('?' if r['home_score'] is None else 'D' if r['home_score']==r['away_score'] else 'W' if (r['home_score']>r['away_score'])==(r['home_team']==team) else 'L' for r in recent)
    coverage.append({'team':team,'baseline_results':len(basekeys),'results':len(teamrows),'new_results':sum(key(r) not in basekeys for r in teamrows),'training_results':sum(r['training_eligible'] for r in teamrows),'season_counts':dict(sorted(byseason.items())),'competitions':dict(collections.Counter(r['competition'] for r in teamrows)),'earliest':teamrows[0]['date'] if teamrows else None,'latest':teamrows[-1]['date'] if teamrows else None,'last_five':sequence,'last_five_matches':[{k:r.get(k) for k in ['date','home_team','away_team','home_score','away_score','competition','source_url','training_eligible']} for r in recent]})
report={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'2023/24, 2024/25, 2025/26 and current 2026/27; Viking calendar seasons 2023–2026','cutoff':str(CUTOFF),'raw_result_observations':len(rows),'unique_results':len(accepted),'new_unique_fixtures':len({key(x) for x in accepted}-{key(x) for x in baseline}),'training_results':len(training),'conflicted_fixtures':len(conflicts),'unresolved_regulation':len(accepted)-len(training),'pages':pages,'coverage':coverage,'source_files':source_files,'database_writes':False,'model_changed':False,'coverage_complete':False,'tm_inventory_fixtures':len({key(x) for x in tm_expected}),'tm_inventory_missing':sorted({key(x) for x in tm_expected}-{key(x) for x in accepted})}
(RAW/'coverage.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['pages','coverage','source_files']}))
for row in coverage:print(json.dumps({k:v for k,v in row.items() if k not in ['last_five_matches','competitions']}))
print('PAGE_ERRORS',json.dumps([p for p in pages if 'error' in p]))
print('CONFLICTS',json.dumps([{k:v for k,v in c.items() if k!='rows'} for c in conflicts][:15]))
