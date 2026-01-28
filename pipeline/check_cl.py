from sqlalchemy import create_engine, text
from config import DATABASE_URI

db = create_engine(DATABASE_URI)
conn = db.connect()

print("=== Recent CL matches ===")
r = conn.execute(text("SELECT m.match_id, m.home_team, m.away_team, m.date, m.result, m.home_score, m.away_score FROM matches m WHERE m.competition ILIKE '%champion%' ORDER BY m.match_id DESC LIMIT 10"))
for row in r.fetchall():
    print(dict(row._mapping))

print("\n=== CL matches with predictions ===")
r2 = conn.execute(text("SELECT m.match_id, m.home_team, m.away_team, m.date, m.result, p.winner FROM matches m JOIN predictions p ON m.match_id = p.match_id WHERE m.competition ILIKE '%champion%' AND m.result IS NOT NULL ORDER BY m.match_id DESC LIMIT 10"))
for row in r2.fetchall():
    print(dict(row._mapping))

print("\n=== CL matches WITHOUT predictions ===")
r3 = conn.execute(text("SELECT m.match_id, m.home_team, m.away_team, m.date, m.result FROM matches m LEFT JOIN predictions p ON m.match_id = p.match_id WHERE m.competition ILIKE '%champion%' AND p.match_id IS NULL ORDER BY m.match_id DESC LIMIT 10"))
for row in r3.fetchall():
    print(dict(row._mapping))

conn.close()
