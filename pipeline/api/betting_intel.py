"""Pure, sport-scoped intelligence from timestamped, complete market snapshots."""
from collections import defaultdict
from datetime import datetime, timezone
import math

from api.odds_math import expected_value, implied_probability_from_decimal

SPORTS = {
    'football': {'label': 'Football', 'model_sport': 'football', 'league': None, 'rule': 'REGULATION_1X2'},
    'nba': {'label': 'NBA', 'model_sport': 'basketball', 'league': 'basketball_nba', 'rule': 'INCLUDING_OVERTIME'},
    'nfl': {'label': 'NFL', 'model_sport': 'nfl', 'league': 'americanfootball_nfl', 'rule': 'TIE_PUSH'},
    'wnba': {'label': 'WNBA', 'model_sport': 'wnba', 'league': 'basketball_wnba', 'rule': 'INCLUDING_OVERTIME'},
    'ncaab': {'label': 'NCAAB', 'model_sport': 'ncaab', 'league': 'basketball_ncaab', 'rule': 'INCLUDING_OVERTIME'},
    'college-football': {'label': 'College Football', 'model_sport': 'ncaaf', 'league': 'americanfootball_ncaaf', 'rule': 'INCLUDING_OVERTIME'},
}
SECTIONS = ('ai_picks', 'predictions', 'devigged_odds', 'ev_bets', 'player_props', 'arbitrage')
MAX_QUOTE_AGE = 1800
MAX_QUOTE_SKEW = 120
MAX_PREDICTION_AGE = 86400


def timestamp(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.astimezone(timezone.utc) if value.tzinfo else None


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def sport_key(sport, league):
    """League takes precedence: NBA must never include WNBA or college games."""
    league = str(league or '').strip().lower()
    aliases = {'nba': 'nba', 'basketball_nba': 'nba', 'wnba': 'wnba', 'basketball_wnba': 'wnba',
               'ncaab': 'ncaab', 'basketball_ncaab': 'ncaab', 'ncaa basketball': 'ncaab',
               'nfl': 'nfl', 'americanfootball_nfl': 'nfl', 'ncaaf': 'college-football',
               'americanfootball_ncaaf': 'college-football', 'college football': 'college-football'}
    if league in aliases:
        return aliases[league]
    if str(sport).lower() in ('soccer', 'football') and league not in ('nfl', 'ncaaf'):
        return 'football'
    return None


def prediction_for(fixture, outcomes, now):
    prediction = fixture.get('prediction') or {}
    probabilities = prediction.get('probabilities') or {}
    created = timestamp(prediction.get('generated_at'))
    kickoff = timestamp(fixture['kickoff'])
    values = [finite(probabilities.get(key)) for key in outcomes]
    if (set(probabilities) != set(outcomes) or any(p is None or not 0 < p < 1 for p in values)
            or abs(sum(values)-1) > 1e-6 or created is None or created >= kickoff
            or not 0 <= (now-created).total_seconds() <= MAX_PREDICTION_AGE
            or prediction.get('settlement_rule') != fixture['settlement_rule']
            or prediction.get('probability_basis') == 'CONDITIONAL_ON_DECISIVE_RESULT'):
        return None
    return {**prediction, 'probabilities': dict(zip(outcomes, values))}


def complete_books(offers, outcomes, kickoff, now):
    latest = {}
    for offer in offers:
        observed = timestamp(offer.get('observed_at'))
        selection, book = offer.get('selection'), str(offer.get('bookmaker') or '').strip()
        if not book or selection not in outcomes or observed is None or observed > now:
            continue
        key = (book, selection)
        if key not in latest or observed > timestamp(latest[key]['observed_at']):
            latest[key] = {**offer, 'decimal_odds': finite(offer.get('decimal_odds')), 'observed_at': observed.isoformat()}
        elif observed == timestamp(latest[key]['observed_at']) and finite(offer.get('decimal_odds')) != latest[key]['decimal_odds']:
            # Conflicting same-time evidence invalidates this selection rather than choosing a convenient price.
            latest[key]['decimal_odds'] = None
    books = []
    for book in sorted({key[0] for key in latest}):
        legs = {key: latest[(book, key)] for key in outcomes if (book, key) in latest}
        if len(legs) != len(outcomes):
            continue
        times = [timestamp(leg['observed_at']) for leg in legs.values()]
        if any(leg['decimal_odds'] is None or leg['decimal_odds'] <= 1 for leg in legs.values()):
            continue
        if any(t >= kickoff or not 0 <= (now-t).total_seconds() <= MAX_QUOTE_AGE for t in times):
            continue
        if (max(times)-min(times)).total_seconds() > MAX_QUOTE_SKEW:
            continue
        implied = {key: implied_probability_from_decimal(leg['decimal_odds']) for key, leg in legs.items()}
        total = sum(implied.values())
        books.append({'bookmaker': book, 'legs': legs, 'fair_probabilities': {key: p/total for key,p in implied.items()},
                      'overround': total-1})
    return books


def analyze_market(fixture, market, offers, now, prediction=None):
    outcomes = ('home_win', 'draw', 'away_win') if market['market'] == 'h2h' and fixture['sport'] == 'football' else (
        ('home_win', 'away_win') if market['market'] == 'h2h' else ('over', 'under'))
    kickoff = timestamp(fixture['kickoff'])
    books = complete_books(offers, outcomes, kickoff, now)
    push_possible = fixture['settlement_rule'] == 'TIE_PUSH' or (
        market['market'] != 'h2h' and float(market['line']).is_integer())
    base = {key: fixture[key] for key in ('fixture_id','sport','competition','home_team','away_team','kickoff','settlement_rule')}
    base.update(market)
    devig, ev, arbs = [], [], []
    for book in books:
        devig.append({**base, **book, 'probability_basis': 'bookmaker_multiplicative_devig',
                      'push_probability_unmodeled': push_possible})
        if push_possible:
            continue
        others = [b for b in books if b['bookmaker'] != book['bookmaker']]
        reference = prediction['probabilities'] if prediction else (
            {key: sum(b['fair_probabilities'][key] for b in others)/len(others) for key in outcomes} if len(others) >= 2 else None)
        if reference is None:
            continue
        for selection, leg in book['legs'].items():
            estimate = expected_value(reference[selection], leg['decimal_odds'], 1)['expected_value_pct']
            if estimate > 0:
                ev.append({**base, **leg, 'probability': reference[selection], 'ev_pct': estimate,
                           'probability_basis': 'model' if prediction else 'other_book_consensus',
                           'model_version': prediction.get('model_version') if prediction else None,
                           'model_status': prediction.get('status') if prediction else None,
                           'generated_at': prediction.get('generated_at') if prediction else None,
                           'reference_books': [b['bookmaker'] for b in others] if not prediction else [],
                           'costs_included': False})
    if books and not push_possible:
        best = {key: max((book['legs'][key] for book in books), key=lambda leg: leg['decimal_odds']) for key in outcomes}
        inv = sum(1/leg['decimal_odds'] for leg in best.values())
        times = [timestamp(leg['observed_at']) for leg in best.values()]
        if inv < 1 and len({leg['bookmaker'] for leg in best.values()}) > 1 and (max(times)-min(times)).total_seconds() <= MAX_QUOTE_SKEW:
            arbs.append({**base, 'reciprocal_sum': inv, 'gross_roi': 1/inv-1, 'execution_verified': False,
                         'legs': [{**leg, 'reference_stake': 100/(leg['decimal_odds']*inv)} for leg in best.values()],
                         'reference_total_stake': 100, 'costs_included': False})
    return devig, ev, arbs


def build_intelligence(sport, fixtures, now=None):
    if sport not in SPORTS:
        raise ValueError('Unsupported sport')
    now = now or datetime.now(timezone.utc)
    output = {key: [] for key in SECTIONS}
    considered = 0
    for fixture in fixtures:
        kickoff = timestamp(fixture.get('kickoff'))
        if fixture.get('sport') != sport or kickoff is None or kickoff <= now or str(fixture.get('status','')).upper() in (
                'LIVE','IN_PLAY','PAUSED','FINISHED','COMPLETED','CANCELLED','CANCELED','POSTPONED'):
            continue
        considered += 1
        fixture = {**fixture, 'kickoff': kickoff.isoformat()}
        outcomes = ('home_win','draw','away_win') if sport == 'football' else ('home_win','away_win')
        prediction = prediction_for(fixture, outcomes, now)
        if prediction:
            output['predictions'].append({**prediction, **{key: fixture[key] for key in ('fixture_id','sport','competition','home_team','away_team','kickoff','settlement_rule')}})
        groups = defaultdict(list)
        for offer in fixture.get('offers', []):
            market = offer.get('market')
            if market == 'h2h':
                groups[(market, '', None)].append(offer)
            elif str(market).startswith('player_') and offer.get('participant') and finite(offer.get('line')) is not None:
                # Never pair different players, thresholds, periods or market types.
                groups[(market, offer['participant'], float(offer['line']))].append(offer)
        fixture_ev = []
        for (market, player, line), offers in groups.items():
            devig, ev, arbs = analyze_market(fixture, {'market':market,'player':player or None,'line':line}, offers, now,
                                            prediction if market == 'h2h' else None)
            output['devigged_odds'].extend(devig)
            output['ev_bets'].extend(ev)
            output['arbitrage'].extend(arbs)
            if market != 'h2h':
                output['player_props'].extend(devig)
            else:
                fixture_ev.extend(row for row in ev if row['probability_basis'] == 'model')
        if prediction:
            best = max(fixture_ev, key=lambda row: row['ev_pct'], default=None)
            winner = max(prediction['probabilities'], key=prediction['probabilities'].get)
            output['ai_picks'].append({**output['predictions'][-1], 'selection': best['selection'] if best else winner,
                                      'probability': best['probability'] if best else prediction['probabilities'][winner],
                                      'decimal_odds': best['decimal_odds'] if best else None,
                                      'bookmaker': best['bookmaker'] if best else None,
                                      'ev_pct': best['ev_pct'] if best else None,
                                      'pick_type': 'model_value' if best else 'most_likely'})
    output['ev_bets'].sort(key=lambda row: row['ev_pct'], reverse=True)
    output['arbitrage'].sort(key=lambda row: row['gross_roi'], reverse=True)
    output['ai_picks'].sort(key=lambda row: (row['ev_pct'] is not None, row['ev_pct'] or row['probability']), reverse=True)
    return {'sport': sport, 'label': SPORTS[sport]['label'], 'generated_at': now.isoformat(),
            'summary': {'fixtures': considered, **{key:len(output[key]) for key in SECTIONS}}, **output,
            'policy': {'quote_max_age_seconds': MAX_QUOTE_AGE, 'quote_max_skew_seconds': MAX_QUOTE_SKEW,
                       'prediction_max_age_seconds': MAX_PREDICTION_AGE, 'execution_verified': False,
                       'ev_is_gross_estimate': True, 'consensus_excludes_target_book': True}}
