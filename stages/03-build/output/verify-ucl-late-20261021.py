"""Independently reproduce saved inference and arithmetic, then write the review."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from models.features import FEATURE_NAMES

report_path = OUT / 'ucl-late-scrapling-check-20261021.json'
report = json.loads(report_path.read_text())
directory = ROOT / 'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020'
model = joblib.load(directory / 'model_v2.1.0.pkl')
encoder = joblib.load(directory / 'label_encoder_v2.1.0.pkl')
assert list(model.classes_) == [0, 1, 2]
classes = list(encoder.inverse_transform(model.classes_))
assert classes == ['away_win', 'draw', 'home_win']
matches = report['matches']
with threadpool_limits(limits=2):
    reproduced = model.predict_proba(pd.DataFrame([r['features'] for r in matches], columns=FEATURE_NAMES))
checks = {'model_class_order': True, 'probability_vectors': 0, 'value_calculations': 0, 'best_prices': 0, 'devig_vectors': 0, 'arbitrage_calculations': 0, 'complete_book_quotes': 0}
for row, predicted in zip(matches, reproduced):
    assert np.allclose(predicted, [row['probabilities'][c] for c in classes], rtol=0, atol=1e-12)
    assert np.isclose(sum(predicted), 1) and all(0 < p < 1 for p in predicted)
    checks['probability_vectors'] += 1
    assert pd.Timestamp(row['kickoff']) > pd.Timestamp(report['generated_at'])
    for quote in row['quotes']:
        assert set(quote['prices']) == set(classes) and all(v > 1 for v in quote['prices'].values())
        checks['complete_book_quotes'] += 1
    devig = np.mean([[1 / q['prices'][c] / sum(1 / v for v in q['prices'].values()) for c in classes] for q in row['quotes']], axis=0)
    assert np.allclose(devig, [row['consensus'][c] for c in classes], rtol=0, atol=1e-12)
    checks['devig_vectors'] += 1
    for c in classes:
        best = row['best'][c]
        assert best['odds'] == max(q['prices'][c] for q in row['quotes'])
        assert any(q['bookmaker'] == best['bookmaker'] and q['prices'][c] == best['odds'] for q in row['quotes'])
        checks['best_prices'] += 1
        assert abs(row['probabilities'][c] * best['odds'] - 1 - best['ev']) < 1e-12
        assert abs(1 / row['probabilities'][c] - best['fair_odds']) < 1e-12
        checks['value_calculations'] += 1
    reciprocal = sum(1 / row['best'][c]['odds'] for c in classes)
    assert abs(reciprocal - row['reciprocal_sum']) < 1e-12
    assert abs(1 / reciprocal - 1 - row['nominal_arb_roi']) < 1e-12
    checks['arbitrage_calculations'] += 1
assert len(matches) == 7 and len(report['excluded']) == 2
summary = {'generated_at': datetime.now(timezone.utc).isoformat(), 'all_checks_passed': True, 'checks': checks, 'artifact_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(), 'arbitrage_opportunities': sum(r['reciprocal_sum'] < 1 for r in matches), 'predictive_success_verified': False}
(OUT / 'ucl-late-scrapling-verification-20261021.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
labels = {'Sp Lisbon': 'Sporting CP', 'Betis': 'Real Betis', 'LASK Linz': 'LASK', 'Bayern Munich': 'Bayern'}
def label(team):
    return labels.get(team, team)
lines = [
    '# UCL public sportsbook and form review — 21 October 2026', '',
    'Public prices captured with Scrapling at 17:24:24–17:24:38 UTC (20:24 Kampala). All seven remaining games kick off at 19:00 UTC / 22:00 Kampala. These are captured public offers; account acceptance, limits and final bet-slip prices were not verified.', '',
    '## Finding', '',
    'No regulation-time 1X2 arbitrage among the accepted sources. Club Brugge, Sporting CP and Real Madrid are the main experimental watchlist. The model has no statistically established advantage over the market; no pick or combination ensures a win. Final starting lineups were not verified. No bet was placed.', '',
    '## Source checks', '',
    'Refreshed betPawa Uganda, Cloudbet, Ababet Uganda, Bovada and Bookmaker. Only the first three passed this review’s conservative freshness rules. Bovada returned upstream Age=952 seconds. Bookmaker’s page Last-Modified was 17:00:38 UTC; its exclusion is a conservative page-timestamp rule, not proof of when its individual odds changed. This is not an exhaustive claim about all public bookmakers.', '',
    'Accepted only complete, open, pre-match HOME/DRAW/AWAY markets, matched to the fixture and kickoff with regulation-time settlement. Como–Manchester United and Lille–Galatasaray were excluded because kickoff had passed.', '',
    '## Model and history', '',
    'Used the separately reviewed v2.1.0 research candidate, not the active site’s v2.0.0. Repriced its saved causal history features with new consensus prices; did not retrain, recalibrate or promote a model. Historical inputs contain 19,739 merged fixtures, including 2,757 usable regulation results from the expanded target-team history across the last three seasons plus the current season. Another 58 ambiguous regulation results were withheld. No results from tonight entered these historical features.', '',
    'Prior matched-odds holdout log loss: model 0.97339074 versus market 0.97376709. The bootstrap difference interval [-0.003281, +0.002485] includes zero. Positive estimated EV below is therefore a research signal, not a demonstrated profitable betting system. The model incorporates odds and team performance history but has no explicit player-availability features.', '',
    '## Remaining matches', '',
    'Form is the last five available competitive results, oldest to newest. Cross-league winning runs do not imply equal opponent strength.', '',
    '| Home / away | Home form / away form | Best home price | Model home chance | De-vig market home chance | Model gross EV |',
    '|---|---|---:|---:|---:|---:|',
]
for row in matches:
    home, away = row['home'], row['away']
    best = row['best']['home_win']
    lines.append(f"| {label(home)} / {label(away)} | {row['form'][home]['last_five']} / {row['form'][away]['last_five']} | {best['odds']:.2f} {best['bookmaker']} | {row['probabilities']['home_win']:.1%} | {row['consensus']['home_win']:.1%} | {best['ev']:+.1%} |")
lines += [
    '', 'EV = model probability × decimal odds − 1, before fees and taxes. De-vig market chance is the mean of each accepted book’s normalized implied probabilities.', '',
    '## Selection review', '',
    '- Club Brugge win at 1.94 Ababet: strongest combination of a sizeable model estimate and recent form (five wins). Lens recovered with a 3–1 win at Troyes after losing 0–2 to Sporting. Lens’s official preview confirms Brugge’s 4–3 win at Inter but also notes Brugge conceded at least three in four of its previous five home Champions League games. This remains a material risk.',
    '- Sporting CP win at 1.37 Ababet: unbeaten in the last five available results (WDDWW), compared with LASK’s LDLLW. The estimate fell from roughly 82% in the earlier price review to 78% as the market moved. Do not treat a better offered price alone as evidence of better underlying prospects.',
    '- Real Madrid win at 1.27 Ababet: four wins from five, while Leipzig’s latest result was a 1–6 defeat to Bayern. Real’s announced squad includes Mbappe, Vinicius and Bellingham; this is squad availability, not a verified starting XI. The estimated margin is smaller than Brugge’s and Sporting’s.',
    '- Aston Villa win at 1.31 and Inter win at 1.27, both Ababet: secondary signals. Viking are unbeaten in five available results and held Bayern 3–3; Shakhtar have five consecutive wins. Those opponent runs temper confidence.',
    '- Bayern win at 2.28 Ababet: hold despite approximately +13.4% raw model EV. Bayern officially confirms Olise suspended and Musiala unavailable; the model has no explicit features for these absences. Neuer’s participation was still a match-day decision in the official preview.',
    '- Real Betis home win at 1.68: pass; model EV is negative. The Betis–Feyenoord draw at 4.76 Ababet shows approximately +17.7% model EV but only a 24.7% estimated chance; retain as a speculative research signal, not a main selection.', '',
    '## Arbitrage', '',
    '| Match | Sum of best inverse odds | Theoretical equal-return ROI |',
    '|---|---:|---:|',
]
for row in matches:
    lines.append(f"| {label(row['home'])} / {label(row['away'])} | {row['reciprocal_sum']:.6f} | {row['nominal_arb_roi']:+.3%} |")
lines += [
    '', 'Every reciprocal sum exceeds 1, so there is no nominal arbitrage in these captured prices. Fees, limits, price changes and settlement mismatches could only make execution harder.', '',
    '## Evidence and verification', '',
    f"Source capture: `{report['capture']}`. Machine output: `ucl-late-scrapling-check-20261021.json`. Independent replay: `ucl-late-scrapling-verification-20261021.json`.", '',
    'Verified model class order, reproduced all seven probability vectors, checked all 21 best-price and EV calculations, recomputed seven de-vig vectors and seven arbitrage calculations, and checked 21 complete bookmaker quotes. These checks validate the calculations and retained inputs, not future match outcomes.', '',
    '- [RC Lens official match preview](https://www.rclens.fr/fr/club-brugge-kv-rclens)',
    '- [Bayern official availability and match preview](https://fcbayern.com/es/noticias/matchpreviews/2026/10/previa-champions-league-fc-bayern-fc-arsenal)',
    '- [Real Madrid official squad](https://www.realmadrid.com/en-US/news/football/first-team/squad-call/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)',
    '- [Ababet public page](https://ababet.ug/)',
    '- [betPawa Uganda](https://www.betpawa.ug/)',
    '- [Cloudbet Champions League](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events)', '',
]
(OUT / 'ucl-late-scrapling-check-20261021.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps(summary))
