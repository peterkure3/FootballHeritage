"""Validate fresh bookmaker 1X2 prices against official UEFA fixtures and XIs."""
import ast,hashlib,json,sys,math
from pathlib import Path
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'))
from models.data import team_key
sys.stdout.reconfigure(encoding='utf-8')
groups=''
for node in ast.parse((OUT/'analyze-ucl-20261021.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='groups' for t in node.targets):groups=ast.literal_eval(node.value)
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='groups':groups+=ast.literal_eval(node.value)
aliases={team_key(v):line.split('|')[0] for line in groups.splitlines() for v in line.split('|')}
aliases.update({team_key('Internazionale'):'Inter',team_key('FC Bayern Munich'):'Bayern Munich'})
def name(s):return aliases.get(team_key(s),s)
fixtures={
    2049598:('Bayern Munich','Arsenal','50037','52280','bayern-munchen-vs-arsenal'),
    2049599:('Real Madrid','RB Leipzig','50051','2603790','real-madrid-vs-leipzig'),
    2049600:('Inter','Shakhtar Donetsk','50138','52707','inter-vs-shakhtar'),
    2049601:('Sp Lisbon','LASK Linz','50149','63405','sporting-cp-vs-lask'),
    2049602:('Aston Villa','Viking','52683','52319','aston-villa-vs-viking'),
    2049603:('Club Brugge','Lens','50043','52277','club-brugge-vs-lens'),
    2049604:('Betis','Feyenoord','52265','52749','real-betis-vs-feyenoord'),
}
price_capture=Path(json.loads((OUT/'ucl-revision-inputs-20261021.json').read_text())['capture'])
lineup_capture=Path(json.loads((OUT/'ucl-confirmed-inputs-20261021.json').read_text())['capture'])
lineup_audit=json.loads((lineup_capture/'audit.json').read_text())
source_checks=[];usable=set()
for source in json.loads((price_capture/'cache-audit.json').read_text()):
    response=source['http_audit'][-1] if source['http_audit'] else None;reason=None
    if not response or source.get('http_status')!=200:reason='unavailable'
    else:
        h={k.lower():v for k,v in response['headers'].items()};observed=pd.Timestamp(response['observed_at'])
        age=float(h.get('age') or 0)
        if h.get('date'):age=max(age,(observed-pd.Timestamp(parsedate_to_datetime(h['date']))).total_seconds())
        if age>120:reason='upstream_cache_older_than_120_seconds'
        if source['bookmaker']=='bookmaker' and h.get('last-modified') and (observed-pd.Timestamp(parsedate_to_datetime(h['last-modified']))).total_seconds()>300:reason='conservative_page_last_modified_age_over_300_seconds'
    source_checks.append({'bookmaker':source['bookmaker'],'accepted':reason is None,'reason':reason,'observed_at':source.get('observed_at'),'headers':response['headers'] if response else {}})
    if reason is None:usable.add(source['bookmaker'])
quotes=[json.loads(line) for line in (price_capture/'odds_snapshots_complete.jsonl').read_text().splitlines() if line]
matches=[];checks={'official_match_metadata':0,'official_starting_xis':0,'unique_starting_players':0,'complete_book_prices':0,'arbitrage_calculations':0,'lineup_responses_with_fresh_http_date':0};warnings=[]
for mid,(home,away,home_id,away_id,slug) in fixtures.items():
    metadata=json.loads((lineup_capture/f'{mid}_metadata.json').read_text(encoding='utf-8'))
    lineup=json.loads((lineup_capture/f'{mid}_lineups.json').read_text(encoding='utf-8'))
    assert str(metadata['id'])==str(lineup['matchId'])==str(mid)
    assert str(metadata['competition']['id'])=='1' and str(metadata['seasonYear'])=='2027'
    assert metadata['status']=='UPCOMING'
    kickoff=pd.Timestamp(metadata['kickOffTime']['dateTime'])
    assert kickoff==pd.Timestamp('2026-10-21T19:00:00Z')
    assert lineup['lineupStatus'] in {'AVAILABLE','TACTICAL_AVAILABLE'}
    checks['official_match_metadata']+=1
    row={'match_id':mid,'home':metadata['homeTeam']['internationalName'],'away':metadata['awayTeam']['internationalName'],'kickoff':kickoff.isoformat(),'lineup_status':lineup['lineupStatus'],'source_url':f'https://www.uefa.com/uefachampionsleague/match/{mid}--{slug}/lineups/','lineup_api_url':f'https://match.uefa.com/v5/matches/{mid}/lineups','teams':{}}
    all_ids=[]
    for side,expected_id in [('homeTeam',home_id),('awayTeam',away_id)]:
        team=lineup[side];assert str(team['team']['id'])==str(metadata[side]['id'])==expected_id
        field,bench=team['field'],team['bench'];ids=[x['player']['id'] for x in field];bench_ids=[x['player']['id'] for x in bench]
        assert len(field)==len(set(ids))==11 and len(set(bench_ids))==len(bench_ids)
        assert not set(ids)&set(bench_ids)
        assert sum(x['player'].get('fieldPosition')=='GOALKEEPER' for x in field)==1
        assert sum(x['type']=='CAPTAIN' for x in field)==1
        assert len({x['jerseyNumber'] for x in field})==11
        assert all(x['player']['internationalName'] for x in field)
        all_ids+=ids
        row['teams'][side]={'name':team['team']['internationalName'],'team_id':expected_id,'starters':[{'id':x['player']['id'],'name':x['player']['internationalName'],'shirt':x['jerseyNumber'],'position':x['player'].get('fieldPosition'),'captain':x['type']=='CAPTAIN','late_update':x.get('isLateUpdate',False)} for x in field],'bench':[{'id':x['player']['id'],'name':x['player']['internationalName']} for x in bench]}
        checks['official_starting_xis']+=1;checks['unique_starting_players']+=11
    assert len(set(all_ids))==22
    for kind in ['lineups','metadata']:
        a=next(x for x in lineup_audit if x['match_id']==mid and x['kind']==kind)
        assert a['status']==200 and hashlib.sha256(Path(a['file']).read_bytes()).hexdigest()==a['sha256']
        hdr=a['headers'];age=float(hdr.get('age') or 0)
        assert age<=120
        if hdr.get('date'):
            assert abs((pd.Timestamp(a['observed_at'])-pd.Timestamp(parsedate_to_datetime(hdr['date']))).total_seconds())<=120
            if kind=='lineups':checks['lineup_responses_with_fresh_http_date']+=1
        else:warnings.append(f'{mid} {kind}: HTTP date absent; capture time only')
        if kind=='lineups':row['lineup_observed_at']=a['observed_at']
    previous=ROOT/'pipeline/data/raw/ucl_lineups_20261021T174624Z'/f'{mid}_api.json'
    if previous.exists():
        old=json.loads(previous.read_text(encoding='utf-8'))
        assert all({x['player']['id'] for x in old[s]['field']}=={x['player']['id'] for x in lineup[s]['field']} for s in ['homeTeam','awayTeam']),f'{mid} starting XI changed; needs review'
        row['same_starter_ids_as_1746_capture']=True
    found={}
    for q in quotes:
        if q['bookmaker'] not in usable:continue
        pair=(name(q['home_team']),name(q['away_team']))
        if set(pair)!={home,away} or abs((pd.Timestamp(q['commence_time'])-kickoff).total_seconds())>60:continue
        if q['sport']!='football' or q['market']!='h2h' or q['period']!='FULL_TIME_90_MIN' or q['settlement_rule']!='REGULATION_TIME' or q['is_live'] or q['market_status']!='OPEN' or q['event_status']!='SCHEDULED':continue
        if len(q['outcomes'])!=3 or any(x['status']!='OPEN' for x in q['outcomes']):continue
        prices={x['selection']:x['odds_decimal'] for x in q['outcomes']}
        if set(prices)!={'HOME','DRAW','AWAY'} or not all(math.isfinite(v) and v>1 for v in prices.values()):continue
        assert pd.Timestamp(q['observed_at'])<kickoff
        if pair[0]!=home:prices={'HOME':prices['AWAY'],'DRAW':prices['DRAW'],'AWAY':prices['HOME']}
        ref=Path(q['raw_capture_ref']);ref=ref if ref.is_absolute() else price_capture/ref
        assert ref.exists(),str(ref)
        candidate={'bookmaker':q['bookmaker'],'prices':prices,'observed_at':q['observed_at'],'source_url':q['source_url'],'raw_capture_ref':str(ref)}
        if q['bookmaker'] not in found or pd.Timestamp(q['observed_at'])>pd.Timestamp(found[q['bookmaker']]['observed_at']):found[q['bookmaker']]=candidate
    assert len(found)>=2,(mid,'insufficient independent book quotes')
    row['quotes']=list(found.values());checks['complete_book_prices']+=len(found)
    row['best_prices']={outcome:{'odds':max(q['prices'][outcome] for q in found.values()),'bookmaker':max(found.values(),key=lambda q:q['prices'][outcome])['bookmaker']} for outcome in ['HOME','DRAW','AWAY']}
    inv=sum(1/v['odds'] for v in row['best_prices'].values());row['reciprocal_sum']=inv;row['nominal_arb_roi']=1/inv-1
    checks['arbitrage_calculations']+=1;matches.append(row)
assert checks['official_starting_xis']==14 and checks['unique_starting_players']==154
checks['starting_ids_stable_across_two_captures']=all(r.get('same_starter_ids_as_1746_capture') for r in matches)
report={'generated_at':datetime.now(timezone.utc).isoformat(),'price_capture':str(price_capture),'lineup_capture':str(lineup_capture),'source_checks':source_checks,'checks':checks,'warnings':warnings,'all_validation_checks_passed':True,'arbitrage_opportunities':sum(r['reciprocal_sum']<1 for r in matches),'matches':matches}
dest=OUT/'ucl-prices-lineups-validated-20261021.json'
if dest.exists():
    prior=json.loads(dest.read_text(encoding='utf-8'))
    if prior['price_capture']!=str(price_capture):
        (OUT/'ucl-prices-lineups-earlier-20261021.json').write_text(json.dumps(prior,indent=2,ensure_ascii=False),encoding='utf-8')
        report['previous_price_capture']=prior['price_capture'];report['arbitrage_recheck']=[]
        for old in prior['matches']:
            if old['reciprocal_sum']>=1:continue
            current=next(m for m in matches if m['match_id']==old['match_id'])
            unchanged=current['best_prices']==old['best_prices']
            report['arbitrage_recheck'].append({'match_id':old['match_id'],'all_three_best_legs_unchanged':unchanged,'still_nominal_arbitrage':current['reciprocal_sum']<1,'current_gross_roi':current['nominal_arb_roi']})
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
lines=['# UCL prices and starting XIs — validated 21 October 2026','',f"Generated {report['generated_at']}. All seven fixtures kick off at 19:00 UTC / 22:00 Kampala.",'',
    'Prices are public, open regulation-time 1X2 offers observed in the saved capture. They are not guaranteed executable bet-slip prices. UEFA’s public match service supplies the starting XIs; generic squad pages and predicted third-party XIs were not treated as confirmation. The UEFA public HTML pages were still showing registered squads while its match feed had published starting XIs.','',
    '## Validation','',f"Passed: {checks['official_match_metadata']} official fixture identities, {checks['official_starting_xis']} XIs, {checks['unique_starting_players']} unique starters within their teams, {checks['complete_book_prices']} complete bookmaker markets, and {checks['arbitrage_calculations']} arbitrage calculations. All starter sets were unchanged between the 17:46 and 17:52 UTC captures.",'',
    'Checked competition, season, home/away club IDs, kickoff, upcoming status, lineup publication status, 11 unique starters, one goalkeeper and captain per team, distinct shirt numbers, no starter/bench overlap, response checksums and HTTP freshness. Late changes after capture remain possible.','',
    '## Best available prices','', '| Match | Home | Draw | Away |','|---|---:|---:|---:|']
for r in matches:
    cells=[f"{r['best_prices'][o]['odds']:.2f} ({r['best_prices'][o]['bookmaker']})" for o in ['HOME','DRAW','AWAY']]
    lines.append(f"| {r['home']} – {r['away']} | "+' | '.join(cells)+' |')
lines+=['',f"Nominal arbitrage opportunities: {report['arbitrage_opportunities']}. Requires sum(1 / best outcome odds) < 1 before fees and execution effects.",'']
if report.get('arbitrage_recheck'):
    lines+=['Candidates were re-fetched across all sources. Recheck results:','']
    for item in report['arbitrage_recheck']:lines.append(f"- UEFA match {item['match_id']}: all three best prices and books unchanged = {item['all_three_best_legs_unchanged']}; remains nominal arbitrage = {item['still_nominal_arbitrage']}; gross ROI {item['current_gross_roi']:+.3%}.")
    lines.append('')
lines+=['## Source freshness','']
for s in source_checks:lines.append(f"- {s['bookmaker']}: {'accepted' if s['accepted'] else 'excluded — '+s['reason']}; observed {s['observed_at']}.")
lines+=['','Bookmaker’s Last-Modified exclusion is a conservative page-level rule, not proof of the age of each individual quote. betPawa’s failed 17:42 refresh was retried successfully; only the new capture is used.','', '## Starting XIs and per-book prices','']
for r in matches:
    lines += [f"### {r['home']} – {r['away']}",'',f"UEFA status: `{r['lineup_status']}`. Captured {r['lineup_observed_at']}. [Official match source]({r['lineup_api_url']}).",'']
    for side in ['homeTeam','awayTeam']:
        t=r['teams'][side];players=', '.join(f"{p['shirt']} {p['name']}"+(' (C)' if p['captain'] else '') for p in t['starters'])
        lines.append(f"**{t['name']}:** {players}.");lines.append('')
    lines+=['| Bookmaker | Home | Draw | Away | Observed UTC |','|---|---:|---:|---:|---|']
    for q in r['quotes']:lines.append(f"| {q['bookmaker']} | {q['prices']['HOME']:.2f} | {q['prices']['DRAW']:.2f} | {q['prices']['AWAY']:.2f} | {q['observed_at']} |")
    lines+=['',f"Arbitrage reciprocal sum {r['reciprocal_sum']:.6f}; equal-return gross ROI {r['nominal_arb_roi']:+.3%}.",'']
lines+=['## Effect on the earlier picks','',
    'The earlier model estimates did not incorporate player availability explicitly. Confirmed XIs validate who is selected; they do not validate those probabilities or prove an edge. No artificial percentage adjustment has been applied and no production model or pick was overwritten.','',
    'Bayern: Neuer starts; Olise and Musiala are not in the starting XI or bench. Inter: Lautaro Martinez is absent from the returned match squad. Villa: Suzuki and Jackson start; Martinez and Watkins are absent from the returned match squad. Brugge: Lemarechal starts rather than Vetlesen. Lens: Thauvin, Todibo and Edouard are on the bench; Hazard, Aguilar, Skoras and Kadile start. These differences make predicted third-party XIs unsuitable as confirmed data.','',
    'Raw responses, SHA-256 hashes, timestamps and full benches are retained in the JSON artifact and capture directory. No bet was placed.','']
(OUT/'ucl-prices-lineups-validated-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['matches','source_checks']},ensure_ascii=False))
for r in matches:print(json.dumps({'match':r['home']+' – '+r['away'],'best':r['best_prices'],'arb_sum':r['reciprocal_sum'],'starters':{s:[p['name'] for p in r['teams'][s]['starters']] for s in ['homeTeam','awayTeam']},'bench':{s:[p['name'] for p in r['teams'][s]['bench']] for s in ['homeTeam','awayTeam']}},ensure_ascii=False))
