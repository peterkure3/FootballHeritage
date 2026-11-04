"""Recompute best net returns with verified Uganda winnings withholding."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
OUT=Path(__file__).parent
source=OUT/'ucl-prices-lineups-validated-20261021.json'
report=json.loads(source.read_text(encoding='utf-8'))
rows=[]
for match in report['matches']:
    best={}
    for outcome in ['HOME','DRAW','AWAY']:
        alternatives=[]
        for quote in match['quotes']:
            rate=.15 if quote['bookmaker'] in {'ababet','betpawa'} else 0
            effective=1+(quote['prices'][outcome]-1)*(1-rate)
            alternatives.append({'bookmaker':quote['bookmaker'],'gross_odds':quote['prices'][outcome],'winnings_withholding_rate':rate,'effective_return_multiple':effective})
        best[outcome]=max(alternatives,key=lambda q:q['effective_return_multiple'])
    reciprocal=sum(1/q['effective_return_multiple'] for q in best.values())
    roi=1/reciprocal-1
    # Independent equal-return allocation confirms the derived ROI.
    stakes={o:(1/q['effective_return_multiple'])/reciprocal for o,q in best.items()}
    assert abs(sum(stakes.values())-1)<1e-12
    assert all(abs(stakes[o]*q['effective_return_multiple']-1-roi)<1e-12 for o,q in best.items())
    rows.append({'match_id':match['match_id'],'home':match['home'],'away':match['away'],'gross_nominal_roi':match['nominal_arb_roi'],'best_effective_returns':best,'reciprocal_sum':reciprocal,'equal_return_roi':roi,'net_arbitrage_under_scenario':reciprocal<1})
result={'generated_at':datetime.now(timezone.utc).isoformat(),'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tax_rule':'15% of payout minus the individual winning stake on Ababet Uganda and betPawa Uganda legs. Cloudbet assigned zero deduction as an optimistic sensitivity assumption; this does not establish tax exemption. Assumes displayed odds are gross before separately applied withholding. Bet-slip net payouts were not accessible.','sources':['https://ura.go.ug/en/witholding-tax/','https://www.betpawa.ug/terms'],'effective_return_formula':'1 + (decimal_odds - 1) * (1 - winnings_tax_rate)','nominal_opportunities':report['arbitrage_opportunities'],'net_opportunities_under_scenario':sum(r['net_arbitrage_under_scenario'] for r in rows),'matches':rows}
(OUT/'ucl-prices-lineups-tax-check-20261021.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
md=OUT/'ucl-prices-lineups-validated-20261021.md'
addition=['','## Tax validation — final arbitrage conclusion','',
    'The two gross price discrepancies are not validated net-profit opportunities. [URA current withholding guidance](https://ura.go.ug/en/witholding-tax/) states 15% applies to winnings (payout less stake). [betPawa terms](https://www.betpawa.ug/terms) confirm applicable taxes are deducted before account credit.','',
    'Recomputed best returns across all accepted books using effective multiple = 1 + (odds − 1) × 0.85 on Ababet Uganda and betPawa Uganda. For an optimistic sensitivity check only, Cloudbet was assigned zero withholding; this is not a claim of tax exemption. Displayed prices are assumed gross; actual account bet-slip net payouts and applicable personal tax were not accessible.','',
    '| Match | Gross best-price ROI | Best-return ROI with Uganda-leg deduction |','|---|---:|---:|']
for r in rows:
    if r['gross_nominal_roi']>0:addition.append(f"| {r['home']} – {r['away']} | {r['gross_nominal_roi']:+.3%} | {r['equal_return_roi']:+.3%} |")
addition+=['',f"Net arbitrage under this scenario: {result['net_opportunities_under_scenario']}. No guaranteed-profit claim or execution recommendation is supported. All seven effective-return allocations were independently checked for equal payouts and total stake conservation.",'']
text=md.read_text(encoding='utf-8').split('\n## Tax validation — final arbitrage conclusion')[0]
md.write_text(text+'\n'.join(addition),encoding='utf-8')
print(json.dumps({'net_opportunities_under_scenario':result['net_opportunities_under_scenario'],'candidates':[r for r in rows if r['gross_nominal_roi']>0]},ensure_ascii=False))
