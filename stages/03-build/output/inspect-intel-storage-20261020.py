import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'pipeline'))
from api.db import engine,heritage_engine
from sqlalchemy import text
for label,db in [('pipeline',engine),('heritage',heritage_engine)]:
    with db.connect() as c:
        columns=c.execute(text("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('events','odds_offers','player_props','nba_games','matches') ORDER BY table_name,ordinal_position")).mappings().all()
        print(json.dumps({'database':label,'columns':[dict(x) for x in columns]}))
        if label=='heritage':
            print(json.dumps({'event_groups':[dict(x) for x in c.execute(text('SELECT sport,league,COUNT(*) FROM events GROUP BY sport,league ORDER BY COUNT(*) DESC LIMIT 16')).mappings()]}))
