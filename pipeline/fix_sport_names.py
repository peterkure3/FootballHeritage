"""
Fix sport names in backend database to match frontend expectations.
Changes "Football" to "SOCCER" for consistency.
"""

import psycopg2

conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_heritage')
cur = conn.cursor()

print("Before update:")
cur.execute('SELECT sport, COUNT(*) FROM events GROUP BY sport ORDER BY sport')
for sport, count in cur.fetchall():
    print(f'  {sport}: {count}')

# Update Football to SOCCER
print("\nUpdating 'Football' to 'SOCCER'...")
cur.execute("UPDATE events SET sport = 'SOCCER' WHERE sport = 'Football'")
affected = cur.rowcount
print(f"Updated {affected} records")

conn.commit()

print("\nAfter update:")
cur.execute('SELECT sport, COUNT(*) FROM events GROUP BY sport ORDER BY sport')
for sport, count in cur.fetchall():
    print(f'  {sport}: {count}')

conn.close()
print("\n✓ Sport names fixed!")
