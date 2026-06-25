# Football Heritage Database Migration

## Overview

This script migrates all data from your current `football_betting` database to a new `football_heritage` database.

## What It Does

1. **Creates** the `football_heritage` database
2. **Creates** all necessary tables (matches, odds, predictions)
3. **Copies** all data from source to target
4. **Verifies** data integrity
5. **Reports** migration summary

## Quick Start

### Run the Migration

```bash
python load_to_heritage_db.py
```

### Expected Output

```
================================================================================
FOOTBALL HERITAGE DATABASE MIGRATION
================================================================================
Source: football_betting
Target: football_heritage
================================================================================

Step 1: Creating target database...
✓ Database 'football_heritage' created successfully

Step 2: Creating schema...
✓ Schema created successfully

Step 3: Copying data...
Copying data from 'matches' table...
Found 406 records in 'matches'
  Inserted 406/406 records...
✓ Successfully copied 406 records from 'matches'

Copying data from 'odds' table...
Found 608 records in 'odds'
  Inserted 608/608 records...
✓ Successfully copied 608 records from 'odds'

Copying data from 'predictions' table...
Found 14 records in 'predictions'
  Inserted 14/14 records...
✓ Successfully copied 14 records from 'predictions'

✓ Total records copied: 1028

Step 4: Verifying data integrity...
✓ matches: Source=406, Target=406
✓ odds: Source=608, Target=608
✓ predictions: Source=14, Target=14

✓ All data verified successfully!

================================================================================
MIGRATION SUMMARY
================================================================================
Matches:     406
Odds:        608
Predictions: 14
================================================================================
✓ Migration completed successfully!
================================================================================
```

## Database Schema

The `football_heritage` database will have the same schema as the source:

### Tables

1. **matches** - Match data with team form features
2. **odds** - Betting odds from various bookmakers
3. **predictions** - ML model predictions

### Indexes

- `idx_matches_date` - For date-based queries
- `idx_matches_teams` - For team-based queries
- `idx_odds_match` - For odds lookups
- `idx_predictions_match` - For prediction lookups

## Configuration

### Using Heritage Database in Your Code

#### Option 1: Use heritage_config.py

```python
from heritage_config import DATABASE_URI

from sqlalchemy import create_engine

engine = create_engine(DATABASE_URI)
# Now connected to football_heritage
```

#### Option 2: Direct Connection

```python
from sqlalchemy import create_engine

DATABASE_URI = "postgresql://user:password@localhost:5432/football_heritage"
engine = create_engine(DATABASE_URI)
```

## Connecting API to Heritage Database

### Temporary Switch

Edit `.env` file:

```bash
# Change this line:
DB_NAME=football_betting

# To this:
DB_NAME=football_heritage
```

Then restart the API:

```bash
python -m api.main
```

### Permanent Separate API

Create a new API instance for heritage database:

```python
# api/heritage_main.py
from fastapi import FastAPI
from heritage_config import DATABASE_URI

app = FastAPI(title="Football Heritage API")

# Use DATABASE_URI from heritage_config
# ... rest of your API code
```

Run on different port:

```bash
uvicorn api.heritage_main:app --port 8001
```

## Use Cases

### 1. Backup Database

Keep `football_heritage` as a backup while you work on `football_betting`:

```bash
# Migrate current data
python load_to_heritage_db.py

# Continue working with football_betting
# Heritage DB remains unchanged
```

### 2. Historical Archive

Use `football_heritage` for long-term storage:

```python
# Query historical data
from sqlalchemy import create_engine
import pandas as pd

heritage_uri = "postgresql://user:pass@localhost:5432/football_heritage"
engine = create_engine(heritage_uri)

# Get all historical matches
df = pd.read_sql("SELECT * FROM matches ORDER BY date", engine)
print(f"Total historical matches: {len(df)}")
```

### 3. A/B Testing

Compare different models or data:

- `football_betting` - Current/experimental data
- `football_heritage` - Stable/production data

### 4. Multi-Tenant Setup

Serve different clients from different databases:

```python
# Client A uses football_betting
# Client B uses football_heritage

def get_engine(client_id):
    if client_id == "client_a":
        return create_engine("postgresql://...football_betting")
    else:
        return create_engine("postgresql://...football_heritage")
```

## Verification Queries

### Check Record Counts

```sql
-- In football_heritage database
SELECT 
    (SELECT COUNT(*) FROM matches) as matches,
    (SELECT COUNT(*) FROM odds) as odds,
    (SELECT COUNT(*) FROM predictions) as predictions;
```

### Compare Databases

```sql
-- Run in both databases and compare
SELECT 
    home_team,
    away_team,
    date,
    result
FROM matches
ORDER BY date DESC
LIMIT 10;
```

### Check Data Integrity

```sql
-- Verify foreign keys
SELECT COUNT(*) 
FROM odds o
LEFT JOIN matches m ON o.match_id = m.match_id
WHERE m.match_id IS NULL;
-- Should return 0

SELECT COUNT(*) 
FROM predictions p
LEFT JOIN matches m ON p.match_id = m.match_id
WHERE m.match_id IS NULL;
-- Should return 0
```

## Troubleshooting

### Database Already Exists

If you get "database already exists" error:

```bash
# Option 1: Drop and recreate
psql -U postgres -c "DROP DATABASE football_heritage;"
python load_to_heritage_db.py

# Option 2: Append data (modify script to use if_exists='append')
```

### Permission Denied

Make sure your PostgreSQL user has CREATE DATABASE permission:

```sql
-- Run as postgres superuser
ALTER USER your_username CREATEDB;
```

### Connection Refused

Check PostgreSQL is running:

```bash
# Windows
pg_ctl status

# Linux/Mac
sudo systemctl status postgresql
```

### Data Mismatch

If verification fails, check:

1. Source database has data: `SELECT COUNT(*) FROM matches;`
2. No errors during copy (check logs)
3. Network/connection stable during migration

## Advanced Options

### Selective Migration

Modify the script to copy only specific data:

```python
# In copy_table_data function, add WHERE clause
query = f"SELECT * FROM {table_name} WHERE date >= '2024-01-01'"
```

### Custom Transformations

Add data transformations during migration:

```python
# After reading from source
df = pd.read_sql(query, source_engine)

# Transform data
df['competition'] = df['competition'].str.upper()
df['home_team'] = df['home_team'].str.strip()

# Write to target
df.to_sql(table_name, target_engine, if_exists='append', index=False)
```

### Incremental Updates

Copy only new data:

```python
# Get max date from target
max_date = pd.read_sql(
    "SELECT MAX(date) FROM matches", 
    target_engine
).iloc[0][0]

# Copy only newer records
query = f"SELECT * FROM matches WHERE date > '{max_date}'"
```

## Maintenance

### Regular Backups

Schedule regular migrations:

```bash
# Windows Task Scheduler
# Linux cron job
0 2 * * 0 /usr/bin/python /path/to/load_to_heritage_db.py
```

### Cleanup Old Data

```sql
-- Remove old predictions
DELETE FROM predictions 
WHERE created_at < NOW() - INTERVAL '30 days';

-- Vacuum to reclaim space
VACUUM FULL predictions;
```

## Summary

The `load_to_heritage_db.py` script provides:

✅ **Automated** database creation  
✅ **Complete** schema setup  
✅ **Batch** data copying  
✅ **Integrity** verification  
✅ **Detailed** logging  
✅ **Error** handling  

Perfect for backups, archives, and multi-database setups! 🗄️
