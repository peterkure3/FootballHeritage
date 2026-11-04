"""Render an evidence-based verdict without changing production picks."""
import json,math,hashlib
from pathlib import Path
from datetime import datetime,timezone
OUT=Path(__file__).parent;ROOT=OUT.parents[2]
audit=json.loads((OUT/'ai-picks-live-audit-20261021.json').read_text());deep=json.loads((OUT/'ai-picks-deep-audit-20261021.json').read_text());review=json.loads((OUT/'ucl-picks-rechecked-20261021.json').read_text())
picks=audit['http']['pipeline_picks_ucl']['body']['picks'];completed=deep['latest_completed_saved_run'];checks=[]
for p in picks:
    probs=[p[k] for k in ['home_prob','draw_prob','away_prob']];issues=[]
    assert all(math.isfinite(v) and 0<=v<=1 for v in probs) and abs(sum(probs)-1)<1e-6
    if min(probs)==0 or max(probs)==1:issues.append('degenerate_probability_vector')
    if p['decimal_odds'] is not None:
        assert abs(p['model_prob']*p['decimal_odds']-1-p['expected_value'])<1e-10
        assert abs(100*(p['model_prob']-1/p['decimal_odds'])-p['edge_pct'])<1e-10
        age=(datetime.fromisoformat(audit['audit_at'])-datetime.fromisoformat(p['odds_updated_at'])).total_seconds()
        if age>1800:issues.append('quote_older_than_30_minutes')
    else:issues.append('no_quote_to_validate_value')
    checks.append({'fixture':p['home_team']+' – '+p['away_team'],'selection':p['selection'],'model_probability':p['model_prob'],'decimal_odds':p['decimal_odds'],'bookmaker':p['bookmaker'],'arithmetic_correct':True,'outcome':'unsettled','issues':issues})
assert len(picks)==7 and all(datetime.fromisoformat(p['match_date'])>datetime.fromisoformat(audit['audit_at']) for p in picks)
assert completed['wins']==sum(s['won'] for s in completed['settled'])
assert all(s['pre_match'] for s in completed['settled'])
assert deep['upcoming_filter_counts']['legacy_now_count']==0 and deep['upcoming_filter_counts']['utc_now_count']==7
validation={'audit_at':audit['audit_at'],'report_at':datetime.now(timezone.utc).isoformat(),'scope':'Live Football AI Picks, Champions League 2026-10-21; latest completed saved run 2026-10-20','verdict':'arithmetic_passes_but_prediction_pipeline_not_validated','current_pick_checks':checks,'latest_completed_run':completed,'unit_tests':{'ai_picks':5,'betting_intelligence':24,'passed':29},'production_mutations':False,'source_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'ai-picks-live-audit-20261021.json',OUT/'ai-picks-deep-audit-20261021.json',OUT/'ucl-picks-rechecked-20261021.json']}}
(OUT/'ai-picks-validation-20261021.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
lines=['# Live AI Picks validation — 21 October 2026','',
'**Verdict: the calculations are correct for the supplied inputs, but the current picks cannot be certified as reliable or correct predictions.** The live app is using v2.0.0, whereas the separately reviewed forecasts in the conversation used the inactive v2.1.0 candidate and expanded history. Neither model establishes guaranteed wins.',
'',f"Audit snapshot: {audit['audit_at']}. The live pipeline endpoints returned HTTP 200. The authenticated Rust endpoint correctly returned 401 without a session. The frontend on port 5173 was unavailable and the browser-control kernel failed; this audit verifies the live data API and stored runs rather than claiming a visual inspection of the user's browser.",'',
'## Current seven UCL selections','',
'| App selection | Probability | Decimal price | Gross model EV | Validation result |','|---|---:|---:|---:|---|']
for p,c in zip(picks,checks):
    price=f"{p['decimal_odds']:.3f} ({p['bookmaker']})" if p['decimal_odds'] else 'Unavailable';ev=f"{p['expected_value']:+.1%}" if p['expected_value'] is not None else 'Unavailable'
    notes='; '.join(c['issues']) or 'Arithmetic passes; outcome unsettled'
    lines.append(f"| {p['home_team']}–{p['away_team']}: {p['selection']} | {p['model_prob']:.1%} | {price} | {ev} | {notes} |")
lines+=['','All seven fixtures start at 19:00 UTC / 22:00 Kampala. Their future results cannot be labeled correct or incorrect yet. Como–Manchester United and Lille–Galatasaray have already kicked off and were correctly excluded from the current pre-match endpoint. Saved historical runs naturally retain past fixtures; that retention is not itself a stale-pick bug.',
'','## Confirmed reliability failures','',
'1. **The backfill is not used by the active inference path.** The 38-feature v2.0.0 artifact enters `_build_legacy_feature_vector`, which queries the database and ignores the newer history/cutoff argument. The expanded history was exported for reviewed research, not imported into this legacy database path. Exact production-name history counts were Brugge 10, Lens 12, Bayern 27, Inter 32 and Shakhtar 2. Those counts differ materially from the four-season backfill.',
'2. **Bayern’s stored vector assigns draw probability exactly 0%.** Home is 59.3254%, draw 0%, away 40.6746%. The active artifact is a CalibratedClassifierCV. A fresh diagnostic also produces a 0% draw probability because the draw isotonic calibrator maps its base response to zero. The diagnostic home probability differs from the saved run (60.3591% versus 59.3254%); exact original inputs were not frozen, so it is not claimed as exact full-run reproduction. This is evidence of calibration fragility, not proof of the match outcome. Classic Best Picks accepts this vector while Intelligence rejects zero-outcome probability vectors.',
'3. **The batch predictor has a verified timezone selection bug.** The match date column is `timestamp without time zone`, the database timezone is Africa/Nairobi, and `get_upcoming_matches` compares its UTC wall-clock values against `NOW()`. At audit time that query selected zero of tonight’s UCL fixtures, while `NOW() AT TIME ZONE \'UTC\'` selected seven. This can stop prediction refreshes up to three hours before kickoff. The API selection query already uses the UTC form, so the bug was not observed as seven missing API picks.',
'4. **Price freshness and market evidence are weaker in classic AI Picks.** Feyenoord’s 4.80 BetOnline price was timestamped 08:40 UTC, over eight hours before the audit. The classic route permits 24-hour quotes; Intelligence uses 30 minutes. Three selections have no stored quote at all. Stored `updated_at` alone does not verify upstream cache age, market openness or acceptance at a bookmaker.',
'5. **The two models disagree substantially on the leading value bets.** This does not prove the candidate is correct. It shows these EV claims are model-sensitive, not independently verified edges. At the app’s displayed price:','',
'| Outcome | Active v2.0 probability | Reviewed v2.1 probability | Active gross EV | Reviewed gross EV at same app price |','|---|---:|---:|---:|---:|']
mapping={575374:('Aston Villa','draw'),575370:('Real Madrid','away_win'),575376:('Betis','away_win')}
for p in picks:
    if p['match_id'] not in mapping:continue
    team,selection=mapping[p['match_id']];m=next(m for m in review['matches'] if m['home']==team);prob=m['probabilities'][selection]
    lines.append(f"| {p['selection']} in {p['home_team']}–{p['away_team']} | {p['model_prob']:.1%} | {prob:.1%} | {p['expected_value']:+.1%} | {prob*p['decimal_odds']-1:+.1%} |")
lines+=['',
'The v2.1 values above are the previously frozen review, not a new in-play forecast. Its holdout evaluation did not prove market superiority. The fresh public bookmaker capture at 17:08 UTC was retained separately in `pipeline/data/raw/ucl_revision_20261021T170833Z`; it does not independently establish execution of the app’s Betika, BetOnline or 1xbet prices.',
'','## Latest completed saved run','',
f"Saved {completed['run_created_at']}, requested date {completed['requested_date']}: **{completed['wins']} wins from {completed['picks']} selections ({completed['wins']/completed['picks']:.1%}); {completed['picks']-completed['wins']} losses.** All selected predictions and the saved run preceded kickoff. Results are completed regulation-time scores from the archived football-data.org CL response captured before today’s matches.",'',
'| Fixture | Saved selection | Final score | Correct? |','|---|---|---|---|']
for s in completed['settled']:lines.append(f"| {s['fixture']} | {s['selection']} | {s['score']} | {'Yes' if s['won'] else 'No'} |")
lines+=['',f"For the {completed['paper_quoted_picks']} selections with stored prices, a hypothetical one-unit stake per quoted pick gives net {completed['paper_profit']:+.2f} units before tax/fees. One unpriced selection is excluded from that profit calculation. This is a paper calculation from saved prices, not verified placed bets or evidence of long-run profitability. Duplicate saved runs were not pooled.",
'','## Checks and disposition','',
'- Five existing AI Picks unit tests and 24 betting-intelligence tests passed. The initial module-style test invocation could not import the test modules; discovery-style invocation completed successfully.',
'- All seven current displayed EV and edge calculations were recomputed successfully. Probability sums were checked; the Bayern zero-draw issue was flagged even though its selected home probability is nonzero.',
'- Fallow reported preexisting repository issues (310 dead-code findings, 44 clone groups, 173 complexity findings); no production code was changed in this audit.',
'- No model promotion, prediction replacement, database write or bet was performed. Fix the legacy input integration, timezone cutoff, zero-probability handling and price freshness before treating current value labels as validated recommendations.',
'','Artifacts: `ai-picks-live-audit-20261021.json`, `ai-picks-deep-audit-20261021.json`, `ai-picks-validation-20261021.json`.','']
(OUT/'ai-picks-validation-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'verdict':validation['verdict'],'current_picks':len(checks),'arithmetic_passed':sum(c['arithmetic_correct'] for c in checks),'completed_run_correct':completed['wins'],'completed_run_total':completed['picks'],'tests_passed':29,'report':str(OUT/'ai-picks-validation-20261021.md')}))
