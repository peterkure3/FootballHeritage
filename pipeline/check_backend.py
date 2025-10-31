"""Check backend database contents."""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_heritage')
cur = conn.cursor()

# Total events
cur.execute('SELECT COUNT(*), MIN(event_date), MAX(event_date) FROM events')
total, min_date, max_date = cur.fetchone()
print(f"Total events: {total}")
print(f"Date range: {min_date} to {max_date}")

# By sport
print("\nEvents by sport:")
cur.execute('SELECT sport, COUNT(*) FROM events GROUP BY sport ORDER BY COUNT(*) DESC')
for sport, count in cur.fetchall():
    print(f"  {sport}: {count}")

# By league
print("\nEvents by league:")
cur.execute('SELECT league, COUNT(*) FROM events WHERE sport = \'Football\' GROUP BY league ORDER BY COUNT(*) DESC')
for league, count in cur.fetchall():
    print(f"  {league}: {count}")

# By status
print("\nEvents by status:")
cur.execute('SELECT status, COUNT(*) FROM events GROUP BY status ORDER BY COUNT(*) DESC')
for status, count in cur.fetchall():
    print(f"  {status}: {count}")

# Sample upcoming events with odds
print("\nSample upcoming events with odds:")
cur.execute("""
    SELECT home_team, away_team, event_date, moneyline_home, moneyline_away 
    FROM events 
    WHERE status = 'UPCOMING' 
        AND moneyline_home IS NOT NULL 
    ORDER BY event_date 
    LIMIT 5
""")
for home, away, date, home_odds, away_odds in cur.fetchall():
    print(f"  {home} vs {away} ({date.strftime('%Y-%m-%d')})")
    if home_odds and away_odds:
        print(f"    Odds: {home} {int(home_odds):+d} | {away} {int(away_odds):+d}")

conn.close()
