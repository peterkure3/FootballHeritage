"""Render the reviewed analysis with explicit availability and model limits."""
import json
from pathlib import Path
OUT=Path(__file__).parent;ROOT=OUT.parents[2]
r=json.loads((OUT/'ucl-analysis-20261021.json').read_text())
lines=['# Champions League betting review — 21 October 2026','',
'Prices observed 14:36:12–14:36:14 UTC (17:36 Kampala). Kickoffs are 19:45 Kampala for Como–Manchester United and Lille–Galatasaray; 22:00 for the other seven games. Markets: full-time regulation 1X2, including stoppage time.',
'','## Findings','',
'No confirmed arbitrage. Across the 26 usable complete book/fixture markets, the best combined reciprocal sums range from 1.007054 to 1.016501. All exceed 1; the closest combination still loses about 0.70% before costs. No bets placed.',
'',
'The leading experimental value candidates are Bayern to win at 2.28 and Lille to win at 2.26, both Ababet. Bayern is conditional because Olise is suspended and the model has no player-availability features. Lille is a price-based candidate despite mixed recent results. Real Madrid at 1.27 is a stronger likely-winner selection, with a thin estimated edge. These are tentative singles, not validated profitable recommendations.',
'','## Coverage and validation','',
'The catalog contains 46 brands: 40 had configured URLs, 9 produced normalized football markets, and 8 had quotes for today’s UCL fixtures. SportPesa returned another competition. Five UCL sources explicitly marked markets OPEN. A second capture retained betPawa, Cloudbet and Ababet. Bovada was excluded because its HTTP Age was 554 seconds; Bookmaker’s page was last modified more than seven minutes before retrieval and is omitted conservatively. BetOnline, 1xbet and 22bet had unconfirmed market status. Other brands were inaccessible, unresolved or lacked a verified parser; coverage is not exhaustive.',
'',
'Fixtures were matched by reviewed senior-team aliases, UTC kickoff within 60 seconds, regulation-time market and home/away orientation. Reversed provider listings were reoriented. Open outcome status, finite prices above 1, probability normalization, model/dataset checksums, pre-match history cutoffs and score conflicts were checked. A supplementary archive request for Viking failed; available verified Norwegian league results and European results cover its displayed form.',
'',
'Cross-source duplicate matches under opponent aliases were removed before the final inference. The resulting causal history has '+str(r['history_rows'])+' rows. Form means the latest five available domestic-league and regulation European results; cup coverage is incomplete. Training history for LASK, Shakhtar and Brugge is much thinner than for major-league teams. This report does not claim all team history was collected.',
'',
'The frozen experimental v2.1.0 model uses the previously selected uncalibrated probabilities. Its prior holdout accuracy was 52.75%; on 2,608 matched-odds games, model log loss was 0.973391 versus market 0.973767. The day-block bootstrap interval for the difference included zero (-0.003281 to +0.002485). A market-beating edge is not established. This run updates causal inputs and local identity mappings; it does not retrain, replace production, or validate tonight’s future outcomes.',
'',
'Model SHA256: `'+r['model_sha256']+'`. Gross model EV = model probability × decimal odds − 1. It excludes tax, fees, limits, rejection and price movement. De-vig consensus is the equal-book mean of proportional margin removal; it is a benchmark rather than ground truth.',
'','## All matches','',
'Form is oldest to newest. The lean is the most likely model outcome, not an automatic bet. Prices are the best among retained sources.','',
'| Fixture | Home form (GF–GA) | Away form (GF–GA) | Model H / D / A | Best H / D / A | Reciprocal sum |',
'|---|---|---|---|---|---|']
for m in r['matches']:
    h=m['form'][m['home']];a=m['form'][m['away']]
    p=' / '.join(f"{100*m['probabilities'][c]:.1f}%" for c in ['home_win','draw','away_win'])
    prices=' / '.join(f"{m['best'][c]['odds']:.2f} ({m['best'][c]['bookmaker']})" for c in ['home_win','draw','away_win'])
    lines.append(f"| {m['home']} – {m['away']} | {h['sequence']} ({h['gf']}–{h['ga']}) | {a['sequence']} ({a['gf']}–{a['ga']}) | {p} | {prices} | {m['reciprocal_sum']:.6f} |")
lines+=['','## Candidate prices','', '| Selection | Decimal price | Model probability | Market de-vig probability | Break-even probability | Gross model EV |','|---|---|---|---|---|---|']
for home in ['Bayern Munich','Lille','Real Madrid','Sp Lisbon']:
    m=next(m for m in r['matches'] if m['home']==home);b=m['best']['home_win']
    lines.append(f"| {home} win | {b['odds']:.2f} {b['bookmaker']} | {m['probabilities']['home_win']:.1%} | {m['consensus']['home_win']:.1%} | {1/b['odds']:.1%} | {b['model_ev']:+.1%} |")
lines+=['','These probabilities are experimental point estimates. Lineups are not confirmed. No fabricated adjustment is applied for an absent player. Sporting is an alternative likely-winner lean, but sparse LASK history and reported Sporting absences reduce confidence. Inter faces a Shakhtar side with five available consecutive wins. Betis faces a Feyenoord side with five available consecutive wins; avoid treating either favorite as a safe addition. Manchester United are winless in the displayed five, and the model does not support buying their current win price.','',
'## Sources and evidence','',
'- [UEFA fixtures/results](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--202627-champions-league-all-the-league-phase-fixtures-and-results/)',
'- [Bayern official Viking match reaction: 3–3, not 3–4](https://fcbayern.com/en/news/2026/10/reaction-to-champions-league-match-at-viking-fk)',
'- [Real Madrid official squad](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/convocatorias/convocatoria-del-real-madrid-contra-el-leipzig-20-10-2026)',
'- [Lille official opponent preview](https://losc.fr/actualites/2026-10-20/la-decouverte-de-galatasaray)',
'- [Villa official team news](https://www.avfc.co.uk/news/2026/october/20/prematch-team-news-for-viking-visit/)',
'- [Olise suspension report](https://fcbinside.com/2026/10/20/gnabry-karl-or-saibari-heres-how-bayern-will-solve-the-olise-problem-against-arsenal/)',
'- Public prices: [Ababet](https://ababet.ug/), [betPawa Uganda](https://www.betpawa.ug/), [Cloudbet UCL](https://www.cloudbet.com/en/sports/soccer/international-clubs-uefa-champions-league?tab=events). Public price visibility does not establish account access or stake acceptance.',
'- Machine-readable review: `ucl-analysis-20261021.json`; odds captures and cache audit: `pipeline/data/raw/ucl_today_20261021_recheck/`; first catalog capture: `pipeline/data/raw/ucl_today_20261021_all_public/`; provider form: `pipeline/data/raw/team_form/ucl_20261021/`; supplementary archives: `pipeline/data/raw/ucl_today_20261021_form/`.','']
(OUT/'ucl-betting-review-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
assert len(r['matches'])==9 and all(m['reciprocal_sum']>1 for m in r['matches'])
assert sum(len(m['quotes']) for m in r['matches'])==26
assert all(q['bookmaker'] in {'ababet','betpawa','cloudbet'} for m in r['matches'] for q in m['quotes'])
print('Report saved; 9 fixtures, 26 usable complete markets, no arbitrage. All report invariants passed.')
