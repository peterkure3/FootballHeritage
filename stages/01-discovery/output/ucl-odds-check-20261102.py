"""Reproducible read-only analysis of two public UCL 90-minute 1X2 captures."""
import collections
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
from football_competitions import canonical_competition
from models.league_data import identity, identity_aliases

BASE = ROOT / 'pipeline/data/raw/sportsbooks'
OUT = Path(__file__).parent / 'ucl-odds-20261102'
OUT.mkdir(exist_ok=True)
ALIASES = identity_aliases()
SIDES = ['HOME', 'DRAW', 'AWAY']
REVIEWED = {
    'fc shakhtar donetsk': 'shakhtar donetsk', 'sporting lisbon': 'sp lisbon',
    'sporting lisboa': 'sp lisbon', 'galatasaray istanbul': 'galatasaray',
    'galatasaray a\u015f': 'galatasaray', 'inter': 'inter milan',
    'internazionale milano': 'inter milan', 'sk slovan bratislava': 'slovan bratislava',
    'bodoe/glimt': 'bod\u00f8/glimt', 'bodo-glimt': 'bod\u00f8/glimt',
    'fenerbahce istanbul': 'fenerbahce', 'viking': 'viking fk',
    'sabah baku': 'sabah fk', 'rc lens': 'lens',
    'rasenballsport leipzig': 'rb leipzig', 'paris saint germain': 'paris sg',
}


def team(name):
    value = identity(name, ALIASES)
    return REVIEWED.get(value, value)


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def load(number):
    folder = BASE / f'ucl_discrepancies_20261102_round{number}'
    report = json.loads((folder / 'source_report.json').read_text())
    groups = collections.defaultdict(dict)
    rejected = []
    for line in (folder / 'odds_snapshots.jsonl').read_text().splitlines():
        row = json.loads(line)
        if canonical_competition(row['competition'], row.get('country')) != 'UEFA Champions League':
            continue
        key = (team(row['home_team']), team(row['away_team']),
               instant(row['commence_time']).isoformat())
        source = next(s for s in report['direct_sources'] if s['bookmaker'] == row['bookmaker'])
        audits = source.get('http_audit', [])
        headers = audits[-1]['headers'] if audits else {}
        # Observation time is a fetch timestamp, not proof the quote just updated.
        reason = None
        if row['bookmaker'] == 'betonlineag':
            reason = 'home_away_order_reversed_against_three_other_feeds_requires_adapter_review'
        elif row['period'] != 'FULL_TIME_90_MIN' or row['settlement_rule'] != 'REGULATION_TIME' or row['is_live']:
            reason = 'market_mismatch'
        elif float(headers.get('Age') or 0) > 120:
            reason = 'cached_response_age'
        elif row.get('source_updated_at') and (instant(row['observed_at']) - instant(row['source_updated_at'])).total_seconds() > 900:
            reason = 'source_update_over_15_minutes_old'
        if reason:
            rejected.append({'bookmaker': row['bookmaker'], 'fixture': key, 'reason': reason})
            continue
        if row['bookmaker'] in groups[key]:
            raise ValueError(f'Duplicate fixture market: {key} {row["bookmaker"]}')
        row['prices'] = {o['selection']: o['odds_decimal'] for o in row['outcomes']}
        assert set(row['prices']) == set(SIDES)
        groups[key][row['bookmaker']] = row
    return groups, report, rejected


def analyze():
    first, first_report, rejected1 = load(1)
    second, second_report, rejected2 = load(2)
    comparisons, changes, lag_candidates, arbs = [], [], [], []
    for key, books in second.items():
        if len(books) < 3:
            continue
        times = [instant(r['observed_at']) for r in books.values()]
        if (max(times) - min(times)).total_seconds() > 120:
            continue
        old = first.get(key, {})
        for book, row in books.items():
            if book not in old:
                continue
            for side in SIDES:
                before, after = old[book]['prices'][side], row['prices'][side]
                if before != after:
                    changes.append({'fixture': key, 'bookmaker': book, 'selection': side,
                                    'before': before, 'after': after, 'change_pct': (after / before - 1) * 100})
        best = {side: max(books, key=lambda b: books[b]['prices'][side]) for side in SIDES}
        inverse = sum(1 / books[best[s]]['prices'][s] for s in SIDES)
        if inverse < 1:
            arbs.append({'fixture': key, 'gross_roi_pct': (1 / inverse - 1) * 100,
                         'legs': {s: {'bookmaker': best[s], 'odds': books[best[s]]['prices'][s]} for s in SIDES}})
        for side in SIDES:
            for book, row in books.items():
                peers = [r for b, r in books.items() if b != book]
                probabilities = [(1 / r['prices'][side]) / sum(1 / p for p in r['prices'].values()) for r in peers]
                probability = statistics.median(probabilities)
                price = row['prices'][side]
                item = {'fixture': key, 'bookmaker': book, 'selection': side, 'odds': price,
                        'peer_median_odds': statistics.median(r['prices'][side] for r in peers),
                        'peer_devig_probability': probability, 'consensus_gross_ev_pct': (probability * price - 1) * 100,
                        'peer_books': sorted(b for b in books if b != book),
                        'market_status': row['market_status'], 'observed_at': row['observed_at'],
                        'source_updated_at': row.get('source_updated_at'), 'source_url': row['source_url']}
                comparisons.append(item)
                # Two observed peers must shorten; this does not establish which book leads.
                movers = [b for b in ['cloudbet', '22bet', 'betpawa']
                          if b != book and b in books and b in old
                          and books[b]['prices'][side] / old[b]['prices'][side] <= 0.99]
                if book in old and price == old[book]['prices'][side] and len(movers) >= 2 and item['consensus_gross_ev_pct'] > 0:
                    lag_candidates.append(item | {'moving_references': movers})
    result = {'generated_at': datetime.now(timezone.utc).isoformat(),
              'first_capture': first_report['completed_at'], 'second_capture': second_report['completed_at'],
              'coverage_by_book': dict(collections.Counter(b for books in second.values() for b in books)),
              'fixture_count': len(second), 'comparisons': sorted(comparisons, key=lambda r: -r['consensus_gross_ev_pct']),
              'observed_changes': changes, 'lag_candidates': lag_candidates, 'gross_arbitrages': arbs,
              'excluded_quotes': rejected1 + rejected2,
              'limitations': ['Only full-time regulation 1X2, no handicap or totals line coverage.',
                  'Peer consensus is a reference estimate, not a calibrated true probability.',
                  'No tax, commission, limits, or betslip acceptance verification.',
                  'Reference operators are not assumed independent or proven market leaders.',
                  'Missing source timestamps mean quote freshness cannot be fully established.']}
    (OUT / 'comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    targets = json.loads((ROOT / '_config/bookmakers.json').read_text())
    targets['sportsbooks'] = [t for t in targets['sportsbooks'] if t['bookmaker'] in {'bookmaker', 'cloudbet', 'betonlineag', 'bovada', '22bet', 'betpawa'}]
    (OUT / 'targets.json').write_text(json.dumps(targets, indent=2), encoding='utf-8')
    assert len(second) == 18 and all(len(books) == 3 for books in second.values())
    assert len(comparisons) == 162
    print(json.dumps({k: v for k, v in result.items() if k not in {'comparisons', 'excluded_quotes'}}, indent=2))
    print('TOP_COMPARISONS', json.dumps(result['comparisons'][:6], indent=2))


if __name__ == '__main__':
    if '--prepare' in sys.argv:
        targets = json.loads((ROOT / '_config/bookmakers.json').read_text())
        targets['sportsbooks'] = [t for t in targets['sportsbooks'] if t['bookmaker'] in {'bookmaker', 'cloudbet', 'betonlineag', 'bovada', '22bet', 'betpawa'}]
        (OUT / 'targets.json').write_text(json.dumps(targets, indent=2), encoding='utf-8')
        groups, report, rejected = load(1)
        print('ROUND1', dict(collections.Counter(b for books in groups.values() for b in books)))
        print('EXCLUDED', rejected)
    else:
        if '--diagnostic' in sys.argv:
            groups, report, rejected = load(2)
            print(json.dumps([{'fixture': k, 'books': list(v)} for k, v in groups.items()], indent=2))
        else:
            analyze()
