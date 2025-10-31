import psycopg2

conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_betting')
cur = conn.cursor()

# Check tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
print("Tables in pipeline database:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

print("\nMatches table columns:")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'matches' ORDER BY ordinal_position")
for row in cur.fetchall():
    print(f"  - {row[0]}")

# Check if odds table exists
cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'odds')")
has_odds = cur.fetchone()[0]

if has_odds:
    print("\nOdds table columns:")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'odds' ORDER BY ordinal_position")
    for row in cur.fetchall():
        print(f"  - {row[0]}")

conn.close()
