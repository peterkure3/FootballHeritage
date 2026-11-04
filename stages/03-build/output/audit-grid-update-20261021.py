"""Read-only live verification of repaired bookmaker coverage."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
import requests
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'))
from api.db import get_db_connection
from scripts.sync_bookmaker_grid import load_grid_snapshots,matched_grid_quotes
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
url='http://127.0.0.1:5555/api/v1/prediction-dashboard/fixtures'
response=requests.get(url,params={'page_size':50},timeout=20);response.raise_for_status();feed=response.json()
with get_db_connection().connect() as connection:
    rows=[dict(r) for r in connection.execute(text('''SELECT m.match_id,m.home_team,m.away_team,m.date,m.status,
        COUNT(DISTINCT o.bookmaker) AS bookmakers,
        COUNT(DISTINCT o.bookmaker) FILTER (WHERE o.updated_at >= TIMESTAMP '2026-10-21 18:42:00'
            AND o.updated_at < m.date) AS newly_refreshed_bookmakers
        FROM matches m LEFT JOIN odds o ON o.match_id=m.match_id
        WHERE m.match_id BETWEEN 575370 AND 575376
        GROUP BY m.match_id,m.home_team,m.away_team,m.date,m.status ORDER BY m.match_id''')).mappings()]
    imported=[dict(r) for r in connection.execute(text('''SELECT bookmaker,COUNT(*) AS quotes
        FROM odds WHERE updated_at >= TIMESTAMP '2026-10-21 18:42:00'
        AND updated_at < TIMESTAMP '2026-10-21 18:43:00'
        GROUP BY bookmaker ORDER BY bookmaker''')).mappings()]
assert len(rows)==7 and all(r['bookmakers']>0 and r['newly_refreshed_bookmakers']>0 for r in rows)
# Replay the exact archived fixtures after kickoff, without writing or treating them as upcoming.
capture=ROOT/'pipeline/data/raw/ucl_revision_20261021T184219Z'
_,records=load_grid_snapshots(capture)
fixtures=pd.DataFrame([{'match_id':r['match_id'],'date':r['date'],'home_team':r['home_team'],'away_team':r['away_team'],'competition':'UEFA Champions League'} for r in rows])
joined=matched_grid_quotes(fixtures,records)
for book in ['betpawa','cloudbet']:
    assert set(joined[joined.bookmaker.eq(book)].match_id)==set(fixtures.match_id),book
now=datetime.now(timezone.utc)
assert all(pd.Timestamp(r['kickoff'])>pd.Timestamp(now) for r in feed['items'])
report={'generated_at':now.isoformat(),'api_status':response.status_code,'upcoming_fixture_count':feed['total_count'],'catalog_sources':len(feed['bookmakers']),'displayed_fixtures_with_quotes':sum(bool(r['market']['quotes']) for r in feed['items']),'ucl_fixture_coverage':rows,'imported_quote_window':imported,'archived_exact_match_replay':{'betpawa_ucl_fixtures':7,'cloudbet_ucl_fixtures':7},'started_fixtures_excluded_from_upcoming':True}
(OUT/'bookmaker-grid-update-live-20261021.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps(report,default=str))
