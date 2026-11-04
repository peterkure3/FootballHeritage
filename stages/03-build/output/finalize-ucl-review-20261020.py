"""Record reproducible forecast arithmetic; no orders or database mutations."""
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
forecast = json.loads((OUT/'ucl-reviewed-forecasts-20261020.json').read_text(encoding='utf-8'))
review = json.loads((OUT/'ucl-recalibration-review-20261020.json').read_text(encoding='utf-8'))
arbs = []
table = []
for row in forecast['matches']:
    p = row['probabilities']
    assert set(p) == {'home_win', 'draw', 'away_win'}
    assert all(0 < v < 1 for v in p.values()) and abs(sum(p.values())-1) < 1e-10
    table.append(f"| {row['home_team']} – {row['away_team']} | {p['home_win']:.1%} | {p['draw']:.1%} | {p['away_win']:.1%} | {'Recent stored odds + history' if row['fresh_quote_count'] else 'History only'} |")
    if not row.get('best_prices'):
        continue
    prices = row['best_prices']
    reciprocal_sum = sum(1/v['price'] for v in prices.values())
    if reciprocal_sum >= 1:
        continue
    stakes = {c:100/(v['price']*reciprocal_sum) for c,v in prices.items()}
    payouts = [stakes[c]*v['price'] for c,v in prices.items()]
    assert abs(sum(stakes.values())-100) < 1e-10 and np.ptp(payouts) < 1e-10
    arbs.append(dict(home=row['home_team'],away=row['away_team'],reciprocal_sum=reciprocal_sum,
                     gross_return_on_stake=1/reciprocal_sum-1,best_prices=prices,stakes_per_100=stakes,
                     execution_verified=False))
audit = dict(forecast_as_of=forecast['generated_at'],checks='Probability sums, reciprocal sums and equal-payout allocation verified',
             nominal_arbitrage=arbs,execution_verified=False,
             limitation='Stored quotes only: availability, market rules, limits, commission, taxes and simultaneous acceptance were not verified.')
(OUT/'ucl-final-price-audit-20261020.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
arb_text = '\n'.join(f"- {a['home']} – {a['away']}: {a['gross_return_on_stake']:.2%} nominal gross return; reciprocal sum {a['reciprocal_sum']:.6f}." for a in arbs)
report = f'''# Champions League history and calibration review — 20 October 2026

The isolated candidate is `ucl_europe_reviewed_20261020`, using the project's v2.1 feature and expert-selection pipeline. The active v2.0.0 model was not replaced. These forecasts are experimental; they are not validated profitable bets or guaranteed wins.

## Data and coverage

The requested scope was the last three seasons plus current season for all 18 clubs, including domestic leagues, cups and Europe. Collection substantially expanded coverage, but **all-competition coverage is incomplete**. Records or access for Europa League, Conference League and several domestic cups were unavailable; archive scores whose regulation-time interpretation was uncertain were excluded. No all-history completion claim is supported.

The repaired training dataset contains 19,005 unique completed fixtures across its full historical span, not 19,005 matches involving only tonight's clubs. Captures include 10,355 domestic CSV rows, 2,789 deduplicated archive fixtures (partially overlapping those CSVs), 129 official Slovan/Glimt domestic results, and 539 official regulation-time Champions League results across 2023–2026. These source counts overlap and must not be added together. Coverage per club and source provenance are in `ucl-history-review-20261020.json` and `pipeline/data/raw/ucl_history_20261020/`.

Club and opponent aliases were reconciled in this isolated candidate. Contradictory results are rejected, fixture duplicates removed, and the one-senior-fixture-per-club-per-day check passed. Those checks establish internal consistency, not independent verification of every source row. Labels stop before 20 October; live features use the pre-match causal feature contract.

## Calibration and independent test

Training, tuning, calibration fitting, calibration selection and testing were separated chronologically. Unchanged logistic probabilities beat sigmoid and isotonic alternatives on the calibration selection block for both market and history experts, so the final candidate retains those probabilities. This is a calibration review, not a claim that adding a calibration transform always improves predictions.

On 3,522 held-out fixtures (21 November 2025 through 19 October 2026): accuracy **52.75%**, log loss **0.979966**, multiclass Brier score **0.583829**; zero boundary probabilities. On the same 2,608 fixtures with odds, model log loss was **0.973391**, versus market **0.973767**. The 95% fixture-day bootstrap interval for model-minus-market log loss was **[-0.003281, +0.002485]**, which includes zero. There is no demonstrated advantage over market probabilities. These are broad historical tests, not a dedicated Champions League-only profitability backtest, and do not account for realized betting costs.

The old model's zero Slovan-win and PSG-draw probabilities were reproduced through its isotonic calibrators. New candidate output was not repaired by arbitrary probability clipping. Saved model/data hashes, reload predictions, chronological separation and saved test metrics were independently checked. Seven new checks and 26 existing model/identity/form tests passed (33 total). The repository-wide Fallow audit remains failing in a working tree with hundreds of other changes; it also scans captured HTML and does not validate Python modeling logic. It is not a clean repository gate.

## Late-fixture forecasts

Snapshot: **{forecast['generated_at']}** (UTC; add three hours for Kampala). Home/draw/away refer to regulation time. “Recent” means stored quote age at most 30 minutes, not an independent check that a bookmaker will accept the price. Stuttgart–Atlético has no recent stored quote and uses the history expert.

| Fixture | Home | Draw | Away | Inputs |
|---|---:|---:|---:|---|
{chr(10).join(table)}

The two early fixtures are omitted from this pre-match table because they had already started. Full probabilities, feature vectors, timestamps, bookmaker quotes and theoretical fair prices are retained in `ucl-reviewed-forecasts-20261020.json`.

## Price arithmetic and decision

{arb_text or 'No negative reciprocal-sum combination was found among the recent stored 1X2 prices.'}

These are **nominal quote combinations, not verified executable arbitrage**. Bookmaker availability, consistent settlement rules, limits, taxes, commissions and simultaneous acceptance were not verified. Exact quoted legs and equal-payout allocations are in `ucl-final-price-audit-20261020.json`. No bet was placed.

The largest positive model EV among the recent stored prices is the Liverpool–Villarreal draw at 5.04 (model probability 22.29%, gross theoretical EV +12.35%). Napoli at 1.75 is +8.04%, and Porto at 1.57 is +6.78%. These estimates inherit the model's uncertainty and incomplete competition history; they are review candidates, not established edges. No stake or accumulator recommendation is justified by this validation.

Remaining work before promotion: complete and verify missing competition coverage, evaluate Champions League and relevant club/league subgroups with adequate samples, and run a forward paper trial using executable prices and net returns. No statistic can ensure a winning wager.
'''
(OUT/'ucl-final-review-20261020.md').write_text(report,encoding='utf-8')
print(json.dumps(audit,indent=2))

