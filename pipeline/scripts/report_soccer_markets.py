"""Render the immutable soccer analysis into reviewable Markdown and CSV."""
import argparse
import csv
import json
from pathlib import Path


def render(directory):
    report = json.loads((directory/'analysis.json').read_text(encoding='utf-8'))
    fixtures = report['fixtures']
    qualified = [(f, p) for f in fixtures for p in f.get('best_prices', []) if p['qualifies']]
    lines = [f"# Soccer market analysis — {report['date_eat']} (East Africa Time)", '',
        f"Generated {report['generated_at']}. All prices are observed quotes, not accepted bets.", '',
        f"Coverage: {len(fixtures)} official upcoming fixtures; {sum(f['model_status']=='forecast' for f in fixtures)} forecasts; "
        f"{sum(f['simulation']['runs'] for f in fixtures if 'simulation' in f):,} simulated score pairs.", '',
        f"Screen-passing candidates: {len(qualified)}. Positive quote-level arbitrages: "
        f"{sum(f.get('quote_level_arbitrage_roi', -1)>0 for f in fixtures)}.", '',
        '## Screen-passing candidates', '',
        'These pass a research screen; they have not demonstrated a profitable strategy. Confirm the ordinary 90-minute market and executable price before acting.', '']
    for f, p in qualified:
        alternatives = ', '.join(f"{q['bookmaker']} {q['prices'][p['outcome']]:.2f}" for q in f['quotes'] if q['bookmaker']!=p['bookmaker'])
        lines.extend([f"- {f['home_team']} – {f['away_team']} ({f['kickoff_eat']}): **{p['outcome']} {p['odds']:.2f}, {p['bookmaker']}**; "
            f"other books: {alternatives}. Model {p['model_probability']:.1%}, simulation {p['simulation_probability']:.1%}, "
            f"other-book normalized consensus {p['leave_one_book_out_probability']:.1%}. "
            f"Point EV: model {p['model_ev']:+.1%}, simulation {p['simulation_ev']:+.1%}, consensus {p['consensus_ev']:+.1%}. "
            f"Stressed EV: model {p['model_stress_ev']:+.1%}, simulation {p['simulation_stress_ev']:+.1%}. "
            f"Quote observed {p['observed_at']}."])
    lines.extend(['', '## All fixtures', '',
        'H/D/A probabilities below are percentages. The displayed outcome maximizes the smaller of model and simulation EV; it is not automatically a recommendation.', '',
        '| Kickoff EAT | Fixture | Model H/D/A | Simulation H/D/A | Candidate quote | Screen |',
        '|---|---|---|---|---|---|'])
    csv_rows = []
    for f in fixtures:
        if f['model_status']!='forecast':
            lines.append(f"| {f['kickoff_eat'][11:16]} | {f['home_team']} – {f['away_team']} | unavailable | unavailable | — | {f['model_status']} |")
            continue
        probs = lambda x: '/'.join(f"{100*x[k]:.1f}" for k in ['home_win','draw','away_win'])
        best = max(f['best_prices'], key=lambda p:min(p['model_ev'],p['simulation_ev']), default=None)
        quote = f"{best['outcome']} {best['odds']:.2f} {best['bookmaker']}" if best else 'No eligible prices'
        lines.append(f"| {f['kickoff_eat'][11:16]} | {f['home_team']} – {f['away_team']} | {probs(f['probabilities'])} | {probs(f['simulation']['probabilities'])} | {quote} | {'Passes screen' if best and best['qualifies'] else 'No selection'} |")
        for p in f['best_prices']:
            minimum = max(1.05/p['model_probability'], 1.05/p['simulation_probability'],
                1/(max(1e-12,p['model_probability']-.05)*.98),
                1/(f['simulation']['rate_stress_min_probability'][p['outcome']]*.98),
                1/p['leave_one_book_out_probability'] if p['leave_one_book_out_probability'] else 0)
            csv_rows.append(dict(competition=f['competition'], home=f['home_team'], away=f['away_team'],
                kickoff_eat=f['kickoff_eat'], books=f['eligible_book_count'], **p,
                minimum_price_for_numeric_screen=minimum,
                expected_home_goals=f['simulation']['goal_rates'][0], expected_away_goals=f['simulation']['goal_rates'][1],
                over_2_5_probability=f['simulation']['over_2_5'], btts_probability=f['simulation']['btts'],
                most_likely_score=f['simulation']['top_scores'][0]['score']))
    with (directory/'markets.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = list(csv_rows[0]) if csv_rows else ['competition', 'home', 'away', 'kickoff_eat', 'outcome', 'odds']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    books = sorted({q['bookmaker'] for fixture in fixtures for q in fixture.get('quotes', [])})
    quoted = sum(bool(fixture.get('quotes')) for fixture in fixtures)
    policy = report.get('policy', {})
    lines.extend(['', '## Methods, limits and provenance', '',
        '- Ordinary full-time 90-minute 1X2 only. Identity and exact kickoff must match the official fixture.',
        f'- Eligible bookmaker coverage: {", ".join(books) or "none"}. {quoted} of {len(fixtures)} fixtures have matched eligible quotes.',
        f'- Maximum quote age at analysis: {policy.get("max_quote_age_seconds", "unspecified")} seconds. Cached, incomplete and unmatched prices are excluded by the analysis.',
        '- League classifiers and historical-score Poisson simulations use historical results. Their shared inputs do not provide independent confirmation of an edge.',
        '- Model, source, identity and history hashes, actual simulation draw counts, policy thresholds and exclusions are recorded in analysis.json.',
        '- No numerical lineup, injury or fatigue adjustment is inferred. Confirmed starting lineups were not verified.',
        '- Totals and BTTS values are forecasts without collected matching market prices.',
        '- Actual fees, taxes, limits, liquidity and account eligibility were not verified. No wagers, database writes or model promotion.',
        f"- Capture: `{report['capture']}`; SHA-256 `{report['capture_sha256']}`. Form: `{report['form_capture']}`; history SHA-256 `{report['form_sha256']}`.",
        f"- Exclusions: `{json.dumps(report['exclusions'])}`.",
        '- Coverage is limited to supported competitions and the supplied captures. An empty report is not evidence that no opportunities exist.',
        '- Positive estimated EV or a research-screen pass does not establish prospective profitability.',
        '', '## Reproduction', '',
        'Use the supplied capture and form paths with scripts.analyze_soccer_markets, then render the new output with scripts.report_soccer_markets.',
        'See docs/UNATTENDED_PIPELINE.md. Refreshing captures requires network access and can consume provider credits.'])
    (directory/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'fixtures':len(fixtures),'qualified':len(qualified),'csv_rows':len(csv_rows),'report':str(directory/'report.md')}))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory',type=Path)
    render(parser.parse_args().directory)
