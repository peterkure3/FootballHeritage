"""Recheck nine fixtures using verified backfill and fresh public prices."""
import ast,sys,json,hashlib,importlib.util,collections
from pathlib import Path
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import numpy as np,pandas as pd,joblib
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from models.data import team_key,canonical_matches
from models.features import FeatureState,FEATURE_NAMES
spec=importlib.util.spec_from_file_location('repair',OUT/'recalibrate-ucl-20261020.py');repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
groups=''
for node in ast.parse((OUT/'analyze-ucl-20261021.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='groups' for t in node.targets):groups=ast.literal_eval(node.value)
    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='groups':groups+=ast.literal_eval(node.value)
aliases={team_key(v):line.split('|')[0] for line in groups.splitlines() for v in line.split('|')};aliases.update({team_key('Internazionale'):'Inter',team_key('LOSC Lille'):'Lille',team_key('FC Bayern Munich'):'Bayern Munich'})
def name(s):return aliases.get(team_key(s),repair.reviewed_name(s))
def fix(df):
    df=df.copy()
    for side in ['home','away']:df[side+'_team']=df[side+'_team'].map(name);df[side+'_key']=df[side+'_team'].map(team_key)
    df['date']=pd.to_datetime(df['date'],utc=True);df['fixture_day']=df.date.dt.floor('D');return df
directory=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020';metrics=json.loads((directory/'metrics_v2.1.0.json').read_text())
assert hashlib.sha256((directory/'model_v2.1.0.pkl').read_bytes()).hexdigest()==metrics['model_sha256']
assert hashlib.sha256((directory/'dataset.parquet').read_bytes()).hexdigest()==metrics['dataset_sha256']
base=fix(pd.read_parquet(directory/'dataset.parquet'))
raw=ROOT/'pipeline/data/raw/ucl_history_20261021';coverage=json.loads((raw/'coverage.json').read_text());evidence=json.loads((raw/'all_results.json').read_text());targets={c['team'] for c in coverage['coverage']}
verification=json.loads((OUT/'ucl-history-verification-20261021.json').read_text())
assert hashlib.sha256((raw/'regulation_history.csv').read_bytes()).hexdigest()==verification['artifacts']['regulation_history.csv']['sha256']
# Use overlapping source records to align opponent spellings to existing model keys.
counts=collections.Counter(list(base.home_team)+list(base.away_team));proposals=collections.defaultdict(set)
for match in evidence:
    for side in ['home','away']:
        variants={name(e[side+'_team']) for e in match.get('evidence',[]) if e.get(side+'_team')};variants.add(name(match[side+'_team']))
        if variants & targets:preferred=next(iter(variants & targets))
        else:preferred=max(variants,key=lambda n:(counts[n],n))
        if counts[preferred] or preferred in targets:
            for variant in variants:proposals[team_key(variant)].add(preferred)
opponent_aliases={k:next(iter(v)) for k,v in proposals.items() if len(v)==1 and k not in {team_key(t) for t in targets}}
aliases.update(opponent_aliases);base=fix(base)
oldscope=((base.home_team.isin(targets)|base.away_team.isin(targets))&base.date.ge(pd.Timestamp('2023-07-01',tz='UTC')))|((base.home_team.eq('Viking')|base.away_team.eq('Viking'))&base.date.ge(pd.Timestamp('2023-01-01',tz='UTC')))
history=pd.concat([base[~oldscope],fix(pd.read_csv(raw/'regulation_history.csv'))],ignore_index=True)
official=fix(pd.read_csv(ROOT/'pipeline/data/raw/team_form/ucl_20261021/history.csv'))
official=official[~(official.home_team.isin(targets)|official.away_team.isin(targets))]
history=pd.concat([history,official],ignore_index=True)
key=['fixture_day','home_key','away_key'];conflict=history.groupby(key)[['home_score','away_score']].nunique().max(axis=1)
assert not (conflict>1).any(),'Unresolved history conflict'
history=history.drop_duplicates(key,keep='last').sort_values('date');assert history.date.lt(pd.Timestamp('2026-10-21',tz='UTC')).all()
state=FeatureState()
for row in canonical_matches([history]).to_dict('records'):state.update(row)
model=joblib.load(directory/'model_v2.1.0.pkl');classes=metrics['classes']
pointer=json.loads((OUT/'ucl-revision-inputs-20261021.json').read_text());capture=Path(pointer['capture']);audit=json.loads((capture/'cache-audit.json').read_text());usable={};cache=[]
for source in audit:
    a=source['http_audit'][-1] if source['http_audit'] else None;reason=None
    if not a or source.get('http_status')!=200:reason='source_unavailable'
    else:
        hdr=a['headers'];observed=pd.Timestamp(a['observed_at']);age=float(hdr.get('Age') or 0)
        if hdr.get('Date'):age=max(age,(observed-pd.Timestamp(parsedate_to_datetime(hdr['Date']))).total_seconds())
        if age>120:reason='upstream_cache_older_than_120s'
        if source['bookmaker']=='bookmaker' and hdr.get('Last-Modified') and (observed-pd.Timestamp(parsedate_to_datetime(hdr['Last-Modified']))).total_seconds()>300:reason='page_price_timestamp_older_than_300s'
    cache.append({'bookmaker':source['bookmaker'],'accepted':reason is None,'reason':reason,'headers':a['headers'] if a else {}})
    if reason is None:usable[source['bookmaker']]=source
quotes=[json.loads(x) for x in (capture/'odds_snapshots_complete.jsonl').read_text().splitlines() if x]
previous=json.loads((OUT/'ucl-analysis-20261021.json').read_text());results=[]
odds_features=FEATURE_NAMES[:11]+['odds_missing']
for old in previous['matches']:
    home,away=old['home'],old['away'];kick=pd.Timestamp(old['kickoff']);qs=[]
    for q in quotes:
        if q['bookmaker'] not in usable:continue
        pair=(name(q['home_team']),name(q['away_team']))
        if set(pair)!={home,away} or abs((pd.Timestamp(q['commence_time'])-kick).total_seconds())>60:continue
        if q['sport']!='football' or q['market']!='h2h' or q['period']!='FULL_TIME_90_MIN' or q['settlement_rule']!='REGULATION_TIME' or q['is_live'] or q['market_status']!='OPEN':continue
        if any(x['status']!='OPEN' for x in q['outcomes']):continue
        prices={x['selection']:x['odds_decimal'] for x in q['outcomes']}
        if set(prices)!={'HOME','DRAW','AWAY'} or not all(np.isfinite(v) and v>1 for v in prices.values()):continue
        values=[prices['HOME'],prices['DRAW'],prices['AWAY']] if pair[0]==home else [prices['AWAY'],prices['DRAW'],prices['HOME']]
        qs.append({'bookmaker':q['bookmaker'],'prices':dict(zip(['home_win','draw','away_win'],values)),'observed_at':q['observed_at'],'source_url':q['source_url']})
    assert qs,(home,'no current open odds')
    odds={c:float(np.mean([q['prices'][c] for q in qs])) for c in classes};features=state.vector(home,away,odds);oldfeatures=old['feature_vector'].copy()
    for feature in odds_features:oldfeatures[feature]=features[feature]
    X=pd.DataFrame([features,oldfeatures],columns=FEATURE_NAMES)
    with threadpool_limits(limits=2):probs=model.predict_proba(X)
    assert np.isfinite(probs).all() and (probs>0).all() and (probs<1).all() and np.allclose(probs.sum(axis=1),1)
    p=probs[0];consensus=np.mean([[1/q['prices'][c]/sum(1/v for v in q['prices'].values()) for c in classes] for q in qs],axis=0)
    best={c:max(qs,key=lambda q:q['prices'][c]) for c in classes};inv=sum(1/best[c]['prices'][c] for c in classes)
    results.append({'home':home,'away':away,'kickoff':old['kickoff'],'quotes':qs,'probabilities':dict(zip(classes,map(float,p))),'old_history_fresh_prices_probabilities':dict(zip(classes,map(float,probs[1]))),'previous_probabilities':old['probabilities'],'consensus':dict(zip(classes,map(float,consensus))),'best':{c:{'odds':best[c]['prices'][c],'bookmaker':best[c]['bookmaker'],'ev':float(p[i]*best[c]['prices'][c]-1),'fair_odds':float(1/p[i])} for i,c in enumerate(classes)},'reciprocal_sum':inv,'nominal_arb_roi':1/inv-1,'history_sensitivity_max_pp':float(np.max(abs(p-probs[1]))*100),'form':{t:next(c for c in coverage['coverage'] if c['team']==t) for t in [home,away]},'features':features})
report={'generated_at':datetime.now(timezone.utc).isoformat(),'capture':str(capture),'price_observed_at':sorted({q['observed_at'] for r in results for q in r['quotes']}),'cache_validation':cache,'model_sha256':metrics['model_sha256'],'model_retrained':False,'history_rows':len(history),'new_history_regulation_rows':coverage['training_results'],'withheld_history_records':coverage['unresolved_regulation'],'opponent_aliases_from_overlaps':opponent_aliases,'ambiguous_aliases_rejected':{k:sorted(v) for k,v in proposals.items() if len(v)>1},'model_market_edge_proven':False,'matches':results}
(OUT/'ucl-picks-rechecked-20261021.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['matches','opponent_aliases_from_overlaps','ambiguous_aliases_rejected']}))
for r in results:print(json.dumps({k:v for k,v in r.items() if k not in ['quotes','features','form']}|{'form':{t:c['last_five'] for t,c in r['form'].items()}}))
