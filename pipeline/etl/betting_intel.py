"""Publish bounded, atomic intelligence inputs without changing active models."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile

from sqlalchemy import text

from api.betting_intel import SPORTS, build_intelligence, sport_key
from api.db import get_db_connection, get_heritage_db_connection
from config import MODEL_VERSION, PROCESSED_DATA_DIR, RAW_DATA_DIR

SNAPSHOT_PATH = PROCESSED_DATA_DIR / 'betting_intel' / 'snapshot.json'


def raw_event(event, now):
    from api.betting_intel import timestamp
    key = sport_key('', event.get('sport_key'))
    kickoff = timestamp(event.get('commence_time'))
    if not key or key == 'football' or not kickoff or not now < kickoff < now+timedelta(days=7):
        return None
    home, away = event.get('home_team'), event.get('away_team')
    if not event.get('id') or not home or not away or home == away:
        return None
    fixture = {'fixture_id':'oddsapi:'+str(event['id']),'sport':key,'competition':SPORTS[key]['label'],
               'home_team':home,'away_team':away,'kickoff':kickoff,'status':'SCHEDULED',
               'settlement_rule':SPORTS[key]['rule'],'offers':[]}
    for book in event.get('bookmakers',[]):
        for market in book.get('markets',[]):
            name = market.get('key','')
            if name != 'h2h' and not name.startswith('player_'):
                continue
            for outcome in market.get('outcomes',[]):
                selection = {'Over':'over','Under':'under'}.get(outcome.get('name')) if name != 'h2h' else (
                    'home_win' if outcome.get('name') == home else 'away_win' if outcome.get('name') == away else None)
                if selection:
                    fixture['offers'].append({'market':name,'selection':selection,'participant':outcome.get('description'),
                        'line':outcome.get('point'),'decimal_odds':outcome.get('price'),'bookmaker':book.get('key'),
                        'observed_at':market.get('last_update') or book.get('last_update')})
    return fixture


def load_raw(now):
    """NBA wrapper stores captures separately from the generic offer importer."""
    paths = []
    for directory, pattern in [('nba','nba_odds_*.json'),('ncaab','*odds*.json'),
                               ('the_odds_api','odds_*.json'),('player_props','*.json')]:
        paths.extend(sorted((RAW_DATA_DIR/directory).glob(pattern), key=lambda p:p.stat().st_mtime, reverse=True)[:10])
    fixtures = []
    for path in paths:
        payload = json.loads(path.read_text(encoding='utf-8'))
        events = payload if isinstance(payload,list) else payload.get('events',[])
        for event in events:
            fixture = raw_event(event,now) if isinstance(event,dict) else None
            if fixture:
                fixtures.append(fixture)
    return fixtures


def merge_fixtures(fixtures):
    from api.betting_intel import timestamp
    from etl.nba_public_parsers import team as nba_team
    merged = {}
    for fixture in fixtures:
        if fixture['sport']=='nba':
            fixture={**fixture,'home_team':nba_team(fixture['home_team']) or fixture['home_team'],
                     'away_team':nba_team(fixture['away_team']) or fixture['away_team']}
        key = (fixture['sport'],fixture['home_team'].strip().casefold(),fixture['away_team'].strip().casefold(),
               timestamp(fixture['kickoff']).isoformat())
        if key not in merged:
            merged[key] = {**fixture,'offers':list(fixture.get('offers',[]))}
        else:
            merged[key]['offers'].extend(fixture.get('offers',[]))
    return sorted(merged.values(),key=lambda f:timestamp(f['kickoff']))


def load_heritage(now):
    """Only linked, upcoming events; never infer a player prop's fixture."""
    with get_heritage_db_connection().connect() as conn:
        conn.execute(text("SET LOCAL statement_timeout = '30s'"))
        rows = conn.execute(text('''SELECT id::text AS fixture_id,sport,league AS competition,
            home_team,away_team,event_date AS kickoff,status FROM events
            WHERE event_date>:now AND event_date<:end AND UPPER(status) IN ('UPCOMING','SCHEDULED','NOT_STARTED')
            ORDER BY event_date,id LIMIT 500'''), {'now':now,'end':now+timedelta(days=7)}).mappings().all()
        fixtures = {}
        for row in rows:
            key = sport_key(row['sport'], row['competition'])
            if key is None or key == 'football':
                continue
            item = dict(row)
            item.update(sport=key, settlement_rule=SPORTS[key]['rule'], offers=[])
            fixtures[item['fixture_id']] = item
        if not fixtures:
            return []
        offers = conn.execute(text('''SELECT DISTINCT ON (event_id,book_key,market,selection,line,participant)
            event_id::text AS fixture_id,book_key AS bookmaker,market,selection,line,participant,
            odds_decimal AS decimal_odds,source_updated_at AS observed_at
            FROM odds_offers WHERE event_id::text=ANY(:ids)
              AND source_updated_at<=:now
            ORDER BY event_id,book_key,market,selection,line,participant,source_updated_at DESC,created_at DESC'''),
            {'ids':list(fixtures),'now':now}).mappings().all()
        for row in offers:
            offer = dict(row)
            offer['selection'] = {'HOME':'home_win','AWAY':'away_win','DRAW':'draw','OVER':'over','UNDER':'under'}.get(str(row['selection']).upper())
            fixtures[row['fixture_id']]['offers'].append(offer)
        # Prop rows share explicit event IDs. Latest snapshots replace, not combine,
        # opposing outcomes from unrelated events or bookmakers.
        props = conn.execute(text('''SELECT DISTINCT ON (event_id,source,market,player_name,line)
            event_id::text AS fixture_id,source AS bookmaker,market,player_name AS participant,line,
            over_odds,under_odds,source_updated_at AS observed_at FROM player_props
            WHERE event_id::text=ANY(:ids) AND is_active=true AND source_updated_at<=:now
            ORDER BY event_id,source,market,player_name,line,source_updated_at DESC,updated_at DESC'''),
            {'ids':list(fixtures),'now':now}).mappings().all()
        for row in props:
            for side in ('over','under'):
                fixtures[row['fixture_id']]['offers'].append({**dict(row),'selection':side,'decimal_odds':row[side+'_odds']})
    return list(fixtures.values())


def load_football(now):
    with get_db_connection().connect() as conn:
        conn.execute(text("SET LOCAL statement_timeout = '30s'"))
        rows = conn.execute(text('''SELECT m.match_id::text AS fixture_id,m.competition,m.home_team,m.away_team,
            m.date AT TIME ZONE 'UTC' AS kickoff,m.status,p.home_prob,p.draw_prob,p.away_prob,p.model_version,
            p.created_at AT TIME ZONE 'UTC' AS generated_at,
            COALESCE(q.quotes,'[]'::json) AS quotes FROM matches m
            LEFT JOIN LATERAL (SELECT * FROM predictions p WHERE p.match_id=m.match_id AND p.model_version=:version
                AND p.created_at<=:cutoff AND p.created_at<m.date ORDER BY p.created_at DESC,p.id DESC LIMIT 1) p ON TRUE
            LEFT JOIN LATERAL (SELECT json_agg(latest) AS quotes FROM (SELECT DISTINCT ON (bookmaker)
                bookmaker,home_win,draw,away_win,updated_at AT TIME ZONE 'UTC' AS observed_at FROM odds
                WHERE match_id=m.match_id AND updated_at<=:cutoff ORDER BY bookmaker,updated_at DESC,id DESC) latest) q ON TRUE
            WHERE m.sport_type='football' AND m.date>:cutoff AND m.date<:end AND m.result IS NULL
              AND UPPER(COALESCE(m.status,'')) NOT IN ('LIVE','IN_PLAY','PAUSED','FINISHED','CANCELLED','CANCELED','POSTPONED')
            ORDER BY m.date,m.match_id LIMIT 300'''),
            {'version':MODEL_VERSION,'cutoff':now.replace(tzinfo=None),'end':(now+timedelta(days=7)).replace(tzinfo=None)}).mappings().all()
    fixtures = []
    for row in rows:
        item = {key:row[key] for key in ('fixture_id','competition','home_team','away_team','kickoff','status')}
        item.update(sport='football',settlement_rule='REGULATION_1X2',offers=[])
        if row['generated_at']:
            item['prediction'] = {'probabilities':dict(zip(('home_win','draw','away_win'),(row['home_prob'],row['draw_prob'],row['away_prob']))),
                'generated_at':row['generated_at'],'model_version':row['model_version'],'status':'active',
                'settlement_rule':'REGULATION_1X2','probability_basis':'UNCONDITIONAL_FINAL_RESULT'}
        for quote in row['quotes']:
            for key in ('home_win','draw','away_win'):
                item['offers'].append({'market':'h2h','selection':key,'decimal_odds':quote.get(key),
                    'bookmaker':quote['bookmaker'],'observed_at':quote['observed_at']})
        fixtures.append(item)
    return fixtures


def add_candidate_predictions(fixtures, now, max_per_sport=30):
    from models.sport_predict import catalog, candidate_directory, predict_candidate, candidate_teams
    from api.betting_intel import timestamp
    from etl.nba_public_parsers import team as nba_team
    from threadpoolctl import threadpool_limits
    candidates = catalog()
    chosen, counts, errors, names = {}, {}, [], {}
    for fixture in fixtures:
        sport = fixture['sport']
        if sport == 'football' or counts.get(sport,0) >= max_per_sport:
            continue
        config = SPORTS[sport]
        if sport not in chosen:
            chosen[sport] = None
            for run in candidates:
                if run['sports'].get(config['model_sport'],{}).get('status') != 'candidate':
                    continue
                path = candidate_directory(run['candidate_id'],config['model_sport'])/'metrics.json'
                metadata = json.loads(path.read_text(encoding='utf-8'))
                if config['league'] in metadata.get('training_leagues',[]):
                    chosen[sport] = run['candidate_id']
                    break
        if chosen[sport] is None:
            continue
        counts[sport] = counts.get(sport,0)+1
        try:
            home,away=fixture['home_team'],fixture['away_team']
            if sport=='nba':
                if sport not in names:
                    names[sport]={}
                    for name in candidate_teams(chosen[sport],config['model_sport'],config['league']):
                        canonical=nba_team(name)
                        if canonical: names[sport].setdefault(canonical,[]).append(name)
                for canonical in (home,away):
                    if len(names[sport].get(canonical,[]))!=1:
                        raise ValueError('NBA team has no unique reviewed candidate history identity')
                home,away=names[sport][home][0],names[sport][away][0]
            with threadpool_limits(limits=1):
                prediction = predict_candidate(chosen[sport], config['model_sport'],home,away,
                    timestamp(fixture['kickoff']).isoformat(),config['league'])
            fixture['prediction'] = {**prediction,'generated_at':now.isoformat(), 'model_version':prediction['model_version'],
                                      'status':'candidate_preview','active':False}
        except (ValueError,FileNotFoundError) as exc:
            errors.append({'source':'candidate','fixture_id':fixture['fixture_id'],'sport':sport,'reason':str(exc)})
    return errors


def refresh(path=SNAPSHOT_PATH, include_candidates=True):
    now = datetime.now(timezone.utc)
    fixtures, errors = [], []
    from etl.fetch_nba_public_odds import load_validated
    for source, loader in [('pipeline',load_football),('heritage',load_heritage),('raw_odds',load_raw),('nba_public',load_validated)]:
        try:
            fixtures.extend(loader(now))
        except Exception as exc:
            # Keep another source usable, but expose failure rather than treating it as no opportunities.
            errors.append({'source':source,'reason':type(exc).__name__})
    from etl.fetch_nba_public_odds import source_status
    errors.extend(source_status(now))
    fixtures = merge_fixtures(fixtures)
    from etl.fetch_nba_public_odds import current_schedule
    from etl.nba_public_parsers import validate_fixtures
    schedule=current_schedule(now)
    fixture_exclusions=[]
    if schedule:
        nba,fixture_exclusions=validate_fixtures([f for f in fixtures if f['sport']=='nba'],schedule,now)
        fixtures=merge_fixtures([f for f in fixtures if f['sport']!='nba']+nba)
        if fixture_exclusions:
            errors.append({'source':'nba_fixture_validation','reason':f'{len(fixture_exclusions)} stored NBA fixtures excluded: no unique matching scheduled game in the independent feed.'})
    if include_candidates:
        try:
            errors.extend(add_candidate_predictions(fixtures,now))
        except Exception as exc:
            errors.append({'source':'candidate_catalog','reason':type(exc).__name__})
    if not fixtures and len(errors) >= 4:
        raise RuntimeError('No usable intelligence sources; previous snapshot retained')
    payload = {'schema_version':1,'snapshot_at':now.isoformat(),'fixtures':fixtures,'source_errors':errors,
               'nba_fixture_exclusions':fixture_exclusions,
               'model_policy':'Active football predictions; other sports use labeled inactive candidate previews. No models promoted.'}
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary = stream.name
            json.dump(payload,stream,default=lambda value:value.isoformat() if isinstance(value,datetime) else float(value),allow_nan=False)
        os.replace(temporary,path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return {'snapshot_at':payload['snapshot_at'],'source_errors':errors,
            'sports':{sport:build_intelligence(sport,fixtures,now)['summary'] for sport in SPORTS}}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect-props',action='store_true',help='Fetch up to 10 NBA event prop markets using configured provider access/quota')
    args = parser.parse_args()
    if args.collect_props:
        from etl.ingest_player_props import run
        run()
    print(json.dumps(refresh(),indent=2))
