"""Read-only operational coverage for the existing public prediction evidence."""
from datetime import datetime, timezone

from sqlalchemy import text

from api.bookmaker_catalog import bookmaker_catalog
from api.db import get_db_connection
from api.prediction_dashboard import UTC_NOW, VALID_PROBS, utc
from config import BASE_DIR, MODEL_VERSION, RAW_DATA_DIR
from etl.utils import load_json_object, load_status_json


CTE = f"""WITH upcoming AS (
    SELECT match_id,competition,date FROM matches
    WHERE date > {UTC_NOW} AND result IS NULL
      AND UPPER(COALESCE(status,'')) NOT IN
          ('FINISHED','CANCELLED','CANCELED','POSTPONED','LIVE','IN_PLAY','PAUSED')
), latest_quotes AS (
    SELECT DISTINCT ON (o.match_id,o.bookmaker) o.* FROM odds o
    JOIN upcoming m ON m.match_id=o.match_id
    ORDER BY o.match_id,o.bookmaker,o.updated_at DESC NULLS LAST,o.id DESC
), fresh_quotes AS (
    SELECT q.* FROM latest_quotes q JOIN upcoming m ON m.match_id=q.match_id
    WHERE q.updated_at BETWEEN {UTC_NOW} - INTERVAL '24 hours' AND {UTC_NOW}
      AND q.updated_at < m.date
      AND q.home_win > 1 AND q.home_win < 'Infinity'::float8
      AND q.draw > 1 AND q.draw < 'Infinity'::float8
      AND q.away_win > 1 AND q.away_win < 'Infinity'::float8
), latest_predictions AS (
    SELECT DISTINCT ON (p.match_id) p.* FROM predictions p
    JOIN upcoming m ON m.match_id=p.match_id
    WHERE p.model_version=:version AND p.created_at < m.date AND p.created_at <= {UTC_NOW}
    ORDER BY p.match_id,p.created_at DESC,p.id DESC
), current_predictions AS (
    SELECT p.* FROM latest_predictions p WHERE {VALID_PROBS}
      AND p.created_at >= {UTC_NOW} - INTERVAL '24 hours'
), compared AS (
    SELECT p.home_prob,p.draw_prob,p.away_prob,
           MAX(q.home_win) home_price,MAX(q.draw) draw_price,MAX(q.away_win) away_price
    FROM current_predictions p JOIN fresh_quotes q ON q.match_id=p.match_id
    GROUP BY p.match_id,p.home_prob,p.draw_prob,p.away_prob
) """


def collection_receipt(root=RAW_DATA_DIR / 'sportsbooks') -> dict:
    """Expose counts and outcomes, excluding host paths, URLs and credentials."""
    try:
        reports = list(root.glob('*/source_report.json'))
        if not reports:
            return {'state': 'missing'}
        path = max(reports, key=lambda item: item.stat().st_mtime_ns)
        report = load_json_object(path)
        sources = report['direct_sources']
        if not isinstance(sources, list) or any(not isinstance(source, dict) for source in sources):
            raise ValueError('Invalid collection sources')
        return {'state': 'available', 'run_id': report['run_id'],
                'completed_at': report['completed_at'], 'transport': report.get('transport', 'requests'),
                'snapshot_count': report['snapshot_count'], 'sources_checked': len(sources),
                'sources_with_quotes': sum(bool(source.get('snapshots')) for source in sources),
                'sources': [{'bookmaker': source['bookmaker'], 'status': source['status'],
                             'snapshots': source.get('snapshots', 0)} for source in sources]}
    except (OSError, ValueError, KeyError, TypeError):
        return {'state': 'unavailable'}


def overview() -> dict:
    params = {'version': MODEL_VERSION}
    with get_db_connection().connect() as connection:
        summary = dict(connection.execute(text(CTE + """SELECT
            (SELECT COUNT(*) FROM upcoming) upcoming_fixtures,
            (SELECT MIN(date) FROM upcoming) next_kickoff,
            (SELECT COUNT(*) FROM current_predictions) current_forecasts,
            (SELECT MAX(created_at) FROM current_predictions) latest_forecast_at,
            (SELECT COUNT(*) FROM fresh_quotes) fresh_quotes,
            (SELECT COUNT(DISTINCT match_id) FROM fresh_quotes) priced_fixtures,
            (SELECT MAX(updated_at) FROM fresh_quotes) latest_quote_at,
            (SELECT COUNT(*) * 3 FROM compared) compared_outcomes,
            (SELECT COALESCE(SUM((home_prob*home_price>1)::int
                + (draw_prob*draw_price>1)::int + (away_prob*away_price>1)::int),0) FROM compared) positive_ev_outcomes
        """), params).mappings().one())
        books = connection.execute(text(CTE + """SELECT bookmaker,COUNT(*) fresh_quotes,
            COUNT(DISTINCT match_id) fixtures,MAX(updated_at) latest_quote_at
            FROM fresh_quotes GROUP BY bookmaker ORDER BY COUNT(*) DESC,bookmaker"""), params).mappings().all()
        leagues = connection.execute(text(CTE + """SELECT m.competition,COUNT(DISTINCT m.match_id) fixtures,
            COUNT(DISTINCT p.match_id) current_forecasts,COUNT(DISTINCT q.match_id) priced_fixtures
            FROM upcoming m LEFT JOIN current_predictions p ON p.match_id=m.match_id
            LEFT JOIN fresh_quotes q ON q.match_id=m.match_id GROUP BY m.competition
            ORDER BY COUNT(DISTINCT m.match_id) DESC,m.competition"""), params).mappings().all()
    for key in ['next_kickoff', 'latest_forecast_at', 'latest_quote_at']:
        summary[key] = utc(summary[key])
    catalog = bookmaker_catalog()
    observed = {row['bookmaker']: dict(row) for row in books}
    configured = {row['bookmaker'] for row in catalog}
    rows = []
    for book in catalog + [{'bookmaker': key, 'name': key} for key in observed if key not in configured]:
        stats = observed.get(book['bookmaker'])
        rows.append({'bookmaker': book['bookmaker'], 'name': book['name'],
                     'configured': book['bookmaker'] in configured,
                     'fresh_quotes': stats['fresh_quotes'] if stats else 0,
                     'fixtures': stats['fixtures'] if stats else 0,
                     'latest_quote_at': utc(stats['latest_quote_at']) if stats else None})
    status = load_status_json(BASE_DIR / 'logs/edge_trial_status.json')
    collector = {key: status.get(key) for key in
                 ['outcome', 'last_attempt_at', 'finished_at', 'last_success_at', 'failed_steps']} if status else None
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'active_model_version': MODEL_VERSION,
            'max_evidence_age_hours': 24, 'summary': summary,
            'configured_bookmakers': len(configured),
            'covered_bookmakers': len(configured & observed.keys()),
            'bookmakers': sorted(rows, key=lambda row: (-row['fresh_quotes'], row['name'].casefold())),
            'competitions': [dict(row) for row in leagues], 'collector': collector,
            'latest_collection': collection_receipt()}
