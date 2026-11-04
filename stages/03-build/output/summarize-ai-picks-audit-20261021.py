import json
from pathlib import Path
OUT=Path(__file__).parent;r=json.loads((OUT/'ai-picks-live-audit-20261021.json').read_text())
for label in ['pipeline_picks_ucl','football_intelligence','intelligence_overview']:
    item=r['http'][label];body=item.get('body',{});print('ENDPOINT',label,'STATUS',item.get('status'))
    print('META',json.dumps({k:v for k,v in body.items() if k not in ['picks','predictions','ai_picks','devigged_odds','ev_bets','player_props','arbitrage','sports']},default=str)[:3500])
    if label=='pipeline_picks_ucl':
        for p in body.get('picks',[]):print('PICK',json.dumps(p,default=str))
    elif label=='football_intelligence':
        print('SECTIONS',{k:len(body.get(k,[])) for k in ['ai_picks','predictions','devigged_odds','ev_bets','player_props','arbitrage']})
        print('AI_PICKS',json.dumps(body.get('ai_picks',[])[:3],default=str)[:1600])
print('SAVED_RUNS',[{k:x.get(k) for k in ['sport','competition','requested_date','model_version','created_at']}|{'picks':len(x.get('results') or [])} for x in r['backend_db'].get('saved_runs',[])[:5]])
for x in r['pipeline_db'].get('today_ucl',[]):print('DBMATCH',json.dumps({k:v for k,v in x.items() if k!='quotes'}|{'books':[q['bookmaker'] for q in x['quotes']]},default=str))
