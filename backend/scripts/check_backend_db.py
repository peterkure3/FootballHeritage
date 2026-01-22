"""Check the current state of the Football Heritage backend database."""
import psycopg2
from datetime import datetime

# Database connection
conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_heritage')
cur = conn.cursor()

print("=" * 80)
print("FOOTBALL HERITAGE DATABASE STATUS")
print("=" * 80)

# Check events table
cur.execute('SELECT COUNT(*) FROM events')
total_events = cur.fetchone()[0]
print(f"\nTotal events: {total_events}")

if total_events > 0:
    # Events by sport
    cur.execute('SELECT sport, COUNT(*) FROM events GROUP BY sport')
    print("\nEvents by sport:")
    for sport, count in cur.fetchall():
        print(f"  {sport}: {count}")
    
    # Events by status
    cur.execute('SELECT status, COUNT(*) FROM events GROUP BY status')
    print("\nEvents by status:")
    for status, count in cur.fetchall():
        print(f"  {status}: {count}")
    
    # Events by source
    cur.execute('SELECT external_source, COUNT(*) FROM events WHERE external_source IS NOT NULL GROUP BY external_source')
    print("\nEvents by source:")
    for source, count in cur.fetchall():
        print(f"  {source}: {count}")
    
    # Sample events
    cur.execute("""
        SELECT sport, league, home_team, away_team, event_date, status
        FROM events
        ORDER BY event_date DESC
        LIMIT 5
    """)
    print("\nSample events (latest 5):")
    for row in cur.fetchall():
        sport, league, home, away, date, status = row
        print(f"  {sport} - {league}: {home} vs {away} ({status}) - {date}")
else:
    print("\n⚠️  No events in database yet!")

# Check users
cur.execute('SELECT COUNT(*) FROM users')
total_users = cur.fetchone()[0]
print(f"\nTotal users: {total_users}")

# Check bets
cur.execute('SELECT COUNT(*) FROM bets')
total_bets = cur.fetchone()[0]
print(f"Total bets: {total_bets}")

print("\n" + "=" * 80)

conn.close()
