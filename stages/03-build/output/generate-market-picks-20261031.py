"""Today's candidate previews using existing quote gates and causal features."""
import hashlib
import json
from pathlib import Path
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
import joblib
import numpy as np
import pandas as pd
from models.features import FeatureState, FEATURE_NAMES
from models.football_identity import football_history_key, football_identity_key
from models.import_sportsbook_odds import normalize_snapshots
from models.training_resources import training_threads
from scripts.record_edge_trial import price_analysis
from scripts.sync_bookmaker_grid import capture_cache_rejections

capture = ROOT / 'stages/01-discovery/output/markets-20261031-session'
bundle = ROOT / 'pipeline/models/model_store/candidates/20261031T072113663597Z'
out = ROOT / 'stages/03-build/output/today-picks-20261031-reviewed'
out.mkdir(exist_ok=False)
now = pd.Timestamp.now(tz='UTC')
day = now.tz_convert('Africa/Kampala').date()
manifest = json.loads((bundle / 'metrics_v2.1.0.json').read_text())
assert hashlib.sha256((bundle/'dataset.parquet').read_bytes()).hexdigest() == manifest['dataset_sha256']
assert pd.Timestamp(manifest['trained_at']) < now
history = pd.read_parquet(bundle/'dataset.parquet')
history = history[history.date.lt(now.normalize()) & history.result.notna()].sort_values('date')
# Reviewed Premier League aliases used in the existing weekend analysis.
aliases = {'leeds united':'leeds','coventry city':'coventry','hull city':'hull',
           'ipswich town':'ipswich','crystal palace':'palace','aston villa':'villa',
           'nottingham forest':'forest','manchester utd':'manchester united',
           'nottingham':'forest'}
def identity(name):
    key = football_identity_key(name)
    return aliases.get(key,key)
for side in ['home','away']:
    history[side+'_key'] = history[side+'_team'].map(identity)
keys=['fixture_day','home_key','away_key']
assert not history.groupby(keys)[['home_score','away_score']].nunique().gt(1).any().any()
history=history.drop_duplicates(keys,keep='last')
known = set(history.home_key) | set(history.away_key)
state = FeatureState()
for row in history.to_dict('records'):
    state.update(row)
rejected = capture_cache_rejections(capture)
records = [json.loads(line) for line in (capture/'odds_snapshots.jsonl').read_text().splitlines()]
eligible, excluded, vectors = [], [], []
for row in records:
    kickoff = pd.Timestamp(row['commence_time'])
    if kickoff.tz_convert('Africa/Kampala').date() != day:
        continue
    reason = rejected.get(row['bookmaker'])
    if kickoff <= now:
        reason = 'already_started'
    if not 0 <= (now-pd.Timestamp(row['observed_at'])).total_seconds() <= 900:
        reason = 'quote_older_than_15_minutes'
    if reason:
        excluded.append({'snapshot_id':row['snapshot_id'],'bookmaker':row['bookmaker'],'reason':reason})
        continue
    try:
        normalized = normalize_snapshots([row]).iloc[0]
        home = identity(row['home_team'])
        away = identity(row['away_team'])
        if home not in known or away not in known:
            raise ValueError('Teams lack training history')
        prices = {key:float(normalized[key]) for key in ['home_win','draw','away_win']}
        vector = state.vector(home,away,prices)
        eligible.append({**row,'canonical_home':home,'canonical_away':away,'prices':prices,
            'home_history_games':int(((history.home_key==home)|(history.away_key==home)).sum()),
            'away_history_games':int(((history.home_key==away)|(history.away_key==away)).sum())})
        vectors.append(vector)
    except ValueError as exc:
        excluded.append({'snapshot_id':row['snapshot_id'],'bookmaker':row['bookmaker'],'reason':str(exc),
                         'home':row['home_team'],'away':row['away_team']})
model = joblib.load(bundle/'model_v2.1.0.pkl')
assert list(manifest['features'])==FEATURE_NAMES
with training_threads(2):
    probabilities = model.predict_proba(pd.DataFrame(vectors,columns=FEATURE_NAMES)) if vectors else []
groups=defaultdict(list)
for row,p in zip(eligible,probabilities):
    row['probabilities']=dict(zip(manifest['classes'],p.tolist()))
    row['analysis']=price_analysis(row['probabilities'],row['prices'])
    groups[(row['canonical_home'],row['canonical_away'],row['commence_time'].replace('Z','+00:00'))].append(row)
fixtures=[]
for key, quotes in groups.items():
    reference=np.mean([[r['probabilities'][c] for c in manifest['classes']] for r in quotes],axis=0)
    forecast=dict(zip(manifest['classes'],reference.tolist()))
    best=[]
    for outcome in manifest['classes']:
        quote=max(quotes,key=lambda q:q['prices'][outcome])
        others=[q for q in quotes if q['bookmaker']!=quote['bookmaker']]
        market_probability=None
        if others:
            market_probability=float(np.mean([(1/q['prices'][outcome])/sum(1/v for v in q['prices'].values()) for q in others]))
        price=quote['prices'][outcome]
        best.append({'outcome':outcome,'bookmaker':quote['bookmaker'],'odds':price,
            'model_probability':forecast[outcome],'fair_odds':1/forecast[outcome],
            'estimated_ev':forecast[outcome]*price-1,'stressed_ev':forecast[outcome]*price*.98-1,
            'other_books_probability':market_probability,'observed_at':quote['observed_at']})
    selection=max(best,key=lambda x:x['stressed_ev'])
    sufficient=min(quotes[0]['home_history_games'],quotes[0]['away_history_games'])>=10
    selected=selection if sufficient and selection['stressed_ev']>=.05 else None
    fixtures.append({'home':quotes[0]['home_team'],'away':quotes[0]['away_team'],'competition':quotes[0]['competition'],
        'kickoff':quotes[0]['commence_time'],'kickoff_eat':pd.Timestamp(quotes[0]['commence_time']).tz_convert('Africa/Kampala').isoformat(),
        'probabilities':forecast,'winner':max(forecast,key=forecast.get),'books':len(quotes),
        'home_history_games':quotes[0]['home_history_games'],'away_history_games':quotes[0]['away_history_games'],
        'best_prices':best,'paper_pick':selected,'quotes':quotes})
fixtures.sort(key=lambda x:x['kickoff'])
report={'generated_at':now.isoformat(),'day_eat':str(day),'model_version':'2.1.0','status':'inactive_candidate_preview',
 'model_sha256':hashlib.sha256((bundle/'model_v2.1.0.pkl').read_bytes()).hexdigest(),
 'history_through':history.date.max().isoformat(),'capture':str(capture),'cache_rejections':rejected,
 'policy':{'minimum_stressed_ev':.05,'payout_haircut':.02,'minimum_history_games_per_team':10,'quote_max_age_seconds':900},
 'limitations':['Paper shortlist; prices not confirmed executable.','No lineup or injury verification or adjustments.',
 'Candidate has not established market-beating performance.','One forecast per quote, averaged equally across books for fixture consensus.'],
 'fixtures':fixtures,'excluded':excluded}
(out/'predictions.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# Today’s market predictions and paper picks','',f'Generated {now.isoformat()}; model 2.1.0 candidate, inactive.','',
 '| Fixture | Kickoff EAT | Home / Draw / Away | Model winner | Paper value selection |',
 '|---|---|---|---|---|']
for f in fixtures:
    p=f['probabilities']; pick=f['paper_pick']
    chosen=f"{pick['outcome']} @ {pick['odds']:.2f} ({pick['bookmaker']}); estimated EV {pick['estimated_ev']:.1%}" if pick else 'Pass'
    lines.append(f"| {f['home']}–{f['away']} | {f['kickoff_eat'][11:16]} | {p['home_win']:.1%} / {p['draw']:.1%} / {p['away_win']:.1%} | {f['winner']} | {chosen} |")
lines += ['',*['- '+s for s in report['limitations']]]
(out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'fixtures':len(fixtures),'eligible_quotes':len(eligible),'paper_picks':sum(f['paper_pick'] is not None for f in fixtures),
 'exclusions':len(excluded),'output':str(out),'epl':[ {k:f[k] for k in ['home','away','probabilities','paper_pick','kickoff_eat']} for f in fixtures if f['competition']=='Premier League']},indent=2))
