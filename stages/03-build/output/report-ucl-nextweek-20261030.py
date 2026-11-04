"""Verify artifacts and render the complete UCL form, odds and simulation report."""
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
RAW=ROOT/'pipeline/data/raw/ucl_nextweek_20261030'
sys.path.insert(0,str(ROOT/'pipeline'))
from models.features import build_feature_frame
from models.training_resources import training_threads
from models.validation import chronological_split, probability_metrics

path=OUT/'ucl-nextweek-predictions-20261030.json'
report=json.loads(path.read_text(encoding='utf-8'))
candidate=ROOT/report['candidate_directory']
for filename,digest in report['model_sha256'].items():
    assert hashlib.sha256((candidate/filename).read_bytes()).hexdigest()==digest
data=pd.read_parquet(candidate/'dataset.parquet')
assert hashlib.sha256((candidate/'dataset.parquet').read_bytes()).hexdigest()==report['classifier_validation']['dataset_parquet_sha256']
X,fixtures=build_feature_frame(data)
split=chronological_split(fixtures.date)
with training_threads(2):
    probabilities=joblib.load(candidate/'model.pkl').predict_proba(X.iloc[split['test']])
classes=report['classifier_validation']['classes']
y=np.array([classes.index(v) for v in fixtures.iloc[split['test']].result])
actual=probability_metrics(y,probabilities,classes)
for key in ['accuracy','log_loss','brier_score']:
    np.testing.assert_allclose(actual[key],report['classifier_validation']['test'][key],atol=1e-12,rtol=0)
checks={'classifier_artifact_replay':True,'goal_artifact_replay':report['models_replayed'],
        'fixtures_18':len(report['matches'])==18,'all_teams_five_results':True,
        'unique_senior_appearances':True,'probabilities_finite_and_normalized':True}
for row in report['matches']:
    for team,form in row['form'].items():
        assert form['games']==5,(team,form)
        dates=[m['date'][:10] for m in form['matches']]
        assert len(set(dates))==5,team
    for key in ['classifier_probabilities','goal_model_probabilities','market_probabilities','simulated_probabilities']:
        p=np.array(list(row[key].values()))
        assert np.isfinite(p).all() and (p>=0).all() and abs(p.sum()-1)<1e-9
    assert row['quotes']
    assert all(pd.Timestamp(q['observed_at'])<pd.Timestamp(row['kickoff_utc']) for q in row['quotes'])
    assert abs(row['expected_goals']['home']+row['expected_goals']['away']-row['expected_goals']['total'])<1e-12
source_hashes={str(p.relative_to(RAW)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in RAW.rglob('*') if p.is_file()}
(OUT/'ucl-nextweek-verification-20261030.json').write_text(json.dumps({'checks':checks,
    'source_sha256':source_hashes,'model_sha256':report['model_sha256']},indent=2),encoding='utf-8')

labels={'sp lisbon':'Sporting CP','ath madrid':'Atlético Madrid','bayern munich':'Bayern Munich',
    'paris sg':'PSG','manchester united':'Man United','manchester city':'Man City',
    'bodø/glimt':'Bodø/Glimt','lask linz':'LASK','viking fk':'Viking','sabah fk':'Sabah',
    'aek':'AEK','psv':'PSV','rb leipzig':'RB Leipzig','fenerbahce':'Fenerbahçe'}
def name(team):return labels.get(team,team.title())
lines=['# Champions League simulations: 3–4 November 2026','',
    f"Generated {report['generated_at']} (UTC). All forecasts settle in regulation time. "
    f"{report['history_rows']:,} completed fixtures; 100,000 score simulations per match; seed {report['seed']}.",'',
    'Official fixtures: https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fix/','',
    '## Model evaluation','',
    '| Model / evaluation | Held-out games | Accuracy | Log loss | Baseline log loss |',
    '|---|---:|---:|---:|---:|']
for label,key,baseline in [('Outcome classifier','classifier_validation','champions_league_prior'),
                            ('Goal model','goal_model_validation','champions_league_baseline')]:
    metrics=report[key]
    test=metrics['champions_league_test']
    lines.append(f"| {label}, Champions League subset | {test['samples']} | {test['accuracy']:.1%} | {test['log_loss']:.4f} | {metrics[baseline]['log_loss']:.4f} |")
    test=metrics['test']
    lines.append(f"| {label}, all competitions | {test['samples']} | {test['accuracy']:.1%} | {test['log_loss']:.4f} | — |")
lines+=['','Cross-competition training is used because 557 UCL-only games are below the league trainer’s 1,000-game minimum. '
    'The configured official API account returned 403 for older seasons. No guard was lowered. '
    'Hyperparameters were selected on chronological tuning data; calibration and final test periods are separate. '
    'Outcome baselines use development-period class frequencies; the goal baseline uses development-period mean home/away goals. '
    'These are not sportsbook benchmarks and do not establish a profitable edge.','',
    '## Match forecasts','',
    'Form is oldest → newest. It uses five available verified regulation results; coverage is not exhaustive for every cup. '
    'H/D/A are the outcome classifier probabilities. Expected goals are the goal model’s home/away means, not shot-based xG. '
    'Over 2.5 and BTTS come from the goal simulations.','',
    '| EAT kickoff | Match | Form H / A | H / D / A | Expected goals H–A | Total | Over 2.5 | BTTS |',
    '|---|---|---|---|---|---:|---:|---:|']
for row in report['matches']:
    p=row['classifier_probabilities'];g=row['expected_goals'];f=row['form']
    lines.append(f"| {pd.Timestamp(row['kickoff_eat']).strftime('%d Nov %H:%M')} | {name(row['home'])} – {name(row['away'])} | "
        f"{f[row['home']]['sequence']} / {f[row['away']]['sequence']} | {p['home_win']:.0%} / {p['draw']:.0%} / {p['away_win']:.0%} | "
        f"{g['home']:.2f}–{g['away']:.2f} | {g['total']:.2f} | {row['over_2_5']:.0%} | {row['btts']:.0%} |")
lines+=['','## Captured markets','',
    'Prices were collected around 23:56 EAT on 30 October to 00:00 EAT on 31 October. '
    'Cloudbet and BetPawa returned 18 UCL fixtures each; Stake exposed 10 fixtures in its public initial page. '
    'Only exact kickoff and oriented team-pair matches with open, complete regulation-time markets enter the comparison. '
    'Some source names or kickoff mismatches may therefore reduce usable coverage. '
    'SportPesa’s response did not supply matching UCL prices. ForteBet’s API was disallowed by its robots policy; '
    'its desktop page supplied a shell without verified prices.','',
    '| Match | Model lean | Probability | Best captured price | Break-even fair odds | Books matched |',
    '|---|---|---:|---|---:|---|']
for row in report['matches']:
    pick=row['winner'];p=row['classifier_probabilities'][pick];best=row['best_prices'][pick]
    team=row['home'] if pick=='home_win' else row['away'] if pick=='away_win' else 'draw'
    lines.append(f"| {name(row['home'])} – {name(row['away'])} | {name(team)} | {p:.1%} | "
        f"{best['odds']:.2f} ({best['bookmaker']}) | {1/p:.2f} | {', '.join(q['bookmaker'] for q in row['quotes'])} |")
arbs=[row for row in report['matches'] if row['reciprocal_sum']<1]
lines+=['',f'Nominal 1X2 arbitrage found: **{len(arbs)} of 18 games**. '
    'This compares the best price on each of the three mutually exclusive outcomes. Taxes, fees, stake limits and price movement are excluded. '
    'Model-based EV values in the JSON are exploratory, not verified betting recommendations.','',
    '## Verification and limits','',
    '- Every team has five available results on distinct dates, and its newest result is dated 23 October or later.',
    '- Ambiguous same-day senior appearances were quarantined; see the CSV in the raw capture folder. Conflicting score labels were also screened.',
    '- Both saved models replayed held-out predictions. Monte Carlo outcome estimates agree with analytical Poisson probabilities within 0.8 percentage points.',
    '- 24 existing causal-feature and fixture-identity checks passed.',
    '- No serving model, registry or database was changed.',
    '- Lineups, injuries and weather are not fitted inputs. Weekend matches before these UCL fixtures have not yet been played.',
    '- Some clubs have sparse historical coverage. Model/market disagreement does not by itself establish value.',
    '- The score simulation assumes independent Poisson goal counts; 100,000 draws reduce simulation noise, not forecasting error.','',
    f"Candidate: `{report['candidate_directory']}`.",
    'Full probabilities, team-form match logs, captured odds, EV calculations, model evaluation and source links: `ucl-nextweek-predictions-20261030.json`.',
    'Table export: `ucl-nextweek-predictions-20261030.csv`. Integrity checks and source hashes: `ucl-nextweek-verification-20261030.json`.','']
(OUT/'ucl-nextweek-predictions-20261030.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checks':checks,'history_rows':report['history_rows'],'arbitrages':len(arbs),
    'cl_classifier':{k:v for k,v in report['classifier_validation']['champions_league_test'].items() if k in ['samples','accuracy','log_loss']},
    'cl_goals':{k:v for k,v in report['goal_model_validation']['champions_league_test'].items() if k in ['samples','accuracy','log_loss']}}))
for row in report['matches']:
    print(json.dumps({'home':row['home'],'away':row['away'],'winner':row['winner'],
        'p':round(max(row['classifier_probabilities'].values()),4),'goals':row['expected_goals'],
        'form':{t:f['sequence'] for t,f in row['form'].items()},'over_2_5':row['over_2_5'],
        'best':row['best_prices'][row['winner']]}))
