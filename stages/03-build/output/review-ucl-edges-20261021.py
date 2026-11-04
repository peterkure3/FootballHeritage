"""Separate price movement from odds-dependent probability changes."""
import json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
OUT=Path(__file__).parent;ROOT=OUT.parents[2];sys.path.insert(0,str(ROOT/'pipeline'))
from models.features import FEATURE_NAMES
sys.stdout.reconfigure(encoding='utf-8')
current=json.loads((OUT/'ucl-edge-recheck-model-20261021.json').read_text())
old=json.loads((OUT/'ucl-final-picks-model-20261021.json').read_text())
directory=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020'
assert hashlib.sha256((directory/'model_v2.1.0.pkl').read_bytes()).hexdigest()==current['model_sha256']==old['model_sha256']
model=joblib.load(directory/'model_v2.1.0.pkl');encoder=joblib.load(directory/'label_encoder_v2.1.0.pkl')
classes=list(encoder.inverse_transform(model.classes_));assert classes==['away_win','draw','home_win']
with threadpool_limits(limits=2):p=model.predict_proba(pd.DataFrame([r['features'] for r in current['matches']],columns=FEATURE_NAMES))
rows=[]
for row,reproduced in zip(current['matches'],p):
    assert np.allclose(reproduced,[row['probabilities'][c] for c in classes],rtol=0,atol=1e-12)
    prior=next(r for r in old['matches'] if r['home']==row['home'])
    assert all(row['features'][f]==prior['features'][f] for f in FEATURE_NAMES if f not in FEATURE_NAMES[:11]+['odds_missing'])
    for c in classes:
        best=row['best'][c];assert best['odds']==max(q['prices'][c] for q in row['quotes'])
        assert abs(row['probabilities'][c]*best['odds']-1-best['ev'])<1e-12
    best=row['best']['home_win'];prob=row['probabilities']['home_win'];frozen=prior['probabilities']['home_win']
    # All seven best home prices in this capture are Uganda-bookmaker offers.
    assert best['bookmaker'] in {'ababet','betpawa'}
    effective=1+.85*(best['odds']-1)
    ev=prob*effective-1;frozen_ev=frozen*effective-1
    rows.append({'home':row['home'],'away':row['away'],'current_price':best['odds'],'bookmaker':best['bookmaker'],'previous_price':prior['best']['home_win']['odds'],'model_probability':prob,'frozen_previous_probability':frozen,'market_probability':row['consensus']['home_win'],'ev_after_winnings_withholding':ev,'ev_at_frozen_probability':frozen_ev,'ev_if_probability_3pp_lower':max(0,prob-.03)*effective-1,'break_even_gross_price_at_frozen_probability':1+(1/frozen-1)/.85,'previous_accepted_books':sorted(q['bookmaker'] for q in prior['quotes']),'current_accepted_books':sorted(q['bookmaker'] for q in row['quotes'])})
report={'generated_at':datetime.now(timezone.utc).isoformat(),'price_observed_at':current['price_observed_at'],'model_sha256':current['model_sha256'],'independent_inference_reproduced':7,'all_21_gross_EV_calculations_checked':True,'historical_features_unchanged':True,'tax_assumption':'15% withheld from winning payout above its individual stake; displayed odds assumed gross; final personal tax position and account bet-slip not verified.','model_edge_proven':False,'player_availability_explicitly_modelled':False,'rows':rows}
(OUT/'ucl-edge-recheck-20261021.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# UCL edge recheck — 21 October 2026','',f"Generated {report['generated_at']}. Public prices observed {', '.join(report['price_observed_at'])}.",'',
    'Main conclusion: Sporting remains the stronger provisional single at 1.37 Ababet. Brugge has shortened from 1.94 to 1.88 and is downgraded to marginal/watchlist when assessed at its earlier frozen probability. No demonstrated profitable edge or certain winner is established.','',
    '| Home selection | Current odds | Current model chance | EV after winnings withholding | EV at frozen 21:01 probability | EV if current probability is 3pp too high |','|---|---:|---:|---:|---:|---:|']
for r in rows:lines.append(f"| {r['home']} | {r['current_price']:.2f} {r['bookmaker']} | {r['model_probability']:.1%} | {r['ev_after_winnings_withholding']:+.2%} | {r['ev_at_frozen_probability']:+.2%} | {r['ev_if_probability_3pp_lower']:+.2%} |")
lines+=['',
    'The probability stress is a sensitivity scenario, not a confidence interval. The model uses prices as input, so shortening odds can raise its probability without new independent team evidence. Holding the previous probability fixed isolates the offered-price effect. The set of accepted sources also changed: Bookmaker passed at 18:01 but was excluded at 18:16 under the conservative page Last-Modified rule. Changes in probabilities therefore include source-composition effects as well as actual price moves.','',
    'Historical features are identical between runs. All seven saved probability vectors were independently reproduced using the model’s label encoder; all 21 best-price/gross-EV calculations were rechecked. Official lineups were refreshed around 18:17 UTC and retained the same starting-player IDs. Explicit lineup/injury adjustments are still absent from the model.','',
    'Withholding calculation: effective return multiple = 1 + (gross decimal odds − 1) × 0.85. EV = probability × effective multiple − 1. [URA current guidance](https://ura.go.ug/en/witholding-tax/). This is the immediate payout deduction assumption, not a comprehensive personal-tax calculation.','',
    'Inter and Villa retain positive statistical estimates but remain passes due to unmodelled selection uncertainty. Bayern also has a positive estimate but missing Olise and Musiala are not explicitly modelled. Madrid is negative after withholding at 1.27. Betis home is negative before withholding.','',
    'Companion artifacts: `ucl-prices-lineups-validated-20261021.md`, `ucl-prices-lineups-tax-check-20261021.json`, `ucl-edge-recheck-model-20261021.json`. Captured odds do not establish bet acceptance, stake limits or final net bet-slip payout. No bet was placed.','']
(OUT/'ucl-edge-recheck-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(report))
