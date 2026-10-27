"""One bounded regional collection, exact ingestion and paper-result refresh cycle."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

import pandas as pd
import requests
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from threadpoolctl import threadpool_limits

from api.db import get_db_connection
from config import BASE_DIR, MODEL_DIR, MODEL_VERSION, PROCESSED_DATA_DIR, RAW_DATA_DIR
from models.predict_v2 import predict_match
from models.paper_trial import TRIAL_ROOT, dashboard, import_trial, result_key, settle_directory
from models.sport_predict import candidate_directory
from scripts.record_edge_trial import run as record_trial
from scripts.refresh_paper_trial import collect_results
from scripts.sync_verified_odds import sync
from scripts.sync_bookmaker_grid import sync_grid, capture_cache_rejections


def continue_frozen_trial(capture, audit, day, stamp):
    trials = []
    for path in TRIAL_ROOT.glob('*/trial.json'):
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != path.parent.name:
            raise ValueError('Trial checksum mismatch')
        trial = json.loads(payload)
        if trial['policy'].get('selection') != 'user_selected':
            trials.append(trial)
    if not trials:
        return {'status': 'no_imported_policy'}
    primary = min(trials, key=lambda trial: trial['created_at'])
    directory = candidate_directory(primary['candidate_id'], 'football')
    for name, digest in primary['candidate_checksums'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen candidate changed; refusing continuation')
    seen = {result_key(row['home'], row['away'], row['kickoff'])
            for trial in trials for row in trial['fixtures']}
    records = [json.loads(line) for line in (capture/'odds_snapshots.jsonl').read_text().splitlines() if line]
    rejected = capture_cache_rejections(capture)
    records = [row for row in records if row['bookmaker'] == 'bovada'
        and row['bookmaker'] not in rejected
        and row.get('country') == 'England' and row.get('competition') == 'Premier League'
        and row['commence_time'].startswith(day)
        and result_key(row['home_team'], row['away_team'], row['commence_time']) not in seen]
    if not records:
        return {'status': 'no_new_primary_fixtures'}
    source = capture/('new_primary_trial_quotes_' + day + '.jsonl')
    with source.open('x', encoding='utf-8') as stream:
        stream.write(''.join(json.dumps(row)+'\n' for row in records))
    output = audit/(stamp+'_frozen_trial.json')
    report = record_trial(source, output, primary['candidate_id'], day)
    if report['policy'] != primary['policy'] or report['candidate_checksums'] != primary['candidate_checksums']:
        raise ValueError('Trial continuation changed the declared policy')
    return {'status': 'recorded', 'directory': str(import_trial(output)), 'fixtures': len(report['fixtures'])}


def continue_upcoming_trials(capture, audit, day, stamp):
    """Record fresh prematch quotes within the official fixture refresh window."""
    start = pd.Timestamp(day).date()
    end = start + pd.Timedelta(days=14)
    records = [json.loads(line) for line in (capture / 'odds_snapshots.jsonl').read_text(encoding='utf-8').splitlines() if line]
    days = sorted({row['commence_time'][:10] for row in records
        if row['bookmaker'] == 'bovada' and row.get('country') == 'England'
        and row.get('competition') == 'Premier League'
        and start <= pd.Timestamp(row['commence_time']).date() <= end})
    return [{'match_date': date, **continue_frozen_trial(capture, audit, date, stamp + '_' + date)}
            for date in days]


def refresh_forecasts(day):
    artifacts = [MODEL_DIR/f'{name}_v{MODEL_VERSION}.pkl' for name in ['model','label_encoder','features','scaler']]
    checksums = {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts if path.exists()}
    engine = get_db_connection()
    with engine.connect() as conn:
        fixtures = conn.execute(text('''SELECT m.match_id,m.home_team,m.away_team,m.date,
            q.bookmaker,q.home_win,q.draw,q.away_win,q.updated_at FROM matches m
            JOIN LATERAL (SELECT * FROM odds o WHERE o.match_id=m.match_id
                AND o.updated_at <= (NOW() AT TIME ZONE 'UTC')
                AND o.updated_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '15 minutes'
                AND o.updated_at < m.date AND o.home_win>1 AND o.draw>1 AND o.away_win>1
                ORDER BY (o.bookmaker='bovada') DESC,o.updated_at DESC,o.id DESC LIMIT 1) q ON TRUE
            WHERE m.competition='Premier League' AND m.date::date=CAST(:day AS DATE)
                AND m.date>(NOW() AT TIME ZONE 'UTC') AND m.result IS NULL
                AND COALESCE(m.status,'') NOT IN ('FINISHED','CANCELLED','POSTPONED','IN_PLAY','LIVE')'''), {'day':day}).mappings().all()
    report = []
    for row in fixtures:
        cutoff = pd.Timestamp.now(tz='UTC')
        with threadpool_limits(limits=1):
            prediction = predict_match(row['home_team'],row['away_team'],
                odds={key:row[key] for key in ['home_win','draw','away_win']},engine=engine,cutoff=cutoff)
        generated = datetime.now(timezone.utc).replace(tzinfo=None)
        if any(hashlib.sha256((MODEL_DIR/name).read_bytes()).hexdigest() != digest for name,digest in checksums.items()):
            raise ValueError('Active artifacts changed during forecast generation')
        if generated >= row['date']:
            continue
        with engine.begin() as conn:
            prediction_id = conn.execute(text('''INSERT INTO predictions
                (match_id,model_version,winner,home_prob,draw_prob,away_prob,created_at)
                SELECT :match_id,:model_version,:winner,:home_prob,:draw_prob,:away_prob,:created_at
                WHERE EXISTS (SELECT 1 FROM matches WHERE match_id=:match_id AND date>:created_at AND result IS NULL)
                RETURNING id'''), {'match_id':row['match_id'],'created_at':generated,
                    **{key:prediction[key] for key in ['model_version','winner','home_prob','draw_prob','away_prob']}}).scalar()
        report.append({'match_id':row['match_id'],'prediction_id':prediction_id,'prediction':prediction,
            'generated_at':generated.isoformat()+'Z','feature_cutoff':cutoff.isoformat(),
            'artifact_checksums':checksums,
            'bookmaker':row['bookmaker'],'quote_observed_at':row['updated_at'].isoformat()+'Z',
            'prices':{key:row[key] for key in ['home_win','draw','away_win']}})
    return report


def refresh_trial_results():
    trials = [trial for trial in dashboard()['trials'] if trial['pending_forecasts']]
    days = {row['kickoff'][:10] for trial in trials for row in trial['fixtures']
            if row['status'] == 'recorded_pregame'}
    results, errors = {}, {}
    for day in sorted(days):
        if pd.Timestamp(day).date() > datetime.now(timezone.utc).date():
            results[day] = []
            continue
        try:
            results[day] = collect_results(day)
        except (ValueError, OSError, requests.RequestException) as exc:
            errors[day] = type(exc).__name__
    reports = []
    for trial in trials:
        required = {row['kickoff'][:10] for row in trial['fixtures'] if row['status'] == 'recorded_pregame'}
        if required <= results.keys():
            reports.append(settle_directory(TRIAL_ROOT/trial['trial_sha256'],
                [result for day in required for result in results[day]]))
    return {'settlements':reports, 'provider_errors':errors}


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    day = datetime.now(timezone.utc).date().isoformat()
    capture = RAW_DATA_DIR/'sportsbooks'/stamp
    targets = BASE_DIR.parent/'_config/bookmakers.json'
    audit = PROCESSED_DATA_DIR/'regional_audits'
    audit.mkdir(exist_ok=True)
    report = {'capture': str(capture), 'errors': {}}
    try:
        collector_python = BASE_DIR/'.venv-scrapling/Scripts/python.exe'
        if not collector_python.exists():
            raise FileNotFoundError('Scrapling environment unavailable')
        subprocess.run([str(collector_python),'-m','etl.scrape_sportsbooks',
            '--transport','scrapling','--targets',str(targets),'--output-dir',str(capture)],check=True)
        report['bookmaker_grid'] = sync_grid(capture, apply=True)
        report.update(sync(capture,day,audit/(stamp+'_ingestion.json'),apply=True))
        report['trial_continuation'] = continue_upcoming_trials(capture,audit,day,stamp)
        report['forecasts'] = refresh_forecasts(day)
        sources = json.loads((capture/'source_report.json').read_text(encoding='utf-8'))
        primary = next((s for s in sources['direct_sources'] if s['bookmaker'] == 'bovada'), None)
        if not primary or primary.get('status') not in {'collected', 'no_complete_upcoming_1x2'}:
            report['errors']['primary_source'] = 'BovadaUnavailable'
    except (ValueError, OSError, requests.RequestException, subprocess.CalledProcessError, SQLAlchemyError) as exc:
        report['errors']['collection'] = type(exc).__name__
    # Settlement must keep running even when fresh price collection fails.
    report['trial_refreshes'] = refresh_trial_results()
    report['errors'].update(report['trial_refreshes']['provider_errors'])
    from scripts.assess_paper_trial import run as assess_trials
    report['assessments'] = assess_trials()
    # Keep the user's requested NBA public-source route in the recurring refresh.
    # Scrapling has its own compatible environment; do not silently switch to requests.
    nba_python = BASE_DIR/'.venv-scrapling/Scripts/python.exe'
    try:
        if not nba_python.exists():
            raise FileNotFoundError('Scrapling environment unavailable')
        subprocess.run([str(nba_python),'-m','etl.fetch_nba_public_odds'],check=True,timeout=180,cwd=BASE_DIR)
        report['nba_public_odds'] = 'collected_and_independently_validated'
    except (OSError, subprocess.SubprocessError) as exc:
        report['errors']['nba_public_odds'] = type(exc).__name__
    from etl.betting_intel import refresh as refresh_intelligence
    from models.predict_football_leagues import REGISTRY, predict as predict_leagues
    if REGISTRY.exists():
        try:
            league_run = MODEL_DIR/'league_models'/json.loads(REGISTRY.read_text(encoding='utf-8'))['run_directory']
            league_forecasts = predict_leagues(league_run, publish=True)
            report['league_forecasts'] = league_forecasts['coverage']
        except (OSError, ValueError, KeyError, RuntimeError, SQLAlchemyError) as exc:
            report['errors']['league_forecasts'] = type(exc).__name__
    try:
        report['betting_intelligence'] = refresh_intelligence()
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        report['errors']['betting_intelligence'] = type(exc).__name__
    (audit/(stamp+'_cycle.json')).write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'capture':str(capture),'audit':str(audit/(stamp+'_cycle.json')),
        'matched_quotes':report.get('matched_snapshots',0),'refreshed_forecasts':len(report.get('forecasts',[])),
        'errors':report['errors']},indent=2))
    if report['errors']:
        raise RuntimeError('Regional collection incomplete; see saved cycle audit')


if __name__ == '__main__':
    main()
