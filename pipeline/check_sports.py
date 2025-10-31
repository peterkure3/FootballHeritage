import psycopg2

conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_heritage')
cur = conn.cursor()

cur.execute('SELECT DISTINCT sport FROM events ORDER BY sport')
print('Sports in backend database:')
for row in cur.fetchall():
    print(f'  - "{row[0]}"')

cur.execute('SELECT sport, COUNT(*) FROM events GROUP BY sport')
print('\nCounts:')
for sport, count in cur.fetchall():
    print(f'  {sport}: {count}')

conn.close()
