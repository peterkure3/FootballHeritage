"""Train isolated causal football models and simulate all November 3–4 UCL games."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import joblib
import numpy as np
import pandas as pd
from lxml import html
from scipy.stats import poisson
from sklearn.base import clone
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_poisson_deviance
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from etl.fetch_football_form import normalize_result, last_five
from models.data import canonical_matches, normalize_matches
from models.features import FEATURE_NAMES, FeatureState, build_feature_frame
from models.league_data import identity, identity_aliases, load_histories
from models.train_football_leagues import train_league
from models.training_resources import training_threads
from models.validation import chronological_split, probability_metrics

RAW = ROOT/'pipeline/data/raw/ucl_nextweek_20261030'
RUN = ROOT/'pipeline/models/model_store/candidates/ucl_nextweek_20261030_final'
OUT = Path(__file__).parent
NOW = datetime.now(timezone.utc)
ALIASES = identity_aliases()
ALIASES.update({'viking':'viking fk', 'fc shakhtar donetsk':'shakhtar donetsk',
    'sporting lisbon':'sp lisbon','galatasaray aş':'galatasaray','inter milan':'inter',
    'inter milano':'inter','paris saint germain':'paris sg','rc lens':'lens',
    'man utd':'manchester united','manchester utd':'manchester united', 'šk slovan':'slovan bratislava',
    'sk slovan bratislava':'slovan bratislava','galatasaray istanbul':'galatasaray',
    'fenerbahce istanbul':'fenerbahce'})
CLASSES = ['away_win','draw','home_win']

def named(frame):
    frame = frame.copy()
    for side in ['home','away']:
        frame[side+'_team'] = frame[side+'_team'].map(lambda name: identity(name,ALIASES))
    return normalize_matches(frame)

def history():
    frames = [named(frame) for frame in load_histories().values()]
    for path in (RAW/'domestic').glob('*.csv'):
        frame=pd.read_csv(path,low_memory=False)
        frame=frame.rename(columns={'Home':'home_team','Away':'away_team','HG':'home_score','AG':'away_score','Res':'FTR'})
        frame=normalize_matches(frame)
        frame=frame[frame.date.ge(pd.Timestamp('2026-07-01',tz='UTC'))]
        frame['competition']='GRE' if path.stem=='G1' else path.stem
        frame['data_source']='football-data.co.uk:current-domestic'
        frames.append(named(frame))
    tree=html.fromstring((RAW/'domestic/slovan.html').read_bytes())
    rows=[]
    for tr in tree.xpath('//tr[contains(@class,"zapasy")]'):
        left=tr.xpath('./td[contains(@class,"aright")]')
        right=tr.xpath('./td[contains(@class,"aleft")]')
        score=tr.xpath('./td[contains(@class,"score")] | .//div[@class="score"]')
        cells=tr.xpath('./td')
        if not left or not right or not score or not cells:continue
        score=re.fullmatch(r'\s*(\d+)\s*:\s*(\d+)\s*',score[0].text_content())
        date_text=' '.join(cells[0].text_content().split())
        date=re.search(r'\b(Jul|Aug|Sep|Oct)\s*(\d{1,2})',date_text)
        if not score or not date:continue
        home=' '.join(left[0].text_content().split())
        away=' '.join(right[0].text_content().split())
        rows.append({'date':pd.to_datetime(date[0]+' 2026',format='%b %d %Y',utc=True),
            'home_team':home,'away_team':away,'home_score':int(score[1]),'away_score':int(score[2]),
            'competition':'SVK','data_source':'slovan:official-domestic','status':'FINISHED'})
    if rows:frames.append(named(pd.DataFrame(rows)))
    rows=[]
    for path in sorted(RAW.glob('team_*.json')):
        for match in json.loads(path.read_text(encoding='utf-8')).get('matches',[]):
            row = normalize_result(match,NOW)
            if row: rows.append(row)
    if rows: frames.append(named(pd.DataFrame(rows)))
    archives=json.loads((RAW/'archives/results.json').read_text(encoding='utf-8'))
    safe={'ESP','EPL','ITA','BNDL','FRA','NED','POR','TUR','CZE','AUS','BEL','UKR','AZER','NOR','SVK','GRE'}
    rows=[row for team in archives for row in team['results'] if row['competition'] in safe]
    frames.append(named(pd.DataFrame(rows)))
    tree=html.fromstring((RAW/'archives/viking-official.html').read_bytes())
    rows=[]
    for tr in tree.xpath('//tr[contains(@class,"schedule__match--played")]'):
        def cell(suffix):
            cells=tr.xpath('./td[contains(@class,"schedule__match__item--'+suffix+'")]')
            return ' '.join(cells[0].text_content().split()) if cells else ''
        match=re.search(r'^[SUT]\s+(.+?)\s+-\s+(.+?)\s+\((\d+)-(\d+)\)',cell('teams'))
        date=re.search(r'(\d{2}\.\d{2}\.\d{4})',cell('date'))
        league=tr.xpath('./td[contains(@class,"--league")]//img/@alt')
        if match and date and league and league[0]=='Eliteserien':
            rows.append(dict(date=pd.to_datetime(date[1],format='%d.%m.%Y',utc=True),home_team=match[1],
                away_team=match[2],home_score=int(match[3]),away_score=int(match[4]),competition='NOR',
                data_source='viking:official-results',status='FINISHED'))
    if rows: frames.append(named(pd.DataFrame(rows)))
    joined=pd.concat(frames,ignore_index=True)
    joined=joined[joined.result.notna() & joined.date.lt(pd.Timestamp(NOW).normalize()) & joined.date.ge(pd.Timestamp('2019-07-01',tz='UTC'))]
    keys=['fixture_day','home_key','away_key']
    disagreements=joined.groupby(keys)[['home_score','away_score']].nunique().max(axis=1).gt(1)
    bad=set(disagreements[disagreements].index)
    mask=joined[keys].apply(tuple,axis=1).isin(bad)
    RAW.joinpath('score-conflicts.csv').write_text(joined.loc[mask].to_csv(index=False),encoding='utf-8')
    result=canonical_matches([joined.loc[~mask]])
    # An alias mismatch can leave two apparent senior fixtures on the same day.
    # Withhold every affected fixture rather than counting either result twice.
    appearances=pd.concat([pd.DataFrame({'row':result.index,'day':result.fixture_day,'team':result[side+'_key']})
                           for side in ['home','away']],ignore_index=True)
    duplicate_rows=appearances.loc[appearances.duplicated(['day','team'],keep=False),'row'].unique()
    result.loc[duplicate_rows].to_csv(RAW/'duplicate-appearances-quarantined.csv',index=False)
    result=result.drop(index=duplicate_rows).reset_index(drop=True)
    # Retain only stable, serializable columns used in training and source review.
    result=result[[c for c in ['date','home_team','away_team','home_score','away_score','result','competition',
                               'data_source','status'] if c in result]]
    print('HISTORY',len(result),'CONFLICT_FIXTURES_EXCLUDED',len(bad),'DUPLICATE_APPEARANCE_ROWS_EXCLUDED',len(duplicate_rows),flush=True)
    fixture_rows=json.loads((RAW/'fixtures.json').read_text(encoding='utf-8'))
    for team in {identity(m[side]['name'],ALIASES) for m in fixture_rows for side in ['homeTeam','awayTeam']}:
        recent=result[(result.home_team==team)|(result.away_team==team)]
        assert len(recent)>=5,('Insufficient form history',team)
        assert recent.date.max()>=pd.Timestamp('2026-10-23',tz='UTC'),('Stale team form',team)
        assert not recent.date.dt.normalize().duplicated().any(),('Duplicate senior appearances',team)
    return result,len(bad)

def outcome_rates(rates):
    axis=np.arange(40)
    result=[]
    for home,away in rates:
        matrix=poisson.pmf(axis,home)[:,None]*poisson.pmf(axis,away)[None,:]
        p=np.array([np.triu(matrix,1).sum(),np.trace(matrix),np.tril(matrix,-1).sum()])
        result.append(p/p.sum())
    return np.asarray(result)

def goal_models(X,fixtures,splits):
    columns=FEATURE_NAMES[FEATURE_NAMES.index('home_elo'):FEATURE_NAMES.index('odds_missing')]
    data=X[columns]
    targets=fixtures[['home_score','away_score']].to_numpy()
    fitted=[]
    selection=[]
    development=np.concatenate([splits['train'],splits['tune']])
    with training_threads(2):
        for side in range(2):
            options={alpha:make_pipeline(StandardScaler(),PoissonRegressor(alpha=alpha,max_iter=1000)) for alpha in [.1,1.,10.]}
            scores={}
            for alpha,model in options.items():
                model.fit(data.iloc[splits['train']],targets[splits['train'],side])
                scores[alpha]=mean_poisson_deviance(targets[splits['tune'],side],model.predict(data.iloc[splits['tune']]))
            alpha=min(scores,key=scores.get)
            model=clone(options[alpha]).fit(data.iloc[development],targets[development,side])
            calibration=splits['calibration']
            scale=float(targets[calibration,side].sum()/model.predict(data.iloc[calibration]).sum())
            fitted.append((model,scale))
            selection.append({'side':side,'alpha':alpha,'tuning_deviance':scores,'calibration_scale':scale})
        predicted=np.column_stack([model.predict(data.iloc[splits['test']])*scale for model,scale in fitted])
    test=splits['test']
    labels=np.array([CLASSES.index(v) for v in fixtures.iloc[test].result])
    baseline=np.tile(targets[development].mean(axis=0),(len(test),1))
    metrics={'selection':selection,'test':probability_metrics(labels,outcome_rates(predicted),CLASSES),
             'baseline':probability_metrics(labels,outcome_rates(baseline),CLASSES),
             'goal_mae':np.abs(predicted-targets[test]).mean(axis=0).tolist(),
             'baseline_goal_mae':np.abs(baseline-targets[test]).mean(axis=0).tolist()}
    cl=fixtures.iloc[test].competition.eq('CL').to_numpy()
    if cl.any():
        metrics['champions_league_test']=probability_metrics(labels[cl],outcome_rates(predicted[cl]),CLASSES)
        metrics['champions_league_baseline']=probability_metrics(labels[cl],outcome_rates(baseline[cl]),CLASSES)
    joblib.dump({'models':fitted,'features':columns},RUN/'goal_models.pkl')
    return fitted,columns,metrics,predicted

def quotes():
    rows=[json.loads(line) for line in (RAW/'sportsbooks/odds_snapshots.jsonl').read_text().splitlines()]
    stake=json.loads((RAW/'sportsbooks/stake-fixtures.json').read_text())
    for fixture in stake['fixtures']:
        if fixture['status']!='active' or fixture['eventStatus']['matchStatus']!='Not started':continue
        teams={team['qualifier']:team['name'] for team in fixture['data']['teams']}
        for group in fixture['groups']:
            for template in group['templates']:
                for market in template['markets']:
                    if market['name']!='1x2' or market['extId']!='1' or market['status']!='active' or market['specifiers']:continue
                    prices={}
                    for outcome in market['outcomes']:
                        key='DRAW' if outcome['name']=='Draw' else 'HOME' if outcome['name']==teams['home'] else 'AWAY' if outcome['name']==teams['away'] else None
                        if key and outcome['active']:prices[key]=float(outcome['odds'])
                    if set(prices)!={'HOME','DRAW','AWAY'}:continue
                    rows.append({'bookmaker':'stake','home_team':teams['home'],'away_team':teams['away'],
                        'commence_time':pd.Timestamp(fixture['data']['startTime']).isoformat(),'observed_at':stake['observed_at'],
                        'market':'h2h','period':'FULL_TIME_90_MIN','settlement_rule':'REGULATION_TIME','is_live':False,
                        'market_status':'OPEN','source_url':stake['url'],
                        'outcomes':[{'selection':key,'odds_decimal':price,'status':'OPEN'} for key,price in prices.items()]})
    return rows

def main():
    assert not RUN.exists(),'Use a fresh run ID; never overwrite a candidate'
    data,conflicts=history()
    metrics=train_league('cross_competition',data,RUN,threads=2)
    X,fixtures=build_feature_frame(data)
    splits=chronological_split(fixtures.date)
    classifier=joblib.load(RUN/'model.pkl')
    fitted,columns,goal_metrics,goal_test=goal_models(X,fixtures,splits)
    with training_threads(2):
        probabilities=classifier.predict_proba(X.iloc[splits['test']])
    labels=np.array([CLASSES.index(v) for v in fixtures.iloc[splits['test']].result])
    cl=fixtures.iloc[splits['test']].competition.eq('CL').to_numpy()
    metrics['champions_league_test']=probability_metrics(labels[cl],probabilities[cl],CLASSES) if cl.any() else None
    development=np.concatenate([splits['train'],splits['tune']])
    counts=np.bincount([CLASSES.index(v) for v in fixtures.iloc[development].result],minlength=3)+1
    if cl.any():metrics['champions_league_prior']=probability_metrics(labels[cl],np.tile(counts/counts.sum(),(cl.sum(),1)),CLASSES)
    state=FeatureState()
    for row in canonical_matches([data]).to_dict('records'):state.update(row)
    offers=quotes()
    results=[]
    fixture_rows=json.loads((RAW/'fixtures.json').read_text(encoding='utf-8'))
    assert len(fixture_rows)==18
    rng=np.random.default_rng(20261103)
    history_frame=canonical_matches([data])
    for fixture in sorted(fixture_rows,key=lambda row:(row['utcDate'],row['homeTeam']['name'])):
        home,away=[identity(fixture[side]['name'],ALIASES) for side in ['homeTeam','awayTeam']]
        kick=pd.Timestamp(fixture['utcDate'])
        vector=pd.DataFrame([state.vector(home,away,None)],columns=FEATURE_NAMES)
        with training_threads(2):
            p=classifier.predict_proba(vector)[0]
            rates=np.array([model.predict(vector[columns])[0]*scale for model,scale in fitted])
        assert np.isfinite(rates).all() and (rates>0).all()
        samples=rng.poisson(rates,size=(100000,2))
        difference=samples[:,0]-samples[:,1]
        sim=np.array([(difference<0).mean(),(difference==0).mean(),(difference>0).mean()])
        np.testing.assert_allclose(sim,outcome_rates([rates])[0],atol=.008,rtol=0)
        book_quotes=[]
        for offer in offers:
            pair=tuple(identity(offer[side+'_team'],ALIASES) for side in ['home','away'])
            if pair!=(home,away) or pd.Timestamp(offer['commence_time'])!=kick:continue
            if offer['market']!='h2h' or offer['period']!='FULL_TIME_90_MIN' or offer['settlement_rule']!='REGULATION_TIME' or offer['is_live']:continue
            if offer['market_status']!='OPEN' or any(v['status']!='OPEN' for v in offer['outcomes']):continue
            prices={dict(HOME='home_win',DRAW='draw',AWAY='away_win')[v['selection']]:v['odds_decimal'] for v in offer['outcomes']}
            if set(prices)!=set(CLASSES) or min(prices.values())<=1:continue
            book_quotes.append({'bookmaker':offer['bookmaker'],'prices':prices,'observed_at':offer['observed_at'],'source_url':offer['source_url']})
        assert book_quotes,home
        market=np.mean([[1/q['prices'][c]/sum(1/v for v in q['prices'].values()) for c in CLASSES] for q in book_quotes],axis=0)
        best={c:max(book_quotes,key=lambda q:q['prices'][c]) for c in CLASSES}
        reciprocal=sum(1/best[c]['prices'][c] for c in CLASSES)
        best_prices={c:{'bookmaker':best[c]['bookmaker'],'odds':best[c]['prices'][c],
                       'exploratory_model_ev':float(p[i]*best[c]['prices'][c]-1)} for i,c in enumerate(CLASSES)}
        form={team:last_five(history_frame,team,NOW) for team in [home,away]}
        modal=np.floor(rates).astype(int)
        results.append({'home':home,'away':away,'kickoff_utc':kick.isoformat(),
            'kickoff_eat':kick.tz_convert('Africa/Kampala').isoformat(),'form':form,
            'classifier_probabilities':dict(zip(CLASSES,p.tolist())),
            'market_probabilities':dict(zip(CLASSES,market.tolist())),
            'goal_model_probabilities':dict(zip(CLASSES,outcome_rates([rates])[0].tolist())),
            'simulated_probabilities':dict(zip(CLASSES,sim.tolist())),
            'expected_goals':{'home':float(rates[0]),'away':float(rates[1]),'total':float(rates.sum())},
            'modal_score':modal.tolist(),'over_2_5':float((samples.sum(axis=1)>2).mean()),
            'btts':float(((samples[:,0]>0)&(samples[:,1]>0)).mean()),
            'total_goals_interval_90':np.quantile(samples.sum(axis=1),[.05,.95]).tolist(),
            'quotes':book_quotes,'best_prices':best_prices,'reciprocal_sum':reciprocal,
            'nominal_arb_roi':1/reciprocal-1,'winner':CLASSES[int(np.argmax(p))]})
    # Independently reload the saved goal models and reproduce untouched holdout rates.
    restored=joblib.load(RUN/'goal_models.pkl')
    with training_threads(2):
        replay=np.column_stack([m.predict(X.iloc[splits['test']][columns])*s for m,s in restored['models']])
    np.testing.assert_allclose(replay,goal_test,atol=1e-12,rtol=0)
    report={'generated_at':NOW.isoformat(),'fixtures':len(results),'runs_per_fixture':100000,'seed':20261103,
        'candidate_directory':str(RUN.relative_to(ROOT)),'history_rows':len(data),'excluded_conflicting_fixtures':conflicts,
        'classifier_validation':metrics,'goal_model_validation':goal_metrics,'models_replayed':True,
        'active_models_changed':False,'model_market_edge_established':False,
        'limitations':['Cross-competition training; CL-only trainer requires 1000 matches and only 557 were available.',
            'Form covers available verified regulation results; does not prove exhaustive all-competition coverage.',
            'Expected goals are score-model means, not shot-based xG.',
            'Lineups, injuries and weather are not model inputs. Weekend results are not yet known.',
            'Poisson goals assume conditional independence. Monte Carlo precision is not model certainty.',
            'Model EV is exploratory; sportsbook taxes, fees and stake limits are excluded.'],
        'model_sha256':{file:hashlib.sha256((RUN/file).read_bytes()).hexdigest() for file in ['model.pkl','goal_models.pkl']},
        'matches':results}
    target=OUT/'ucl-nextweek-predictions-20261030.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    table=[]
    for row in results:
        table.append({'home':row['home'],'away':row['away'],'kickoff_eat':row['kickoff_eat'],
            'home_form':row['form'][row['home']]['sequence'],'away_form':row['form'][row['away']]['sequence'],
            **{c:row['classifier_probabilities'][c] for c in CLASSES},
            'home_expected_goals':row['expected_goals']['home'],'away_expected_goals':row['expected_goals']['away'],
            'total_expected_goals':row['expected_goals']['total'],'over_2_5':row['over_2_5'],'btts':row['btts'],
            'books':','.join(q['bookmaker'] for q in row['quotes']),'nominal_arb_roi':row['nominal_arb_roi']})
    pd.DataFrame(table).to_csv(OUT/'ucl-nextweek-predictions-20261030.csv',index=False)
    for row in table:print(json.dumps(row),flush=True)
    print('REPORT',target,flush=True)

if __name__=='__main__':main()
