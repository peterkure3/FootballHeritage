"""Quick script to check database contents."""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_betting')
cur = conn.cursor()

# Total matches
cur.execute('SELECT COUNT(*), COUNT(DISTINCT competition), MIN(date), MAX(date) FROM matches')
total, comps, min_date, max_date = cur.fetchone()
print(f"Total matches: {total}")
print(f"Competitions: {comps}")
print(f"Date range: {min_date} to {max_date}")

# By competition
print("\nMatches by competition:")
cur.execute('SELECT competition, COUNT(*) FROM matches GROUP BY competition ORDER BY COUNT(*) DESC LIMIT 10')
for comp, count in cur.fetchall():
    print(f"  {comp}: {count}")

# Upcoming matches
cur.execute("SELECT COUNT(*) FROM matches WHERE status = 'SCHEDULED'")
print(f"\nUpcoming matches: {cur.fetchone()[0]}")

# Recent matches with results
cur.execute("""
    SELECT home_team, away_team, home_score, away_score, date 
    FROM matches 
    WHERE result IS NOT NULL 
    ORDER BY date DESC 
    LIMIT 5
""")
print("\nRecent completed matches:")
for home, away, h_score, a_score, date in cur.fetchall():
    print(f"  {home} {h_score}-{a_score} {away} ({date.strftime('%Y-%m-%d')})")

conn.close()
