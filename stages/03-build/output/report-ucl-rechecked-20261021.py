"""Reproduce forecast probabilities and render the revised betting review."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd,numpy as np,joblib
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'));sys.stdout.reconfigure(encoding='utf-8')
from models.features import FEATURE_NAMES
r=json.loads((OUT/'ucl-picks-rechecked-20261021.json').read_text());matches=r['matches'];directory=ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020';metrics=json.loads((directory/'metrics_v2.1.0.json').read_text());classes=metrics['classes']
assert hashlib.sha256((directory/'model_v2.1.0.pkl').read_bytes()).hexdigest()==r['model_sha256']
model=joblib.load(directory/'model_v2.1.0.pkl')
with threadpool_limits(limits=2):reproduced=model.predict_proba(pd.DataFrame([m['features'] for m in matches],columns=FEATURE_NAMES))
expected=np.array([[m['probabilities'][c] for c in classes] for m in matches]);assert np.allclose(reproduced,expected,atol=1e-12)
assert len(matches)==9 and np.allclose(expected.sum(axis=1),1) and (expected>0).all() and (expected<1).all()
assert all(len({q['bookmaker'] for q in m['quotes']})==len(m['quotes']) for m in matches)
assert all(q['bookmaker'] in {'ababet','cloudbet','betpawa'} for m in matches for q in m['quotes'])
for m in matches:
    inv=sum(1/m['best'][c]['odds'] for c in classes);assert abs(inv-m['reciprocal_sum'])<1e-12
    for c in classes:assert abs(m['probabilities'][c]*m['best'][c]['odds']-1-m['best'][c]['ev'])<1e-12
assert all(m['reciprocal_sum']>1 for m in matches)
verification={'verified_at':datetime.now(timezone.utc).isoformat(),'forecast_rows_reproduced':9,'complete_quote_sets':sum(len(m['quotes']) for m in matches),'model_sha256':r['model_sha256'],'probability_price_ev_and_arbitrage_checks_passed':True,'source_capture':r['capture'],'analysis_sha256':hashlib.sha256((OUT/'ucl-picks-rechecked-20261021.json').read_bytes()).hexdigest()}
(OUT/'ucl-picks-recheck-verification-20261021.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
lines=['# Champions League picks rechecked — 21 October 2026','',
'Public prices observed **15:38:25–15:38:26 UTC / 18:38 Kampala**. This is a timestamped snapshot, not confirmation of an executable ticket. Final team lineups were not independently confirmed. Markets are 90 minutes plus stoppage time.',
'',
'## Revised shortlist','',
'1. **Club Brugge win at 1.94, Ababet:** the main revised value candidate. Five available consecutive wins versus Lens DLWLW. The model estimate is 56.2%, versus 51.1% de-vig consensus. Its rise is mostly caused by expanded history: at the same refreshed prices the old history gave 52.1%. Belgian opponent history remains less complete than the target club history, so the larger estimate is still experimental.',
'2. **Lille win at 2.30, Cloudbet:** retains tentative value, with a lower probability estimate than earlier. Current model 47.1%; de-vig market 42.3%; best-price break-even 43.5%. Mixed form WLWLD means this is a price-based candidate, and a draw or defeat is collectively more likely than a Lille win.',
'3. **Real Madrid win at 1.27, Ababet:** a likely-winner selection at 82.0% model probability, rather than a large value opportunity. Market consensus is 78.5%. Real have four wins in the latest five available results. The short price leaves limited margin for estimation error.',
'',
'**Bayern win at 2.28, Ababet remains conditional:** raw model 49.7%, but the official club preview confirms Olise is suspended and Musiala unavailable. Neuer’s return and Kompany’s presence were unresolved in that preview. These factors are not explicitly modeled; no invented numerical adjustment has been applied. Do not treat the raw +13.4% EV as injury-adjusted value.',
'',
'Sporting win at 1.29 is an alternative likely-winner lean (82.4% model, 76.5% market), subject to lineup review. Betis–Feyenoord draw at 4.72, betPawa, is the largest raw EV signal (+16.0%), but the estimated chance is only 24.6%; it stays a speculative watchlist outcome, outside the main shortlist. Betis win at 1.70 is now slightly negative EV in the model and is a pass.','',
'## All forecasts and prices','',
'All probabilities are experimental. H / D / A means home win / draw / away win. Best-price comparisons use accepted public sources only.','',
'| Fixture | Model H / D / A | Best H / D / A | Home-win gross model EV | Home form / away form |','|---|---|---|---:|---|']
for m in matches:
    probabilities=' / '.join(f"{m['probabilities'][c]:.1%}" for c in ['home_win','draw','away_win'])
    prices=' / '.join(f"{m['best'][c]['odds']:.2f} {m['best'][c]['bookmaker']}" for c in ['home_win','draw','away_win'])
    lines.append(f"| {m['home']} – {m['away']} | {probabilities} | {prices} | {m['best']['home_win']['ev']:+.1%} | {m['form'][m['home']]['last_five']} / {m['form'][m['away']]['last_five']} |")
closest=min(matches,key=lambda m:m['reciprocal_sum'])
lines+=['','## Arbitrage','',f"No confirmed arbitrage across {verification['complete_quote_sets']} complete book/fixture quote sets. Every best-price reciprocal sum exceeds 1. Closest: {closest['home']}–{closest['away']}, sum {closest['reciprocal_sum']:.6f}, gross return {closest['nominal_arb_roi']:.3%} before fees or taxes. Buying all three outcomes would lose money at these prices.",'',
'## What changed and what was verified','',
f"The frozen reviewed v2.1.0 model was rerun with {r['history_rows']:,} causal results, including the {r['new_history_regulation_rows']:,} validated results in the 18-club backfill. The 58 awarded or uncertain extra-time/penalty records remain outside modeling. Existing target-club results in the covered period were replaced, not appended on top. Cross-source opponent aliases were aligned using overlapping fixture evidence; no ambiguous proposals were applied.",
'',
'The same-price comparison isolates the effect of the history changes from the price refresh. The new histories changed the biggest outcome probability by about 4.1 percentage points for Brugge and 2.4 points for Betis; the other seven fixtures changed by less than 1.7 points. This is sensitivity analysis, not a calibration result.',
'',
'All nine forecasts reproduced from saved feature vectors. Market normalization, finite probability sums, model checksum, one quote per bookmaker, best-price EV and reciprocal-sum calculations passed. Bovada was rejected because its cache Age was 1,694 seconds; Bookmaker was conservatively omitted because its page’s price timestamp was over an hour old. Retained sources: betPawa, Cloudbet and Ababet.',
'',
'The model was not retrained or promoted. Earlier holdout comparisons did not establish market-beating performance: model-minus-market log-loss bootstrap interval included zero. Gross EV = probability × decimal price − 1; it is conditional on model accuracy and excludes taxes, fees, limits and execution differences. Prefer tentative singles over an accumulator; no bet was placed.',
'',
'Lille and Como kick off at **19:45 Kampala**; the other seven fixtures at **22:00 Kampala**. Recheck the ticket price and starting XI before any decision.','',
'## Evidence','',
'- [Official Bayern preview and absences](https://fcbayern.com/es/noticias/matchpreviews/2026/10/previa-champions-league-fc-bayern-fc-arsenal)',
'- [Galatasaray official Lille preview and traveling squad](https://www.galatasaray.org/haber/futbol/sampiyonlar-ligi/maca-dogru-lille-galatasaray/61183)',
'- [Real Madrid announced squad](https://www.realmadrid.com/en-US/news/football/first-team/squad-call/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)',
'- [Backfill coverage](ucl-history-backfill-20261021.md)',
'- [Forecasts and quote evidence](ucl-picks-rechecked-20261021.json)',
'- [Verification](ucl-picks-recheck-verification-20261021.json)',
'- Public sources: [Ababet](https://ababet.ug/), [Cloudbet UCL](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events), [betPawa Uganda](https://www.betpawa.ug/).','']
(OUT/'ucl-picks-rechecked-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(verification))
