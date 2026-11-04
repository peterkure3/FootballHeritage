"""Read-only, reproducible review of today's public regulation-time 1X2 markets."""
import sys,json,hashlib,importlib.util
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd,joblib
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from models.features import build_live_features,FeatureState,FEATURE_NAMES
from models.data import team_key,canonical_matches
spec=importlib.util.spec_from_file_location('repair',OUT/'recalibrate-ucl-20261020.py');repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
groups='''Como|Como 1907|Como Calcio
Man United|Manchester United|Manchester United FC|Manchester Utd|Man Utd
Lille|Lille OSC
Galatasaray|Galatasaray SK|Galatasaray Istanbul|Galatasaray AŞ
Aston Villa|Aston Villa FC
Viking|Viking FK
Club Brugge|Club Brugge KV|Brugge
Lens|RC Lens|Racing Club de Lens
Bayern Munich|Bayern|FC Bayern München|Bayern München|Bayern Munchen
Arsenal|Arsenal FC
Inter|Inter Milan|Inter Milano|Internazionale Milano|FC Internazionale Milano
Shakhtar Donetsk|Shakhtar|FK Shakhtar Donetsk|FC Shakhtar Donetsk
Real Madrid|Real|Real Madrid CF
RB Leipzig|Leipzig|RasenBallsport Leipzig
Betis|Real Betis|Real Betis Balompié|Real Betis Seville
Feyenoord|Feyenoord Rotterdam
Sp Lisbon|Sporting CP|Sporting Lisbon|Sporting Lisboa|Sporting Clube de Portugal
LASK Linz|LASK'''
groups+='''
Nice|OGC Nice
Troyes|ES Troyes AC
Telstar|Telstar 1963
Fulham|Fulham FC
Tottenham|Tottenham Hotspur FC|Tottenham Hotspur
Brentford|Brentford FC
Newcastle|Newcastle United FC|Newcastle United
Brighton|Brighton & Hove Albion FC
Sevilla|Sevilla FC
Elversberg|SV 07 Elversberg'''
aliases={team_key(v):line.split('|')[0] for line in groups.splitlines() for v in line.split('|')}
def name(s):return aliases.get(team_key(s),repair.reviewed_name(s))
def fix(df):
    df=df.copy()
    for side in ['home','away']:
        df[side+'_team']=df[side+'_team'].map(name)
        df[side+'_key']=df[side+'_team'].map(team_key)
    df['date']=pd.to_datetime(df['date'],utc=True)
    df['fixture_day']=df['date'].dt.floor('D')
    return df
base=ROOT/'pipeline/data/raw'
forms=json.loads((base/'team_form/ucl_20261021/form.json').read_text(encoding='utf-8'))
archives=json.loads((base/'ucl_today_20261021_form/archives.json').read_text(encoding='utf-8'))
directory=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020'
metrics=json.loads((directory/'metrics_v2.1.0.json').read_text())
for file,key in [('model_v2.1.0.pkl','model_sha256'),('dataset.parquet','dataset_sha256')]:
    assert hashlib.sha256((directory/file).read_bytes()).hexdigest()==metrics[key]
history=fix(pd.read_parquet(directory/'dataset.parquet'))
official=fix(pd.read_csv(base/'team_form/ucl_20261021/history.csv'))
# Only dated senior domestic-league archive scores enter supplementary history.
safe=[r for r in archives['results'] if r['competition'] in {'AUS','BEL','BNDL','EPL','ESP','FRA','ITA','NED','POR','TUR','UKR'}]
extra=fix(pd.DataFrame(safe));extra['result']=np.where(extra.home_score>extra.away_score,'home_win',np.where(extra.home_score<extra.away_score,'away_win','draw'))
history=pd.concat([extra,history,official],ignore_index=True)
keys=['fixture_day','home_key','away_key']
conflicts=history.groupby(keys)[['home_score','away_score']].nunique().max(axis=1)
assert not (conflicts>1).any(),'Score conflict requires review'
history=history.drop_duplicates(keys,keep='last').sort_values('date')
assert (history.date<pd.Timestamp('2026-10-21',tz='UTC')).all()
model=joblib.load(directory/'model_v2.1.0.pkl');classes=metrics['classes']
state=FeatureState()
for match in canonical_matches([history]).to_dict('records'):state.update(match)
quotes=[json.loads(x) for x in (base/'ucl_today_20261021_recheck/odds_snapshots_complete.jsonl').read_text(encoding='utf-8').splitlines()]
quotes=[q for q in quotes if q['bookmaker'] not in {'bovada','bookmaker'}]
results=[]
for f in forms['fixtures']:
    home,away=name(f['home_team']),name(f['away_team']);kick=pd.Timestamp(f['kickoff']);qs=[];rejected=[]
    for q in quotes:
        pair=(name(q['home_team']),name(q['away_team']))
        if set(pair)!={home,away} or abs((pd.Timestamp(q['commence_time'])-kick).total_seconds())>60:continue
        if q['sport']!='football' or q['market']!='h2h' or q['period']!='FULL_TIME_90_MIN' or q['settlement_rule']!='REGULATION_TIME' or q['is_live']:continue
        prices={x['selection']:x['odds_decimal'] for x in q['outcomes']}
        if set(prices)!={'HOME','DRAW','AWAY'} or min(prices.values())<=1:continue
        oriented=dict(zip(['home_win','draw','away_win'],[prices['HOME'],prices['DRAW'],prices['AWAY']] if pair[0]==home else [prices['AWAY'],prices['DRAW'],prices['HOME']]))
        item={'bookmaker':q['bookmaker'],'prices':oriented,'observed_at':q['observed_at'],'source_url':q['source_url'],'status':q['market_status'],'reoriented':pair[0]!=home}
        if q['market_status']!='OPEN' or any(x['status']!='OPEN' for x in q['outcomes']):rejected.append(item);continue
        qs.append(item)
    assert qs,home
    mean={c:float(np.mean([q['prices'][c] for q in qs])) for c in classes}
    consensus=np.mean([[1/q['prices'][c]/sum(1/v for v in q['prices'].values()) for c in classes] for q in qs],axis=0)
    X=pd.DataFrame([state.vector(home,away,mean)],columns=FEATURE_NAMES)
    with threadpool_limits(limits=2):p=model.predict_proba(X)[0]
    assert np.isfinite(p).all() and min(p)>0 and max(p)<1 and abs(p.sum()-1)<1e-9
    best={c:max(qs,key=lambda q:q['prices'][c]) for c in classes}
    inv=sum(1/best[c]['prices'][c] for c in classes)
    form={}
    for team in [home,away]:
        recent=history[(history.home_team==team)|(history.away_team==team)].tail(5)
        rows=[]
        for _,r in recent.iterrows():
            ishome=r.home_team==team;gf=int(r.home_score if ishome else r.away_score);ga=int(r.away_score if ishome else r.home_score)
            rows.append({'date':str(r.date),'opponent':r.away_team if ishome else r.home_team,'venue':'H' if ishome else 'A','gf':gf,'ga':ga,'result':'W' if gf>ga else 'L' if gf<ga else 'D','competition':r.get('competition'),'source':r.get('data_source')})
        form[team]={'sequence':''.join(r['result'] for r in rows),'gf':sum(r['gf'] for r in rows),'ga':sum(r['ga'] for r in rows),'matches':rows,'history_count':int(((history.home_team==team)|(history.away_team==team)).sum())}
    results.append({'home':home,'away':away,'kickoff':str(kick),'form':form,'quotes':qs,'rejected_unknown_status':rejected,'consensus':dict(zip(classes,map(float,consensus))),'probabilities':dict(zip(classes,map(float,p))),'best':{c:{'bookmaker':best[c]['bookmaker'],'odds':best[c]['prices'][c],'model_ev':float(p[i]*best[c]['prices'][c]-1)} for i,c in enumerate(classes)},'reciprocal_sum':inv,'nominal_arb_roi':1/inv-1,'feature_vector':X.iloc[0].to_dict()})
assert len(results)==9
report={'generated_at':datetime.now(timezone.utc).isoformat(),'model_sha256':metrics['model_sha256'],'model_market_edge_established':False,'history_rows':len(history),'form_order':'oldest_to_newest','form_scope':'available domestic leagues plus verified regulation European results; not exhaustive all competitions','settlement':'90 minutes plus stoppage time','matches':results,'sources_attempted':len(json.loads((base/'ucl_today_20261021_all_public/source_report.json').read_text())['direct_sources'])}
(OUT/'ucl-analysis-20261021.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='matches'}))
for r in results:
    print(json.dumps({k:v for k,v in r.items() if k not in ['feature_vector','quotes','rejected_unknown_status','form']}|{'form':{t:{k:v for k,v in f.items() if k!='matches'} for t,f in r['form'].items()},'books':[q['bookmaker'] for q in r['quotes']]}))
