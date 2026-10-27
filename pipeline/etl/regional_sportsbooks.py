"""Verified public football 1X2 adapters; reject live/incomplete markets."""
from datetime import datetime, timezone
import math
import json
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


def snapshot(book, event_id, home, away, kickoff, observed, raw_ref, run_id, prices,
             competition, country, market_id, source_url, updated=None, team_ids=None, region='UG'):
    instant = datetime.fromisoformat(observed.replace('Z', '+00:00'))
    if instant.tzinfo is None or kickoff.tzinfo is None or kickoff <= instant:
        return None
    if set(prices) != {'HOME', 'DRAW', 'AWAY'} or not home or not away or home == away:
        return None
    if any(not math.isfinite(float(p[0])) or float(p[0]) <= 1 for p in prices.values()):
        return None
    return {'schema_version': '1.0', 'snapshot_id': str(uuid4()), 'provider': 'scraper_' + book,
        'collection_route': 'direct_public_feed', 'bookmaker': book, 'region': region,
        'provider_event_id': str(event_id), 'provider_market_id': str(market_id),
        'provider_home_team_id': str(team_ids[0]) if team_ids else None,
        'provider_away_team_id': str(team_ids[1]) if team_ids else None,
        'home_team': home, 'away_team': away, 'sport': 'football',
        'competition': competition, 'country': country, 'commence_time': kickoff.astimezone(timezone.utc).isoformat(),
        'observed_at': observed, 'source_updated_at': updated, 'is_live': False,
        'event_status': 'SCHEDULED', 'market': 'h2h', 'period': 'FULL_TIME_90_MIN',
        'settlement_rule': 'REGULATION_TIME', 'market_status': 'OPEN',
        'outcomes': [{'selection': key, 'odds_decimal': float(prices[key][0]),
                      'provider_selection_id': str(prices[key][1]), 'status': 'OPEN',
                      'line': None, 'participant': None} for key in ['HOME','DRAW','AWAY']],
        'source_url': source_url, 'raw_capture_ref': raw_ref, 'scrape_run_id': run_id,
        'scraper_version': '1.0.0'}


def normalize_fortebet(payload, observed, raw_ref, run_id, source_url='https://www.fortebet.ug/api/web/v1/offer/full_offer'):
    if payload.get('status') != 'OK':
        return []
    data = payload['data']
    definition = data.get('market_list', {}).get('1', {}).get('1', {})
    if definition.get('name') != 'Full Time Result' or definition.get('template') != '3WAY':
        raise ValueError('Unverified Fortebet football market definition')
    if [definition.get('outcome', {}).get(str(i), {}).get('short') for i in [1,2,3]] != ['1','X','2']:
        raise ValueError('Unknown Fortebet selection ordering')
    records = []
    for market_id, market in data.get('markets', {}).items():
        if market.get('marketId') != 1 or market.get('marketStatusId') != 1:
            continue
        event = data['event'].get(market['eventId'], {})
        tournament = data['tournament'].get(str(event.get('tournamentId')), {})
        category = data['category'].get(str(tournament.get('categoryId')), {})
        if category.get('sportId') != 1 or event.get('eventStatusId') != 0:
            continue
        # liveodds means the event supports future live markets, not that it is live.
        # Prematch status, empty scoreboard and future start are all required.
        if event.get('results') or event.get('scoreboard', {}).get('status'):
            continue
        try:
            kickoff = datetime.fromisoformat(event['startTs'].replace('Z', '+00:00'))
            teams = event['competitors']
            home, away = [data['competitors'][str(t)]['name'] for t in teams]
            prices = {}
            for selection_id, offer in market['odds'].items():
                selection = {1: 'HOME', 2: 'DRAW', 3: 'AWAY'}.get(offer.get('outcomeId'))
                if selection:
                    if offer.get('locked') != 0 or selection in prices:
                        prices = {}; break
                    prices[selection] = (offer['odds'], selection_id)
            competition = tournament['name']
            # Verified UEFA tournament in the browser's published prematch directory.
            if str(event.get('tournamentId')) == 'TO7' and competition == 'Champions League' and category['name'] == 'International Clubs':
                competition = 'UEFA Champions League'
            row = snapshot('fortebet', market['eventId'], home, away, kickoff, observed, raw_ref, run_id,
                prices, competition, category['name'], market_id,
                source_url, payload.get('ts') or payload.get('last_update'), teams)
            if row:
                records.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    return records


def normalize_betika(payload, observed, raw_ref, run_id):
    """Uganda prematch 1X2 feed; its published dbTimezone is Africa/Accra (UTC)."""
    records = []
    for event in payload.get('data') or []:
        if (str(event.get('sport_id')) != '3' or event.get('sport_name') != 'Soccer'
            or event.get('is_esport') is not False or event.get('is_srl') is not False
            or event.get('is_live') or event.get('status') in {'LIVE', 'SUSPENDED', 'CLOSED'}):
            continue
        try:
            kickoff = datetime.fromisoformat(event['start_time'])
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            for market in event.get('odds', []):
                if str(market.get('sub_type_id')) != '1' or market.get('name') != '1X2':
                    continue
                prices = {}
                expected = {'1': event['home_team'], 'X': 'draw', '2': event['away_team']}
                for offer in market.get('odds', []):
                    label = offer.get('display')
                    selection = {'1': 'HOME', 'X': 'DRAW', '2': 'AWAY'}.get(label)
                    if (not selection or selection in prices or offer.get('special_bet_value')
                        or str(offer.get('odd_key', '')).casefold() != expected[label].casefold()
                        or offer.get('is_suspended') or offer.get('isActive') == 0):
                        prices = {}; break
                    prices[selection] = (offer['odd_value'], offer['outcome_id'])
                if any(key not in prices or not math.isclose(float(event[field]), float(prices[key][0]))
                       for key, field in [('HOME', 'home_odd'), ('DRAW', 'neutral_odd'), ('AWAY', 'away_odd')]):
                    continue
                row = snapshot('betika', event['match_id'], event['home_team'], event['away_team'],
                    kickoff, observed, raw_ref, run_id, prices, event['competition_name'],
                    event.get('category'), market['sub_type_id'], 'https://api-ug.betika.com/v1/uo/matches')
                if row:
                    row.update(provider_competition_id=str(event['competition_id']), market_status='UNKNOWN',
                        availability_note='Public feed provides prices without an explicit execution-availability flag.')
                    for outcome in row['outcomes']:
                        outcome['status'] = 'UNKNOWN'
                    records.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    return records


def normalize_cloudbet(payload, observed, raw_ref, run_id):
    """Public UEFA Champions League feed, enabled BACK selections in period=ft."""
    if (payload.get('key') != 'soccer-international-clubs-uefa-champions-league'
        or payload.get('name') != 'UEFA Champions League'
        or payload.get('sport', {}).get('key') != 'soccer' or payload.get('blank')):
        return []
    records = []
    for event in payload.get('events', []):
        if (event.get('type') != 'EVENT_TYPE_EVENT' or event.get('status') != 'TRADING'
            or event.get('metadata', {}).get('eventStatus') != 'not_started' or event.get('blank')):
            continue
        try:
            kickoff = datetime.fromisoformat(event['startTime'].replace('Z', '+00:00'))
            market = event.get('markets', {}).get('soccer.match_odds', {}).get('submarkets', {}).get('period=ft')
            if not market or market.get('blank'):
                continue
            prices = {}
            for selection in market.get('selections', []):
                key = {'home': 'HOME', 'draw': 'DRAW', 'away': 'AWAY'}.get(selection.get('outcome'))
                if (not key or key in prices or selection.get('params')
                    or selection.get('status') != 'SELECTION_ENABLED' or selection.get('side') != 'BACK'
                    or selection.get('marketUrl') != 'soccer.match_odds/' + selection['outcome']):
                    prices = {}; break
                prices[key] = (selection['price'], selection['marketUrl'])
            row = snapshot('cloudbet', event['id'], event['home']['name'], event['away']['name'],
                kickoff, observed, raw_ref, run_id, prices, 'UEFA Champions League', 'International Clubs',
                'soccer.match_odds', 'https://www.cloudbet.com/sports-api/c/v6/sports/competitions/soccer-international-clubs-uefa-champions-league/events',
                team_ids=[event['home']['key'], event['away']['key']], region='GLOBAL')
            if row:
                row['provider_competition_id'] = payload['key']
                records.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    return records


def _normalize_main_line(payload, observed, raw_ref, run_id, book, source_url, region):
    """Champions League main-game 1X2: group 1, types 1/home, 2/draw, 3/away."""
    records = []
    if not isinstance(payload, list):
        return records
    for event in payload:
        if (event.get('sport', {}).get('id') != 1
            or event.get('liga', {}).get('id') != 118587
            or event.get('liga', {}).get('name') != 'UEFA Champions League'
            or event.get('id') != event.get('mainGameId')
            or event.get('periodName') or event.get('gameTypeName')
            or any(event.get(flag) for flag in ['isLive', 'live', 'blocked', 'isBlocked'])):
            continue
        try:
            # The league feed also contains aggregate/special-bet placeholder teams.
            names = [event['opponent1']['fullName'], event['opponent2']['fullName']]
            if any(name.casefold() in {'home', 'away'} or '(special bets)' in name.casefold()
                   for name in names):
                continue
            groups = [g for g in event.get('eventGroups', [])
                      if g.get('groupId') == 1 and g.get('shortGroupId') == 1]
            if len(groups) != 1:
                continue
            prices = {}
            for column in groups[0]['events']:
                for offer in column:
                    key = {1: 'HOME', 2: 'DRAW', 3: 'AWAY'}.get(offer.get('type'))
                    if (not key or key in prices or offer.get('param')
                        or any(offer.get(flag) for flag in ['blocked', 'isBlocked', 'isSuspended'])):
                        prices = {}; break
                    prices[key] = (offer['cf'], offer['type'])
                else:
                    continue
                break
            row = snapshot(book, event['id'], event['opponent1']['fullName'],
                event['opponent2']['fullName'], datetime.fromtimestamp(event['startTs'], timezone.utc),
                observed, raw_ref, run_id, prices, 'UEFA Champions League', 'Europe', 1,
                source_url, region=region)
            if row:
                row.update(provider_competition_id='118587', market_status='UNKNOWN',
                    availability_note='Public prematch feed has no explicit execution-availability flag.')
                for outcome in row['outcomes']:
                    outcome['status'] = 'UNKNOWN'
                records.append(row)
        except (KeyError, ValueError, TypeError, OverflowError, OSError):
            continue
    return records


def normalize_1xbet(payload, observed, raw_ref, run_id):
    return _normalize_main_line(payload, observed, raw_ref, run_id, '1xbet',
        'https://1xbet.com/service-api/main-line-feed/v3/games1x2', None)


def normalize_22bet(payload, observed, raw_ref, run_id):
    return _normalize_main_line(payload, observed, raw_ref, run_id, '22bet',
        'https://22bet.ug/service-api/main-line-feed/v3/games1x2', 'UG')


def normalize_betonline(payload, observed, raw_ref, run_id):
    """UTC-offset=0 capture, parent Game-period three-way moneylines only."""
    offering = payload.get('GameOffering') or {}
    if (payload.get('IsError') is not False or payload.get('IsValidModel') is not True
        or offering.get('Sport') != 'Soccer' or offering.get('League') != 'UEFA CL'
        or offering.get('PeriodMin') != 0
        or not any(p.get('Number') == 0 and p.get('Name') == 'Game'
                   for p in offering.get('Periods', []))):
        return []
    records = []
    for description in offering.get('GamesDescription', []):
        game = description.get('Game') or {}
        if (game.get('ParentLinkEvent') or not game.get('SportCastFixtureId')
            or not game.get('DrawRotaion') or game.get('LiveBettingID')
            or game.get('ScheduleText', '').strip() != 'UEFA Champions League'):
            continue
        try:
            kickoff = datetime.fromisoformat(game['WagerCutOff'])
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            prices = {key: (game[field]['MoneyLine']['DecimalLine'], game[rotation])
                for key, field, rotation in [('HOME', 'HomeLine', 'HomeRotation'),
                    ('DRAW', 'DrawLine', 'DrawRotaion'), ('AWAY', 'AwayLine', 'AwayRotation')]}
            row = snapshot('betonlineag', game['GameId'], game['HomeTeam'], game['AwayTeam'],
                kickoff, observed, raw_ref, run_id, prices, 'UEFA Champions League', 'Europe',
                '0:MoneyLine', 'https://api-offering.betonline.ag/api/offering/Sports/offering-by-scheduletext', region=None)
            if row:
                row.update(market_status='UNKNOWN', availability_note='Public moneyline prices; execution availability is not explicit.')
                for outcome in row['outcomes']:
                    outcome['status'] = 'UNKNOWN'
                records.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    return records


def normalize_bookmaker(html, observed, raw_ref, run_id):
    """BookMaker's Champions League page: open full-game three-way moneylines."""
    soup = BeautifulSoup(html, 'html.parser')
    url = 'https://lines.bookmaker.eu/en/sports/soccer/uefa-champions-league/'
    canonical = soup.select_one('link[rel=canonical]')
    heading = soup.select_one('h1')
    table = soup.select_one('table')
    if (not canonical or canonical.get('href') != url or not heading
        or heading.get_text(strip=True) != 'UEFA Champions League Live Betting Odds'
        or not table or not table.caption
        or table.caption.get_text(strip=True) != 'UEFA Champions League games betting lines'
        or [h.get_text(' ', strip=True) for h in table.select('thead th')] !=
            ['Time', 'Team', 'Spread', 'Total', 'ML Moneyline']):
        return []
    try:
        modified = [item['dateModified'] for script in soup.select('script[type="application/ld+json"]')
            for item in json.loads(script.string or '{}').get('@graph', [])
            if item.get('@type') == 'WebPage' and item.get('@id') == url + '#webpage']
        if len(modified) != 1:
            return []
        updated = datetime.fromisoformat(modified[0].replace('Z', '+00:00'))
        instant = datetime.fromisoformat(observed.replace('Z', '+00:00'))
        if updated.tzinfo is None or updated > instant:
            return []
    except (KeyError, TypeError, ValueError):
        return []
    records = []
    for group in table.select('tbody[data-game-row]'):
        if group.get('data-live') != '0':
            continue
        try:
            kickoff = datetime.fromisoformat(group['data-starts'].replace('Z', '+00:00'))
            rows = [row for row in group.find_all('tr', recursive=False) if row.select_one('th.bm-team')]
            if len(rows) != 3 or rows[2].select_one('th.bm-team').get_text(strip=True) != 'Draw':
                continue
            links = [row.select_one('th.bm-team a') for row in rows[:2]]
            if any(not link for link in links) or links[0].get('href') != links[1].get('href'):
                continue
            path = links[0].get('href', '')
            if not re.fullmatch(r'/en/sports/soccer/uefa-champions-league/[a-z0-9-]+/', path):
                continue
            names = [link.select_one('span').get_text(strip=True) for link in links]
            prices = {}
            for key, row in zip(['HOME', 'AWAY', 'DRAW'], rows):
                cells = row.select('td.bm-c')
                chip = cells[-1].select_one('.bm-chip') if len(cells) == 3 else None
                if (not chip or 'is-off' in chip.get('class', [])
                    or 'suspended' in chip.get('title', '').casefold() or not chip.select_one('b')):
                    prices = {}; break
                american = chip.select_one('b').get_text(strip=True)
                if american == 'EV':
                    decimal = 2.0
                elif re.fullmatch(r'[+-][1-9][0-9]*', american):
                    value = int(american)
                    decimal = 1 + (value / 100 if value > 0 else 100 / abs(value))
                else:
                    prices = {}; break
                prices[key] = (decimal, key)
            record = snapshot('bookmaker', path + ':' + group['data-starts'], names[0], names[1],
                kickoff, observed, raw_ref, run_id, prices, 'UEFA Champions League', 'Europe',
                'game:three_way_moneyline', url, updated=updated.isoformat(), region=None)
            if record:
                records.append(record)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return records


def normalize_ababet(html, observed, raw_ref, run_id):
    soup = BeautifulSoup(html, 'html.parser')
    selected = soup.select_one('select[name="date"] option[selected]')
    if not selected:
        raise ValueError('AbaBet page lacks an explicit selected fixture date')
    day = selected['value']
    records = []
    for event in soup.select('tr.event'):
        cells = event.find_all('td', recursive=False)
        competitions = {'England - Premier League': ('Premier League', 'England'),
                        'Europe - UEFA Champions League': ('UEFA Champions League', 'Europe')}
        competition = competitions.get(cells[0].get_text(strip=True)) if cells else None
        if not competition or event.get('data-period') != '-1':
            continue
        try:
            time_cell = event.select_one('[id^="time_"]')
            kickoff = datetime.fromisoformat(day + 'T' + time_cell.get_text(strip=True)).replace(tzinfo=ZoneInfo('Africa/Kampala'))
            prices = {}
            for offer in event.select('button.bet'):
                if offer.get('data-market') != 'Match Result' or offer.get('data-live_status') != '0' or offer.has_attr('disabled'):
                    continue
                selection = {'1':'HOME','X':'DRAW','2':'AWAY'}.get(offer.get('data-bet'))
                if selection:
                    if selection in prices:
                        prices = {}; break
                    prices[selection] = (float(offer['data-odds']), offer['data-id'])
            row = snapshot('ababet', event['data-id'], event.select_one('.home').get_text(strip=True),
                event.select_one('.away').get_text(strip=True), kickoff, observed, raw_ref, run_id,
                prices, competition[0], competition[1], 'Match Result', 'https://ababet.ug/')
            if row:
                records.append(row)
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return records


def normalize_betpawa(payload, observed, raw_ref, run_id):
    from football_competitions import PUBLIC_LEAGUES
    records = []
    for batch in payload.get('responses', []):
        for event in batch.get('responses', []):
            competition = event.get('competition', {}).get('name')
            country = event.get('region', {}).get('name')
            if event.get('category', {}).get('id') != '2' or (country, competition) not in PUBLIC_LEAGUES:
                continue
            if event.get('results') or event.get('scoreboard'):
                continue
            for market in event.get('markets', []):
                definition = market.get('marketType', {})
                if definition.get('name') != '1X2 - FT' or 'regular playing time' not in definition.get('explainer', '').lower():
                    continue
                try:
                    participants = {team['position']: team for team in event['participants']}
                    home, away = participants[1], participants[2]
                    kickoff = datetime.fromisoformat(event['startTime'].replace('Z', '+00:00'))
                    for group in market.get('row', []):
                        prices = {}
                        for offer in group.get('prices', []):
                            key = {'1':'HOME','X':'DRAW','2':'AWAY'}.get(offer.get('name'))
                            if key:
                                if key in prices or offer.get('additionalInfo', {}).get('suspended') or offer.get('status') in {'SUSPENDED','CLOSED'}:
                                    prices = {}; break
                                prices[key] = (offer['odds'], offer['id'])
                        row = snapshot('betpawa', event['id'], home['name'], away['name'], kickoff,
                            observed, raw_ref, run_id, prices, competition, country, group['id'],
                            'https://www.betpawa.ug/api/sportsbook/v4/events/lists/by-queries',
                            team_ids=[home['id'],away['id']])
                        if row:
                            records.append(row)
                except (KeyError, ValueError, TypeError):
                    continue
    return records


def normalize_sportpesa(payload, observed, raw_ref, run_id):
    """Global public EPL feed; standard market 10 excludes early-payout variants."""
    if not isinstance(payload, list):
        raise ValueError('SportPesa response must be an event list')
    records = []
    for event in payload:
        if (event.get('sport', {}).get('id') != 1 or event.get('country', {}).get('name') != 'England'
            or event.get('competition', {}).get('name') != 'Premier League' or event.get('state')):
            continue
        try:
            home, away = event['competitors']
            kickoff = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
            if kickoff.tzinfo is None or round(kickoff.timestamp()*1000) != event['dateTimestamp']:
                continue
            for market in event.get('markets', []):
                if market.get('id') != 10 or market.get('name') != '1X2' or market.get('specValue', 0) != 0:
                    continue
                prices = {}
                names = {'1':home['name'], 'X':'Draw', '2':away['name']}
                for offer in market.get('selections', []):
                    key = {'1':'HOME','X':'DRAW','2':'AWAY'}.get(offer.get('shortName'))
                    if (not key or key in prices or offer.get('specValue', 0) != 0
                        or offer.get('name') != names[offer['shortName']]
                        or offer.get('suspended') or offer.get('status') in {'SUSPENDED','CLOSED'}):
                        prices = {}; break
                    prices[key] = (offer['odds'],offer['id'])
                row = snapshot('sportpesa',event['id'],home['name'],away['name'],kickoff,
                    observed,raw_ref,run_id,prices,'Premier League','England',10,
                    'https://www.sportpesa.com/api/upcoming/games',team_ids=[home['id'],away['id']],region='GLOBAL')
                if row:
                    row.update(provider_competition_id=str(event['competition']['id']),market_status='UNKNOWN',
                        availability_note='Anonymous public feed lists prices without explicit execution availability.')
                    for offer in row['outcomes']:
                        offer['status'] = 'UNKNOWN'
                    records.append(row)
        except (KeyError, ValueError, TypeError):
            continue
    return records
