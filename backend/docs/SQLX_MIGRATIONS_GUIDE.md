# SQLx Migrations Guide for Football Heritage Backend

## Overview

This guide explains how to use SQLx migrations for the Football Heritage betting backend.

---

## What is SQLx Migrations?

SQLx has a built-in migration system that:
- ✅ Runs migrations automatically on application startup
- ✅ Tracks which migrations have been applied
- ✅ Supports rollbacks
- ✅ Works with compile-time checked queries

---

## Migration Files Location

```
backend/
└── migrations/
    └── 20241019000001_initial_schema.sql
```

Migration files are named: `{timestamp}_{description}.sql`

---

## Quick Start - Run Migrations

### Option 1: Let the Application Run Migrations (Easiest)

The application automatically runs migrations on startup!

**Steps:**

1. **Make sure database exists:**
   ```bash
   psql -U postgres -c "CREATE DATABASE football_heritage;"
   ```

2. **Run the application:**
   ```bash
   .\run.ps1
   ```

3. **Done!** Migrations run automatically.

You'll see in the logs:
```
INFO Database migrations completed successfully
```

---

### Option 2: Using SQLx CLI (Manual Control)

Install SQLx CLI:
```bash
cargo install sqlx-cli --no-default-features --features postgres
```

**Run migrations:**
```bash
# Set database URL
set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage

# Create database (if needed)
sqlx database create

# Run migrations
sqlx migrate run

# Check migration status
sqlx migrate info
```

---

## Step-by-Step Setup

### 1. Install SQLx CLI

```bash
cargo install sqlx-cli --no-default-features --features postgres
```

### 2. Set Database URL

**Windows (CMD):**
```batch
set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
```

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL = "postgresql://postgres:jumpman13@localhost:5432/football_heritage"
```

**Linux/Mac:**
```bash
export DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
```

Or add to `.env` file (already done):
```env
DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
```

### 3. Create Database

```bash
sqlx database create
```

Or manually:
```bash
psql -U postgres -c "CREATE DATABASE football_heritage;"
```

### 4. Run Migrations

```bash
sqlx migrate run
```

---

## SQLx Migration Commands

### Create a New Migration

```bash
sqlx migrate add <name>
```

Example:
```bash
sqlx migrate add add_user_preferences
```

This creates:
```
migrations/20241019120000_add_user_preferences.sql
```

### Run Migrations

```bash
sqlx migrate run
```

Applies all pending migrations.

### Revert Last Migration

```bash
sqlx migrate revert
```

**Note:** You need a `.down.sql` file for reversible migrations.

### Check Migration Status

```bash
sqlx migrate info
```

Shows which migrations have been applied.

### Force Migration Version

```bash
sqlx migrate run --target-version <version>
```

---

## Current Migration

### File: `20241019000001_initial_schema.sql`

Creates:

**Tables:**
- ✅ `users` - User accounts (21+ age verification)
- ✅ `wallets` - Encrypted wallet balances
- ✅ `transactions` - Transaction audit trail
- ✅ `events` - Sports betting events
- ✅ `bets` - User bets
- ✅ `gambling_limits` - Responsible gambling limits
- ✅ `user_activity` - Activity tracking
- ✅ `betting_patterns` - Fraud detection

**Indexes:**
- Performance indexes on all foreign keys
- Indexes on frequently queried columns

**Triggers:**
- Auto-update `updated_at` timestamps

**Sample Data:**
- 10 NFL events with realistic odds

---

## How Migrations Work in the Application

### In `main.rs`:

```rust
// Run database migrations
sqlx::migrate!("./migrations")
    .run(&db_pool)
    .await
    .map_err(|e| {
        error!("Failed to run database migrations: {}", e);
        std::io::Error::new(std::io::ErrorKind::Other, "Migration failed")
    })?;
```

This automatically runs all pending migrations when the application starts.

---

## Creating New Migrations

### Step 1: Create Migration File

```bash
sqlx migrate add add_payment_methods
```

### Step 2: Edit the File

```sql
-- migrations/20241019120000_add_payment_methods.sql

CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    method_type VARCHAR(50) NOT NULL,
    details JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_methods_user_id ON payment_methods(user_id);
```

### Step 3: Run Migration

```bash
sqlx migrate run
```

Or just restart the application - it runs automatically!

---

## Reversible Migrations

For reversible migrations, create both `.up.sql` and `.down.sql` files:

**Example:**

**File:** `20241019120000_add_payment_methods.up.sql`
```sql
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    method_type VARCHAR(50) NOT NULL
);
```

**File:** `20241019120000_add_payment_methods.down.sql`
```sql
DROP TABLE payment_methods;
```

**Revert:**
```bash
sqlx migrate revert
```

---

## Migration Tracking

SQLx creates a table `_sqlx_migrations` to track applied migrations:

```sql
SELECT * FROM _sqlx_migrations;
```

Output:
```
 version  |      description      |        installed_on         
----------+-----------------------+-----------------------------
 20241019000001 | initial_schema | 2024-10-19 12:00:00.000000
```

**Never manually modify this table!**

---

## Troubleshooting

### Error: "database does not exist"

**Solution:**
```bash
sqlx database create
```

Or:
```bash
psql -U postgres -c "CREATE DATABASE football_heritage;"
```

---

### Error: "Failed to run database migrations"

**Check:**
1. PostgreSQL is running
2. DATABASE_URL is correct
3. User has permissions
4. Database exists

**Verify connection:**
```bash
psql postgresql://postgres:jumpman13@localhost:5432/football_heritage -c "\dt"
```

---

### Error: "migration X has already been applied"

**This is fine!** SQLx tracks applied migrations and skips them.

To see status:
```bash
sqlx migrate info
```

---

### Error: "syntax error in migration"

**Check the SQL file for syntax errors:**
```bash
psql -U postgres -d football_heritage < migrations/20241019000001_initial_schema.sql
```

---

### Reset All Migrations (Danger!)

**WARNING:** This deletes all data!

```bash
# Drop database
sqlx database drop

# Recreate database
sqlx database create

# Run migrations
sqlx migrate run
```

---

## Best Practices

### 1. Never Edit Applied Migrations

Once a migration is applied (especially in production), **never edit it**.

Instead, create a new migration:
```bash
sqlx migrate add fix_user_table
```

### 2. Test Migrations Locally First

```bash
# Test on local database
sqlx migrate run

# Verify schema
psql -U postgres -d football_heritage -c "\d+ users"
```

### 3. Keep Migrations Small

One migration = one logical change

✅ Good:
```
20241019120000_add_payment_methods.sql
20241019120001_add_user_preferences.sql
```

❌ Bad:
```
20241019120000_add_everything.sql
```

### 4. Use Transactions

Migrations run in transactions by default, but be explicit:

```sql
BEGIN;

CREATE TABLE new_table (...);
CREATE INDEX idx_new_table_id ON new_table(id);

COMMIT;
```

### 5. Add Indexes in Separate Migrations (for large tables)

```bash
sqlx migrate add add_indexes_to_transactions
```

---

## Development Workflow

### Daily Development

1. Pull latest code
2. Run application (migrations run automatically)
3. Develop features
4. Create new migrations as needed

### Creating a Feature with DB Changes

1. **Create migration:**
   ```bash
   sqlx migrate add add_user_notifications
   ```

2. **Edit migration:**
   ```sql
   CREATE TABLE notifications (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID NOT NULL REFERENCES users(id),
       message TEXT NOT NULL,
       read BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. **Run migration:**
   ```bash
   sqlx migrate run
   ```
   Or just run the app: `.\run.ps1`

4. **Update models:**
   ```rust
   // src/models.rs
   #[derive(Debug, sqlx::FromRow)]
   pub struct Notification {
       pub id: Uuid,
       pub user_id: Uuid,
       pub message: String,
       pub read: bool,
       pub created_at: DateTime<Utc>,
   }
   ```

5. **Commit:**
   ```bash
   git add migrations/
   git commit -m "Add notifications table"
   ```

---

## Production Deployment

### Option 1: Automatic (on startup)

The application runs migrations automatically:

```rust
sqlx::migrate!("./migrations").run(&db_pool).await?;
```

**Pros:**
- Simple
- No manual steps

**Cons:**
- Downtime during migration
- All instances must wait for migration

### Option 2: Manual (before deployment)

Run migrations before deploying new code:

```bash
# On production server
export DATABASE_URL=postgresql://user:pass@prod-db:5432/football_heritage
sqlx migrate run
```

Then deploy application.

**Pros:**
- Control over timing
- Can run during maintenance window

**Cons:**
- Manual step
- Need SQLx CLI on production server

---

## Migration File Structure

### Naming Convention

```
{timestamp}_{description}.sql
```

Examples:
```
20241019000001_initial_schema.sql
20241019120000_add_payment_methods.sql
20241020093000_add_user_preferences.sql
```

Timestamp format: `YYYYMMDDHHmmss`

### File Content

```sql
-- Description of what this migration does

-- Enable extensions if needed
CREATE EXTENSION IF NOT EXISTS "extension_name";

-- Create tables
CREATE TABLE table_name (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- columns...
);

-- Create indexes
CREATE INDEX idx_table_column ON table_name(column);

-- Create triggers/functions if needed
CREATE OR REPLACE FUNCTION function_name()
RETURNS TRIGGER AS $$
BEGIN
    -- function body
END;
$$ LANGUAGE plpgsql;

-- Insert seed data (optional)
INSERT INTO table_name (column) VALUES ('value');
```

---

## Verifying Migrations

### Check Tables Exist

```sql
psql -U postgres -d football_heritage -c "\dt"
```

Expected output:
```
                List of relations
 Schema |       Name        | Type  |  Owner   
--------+-------------------+-------+----------
 public | bets              | table | postgres
 public | betting_patterns  | table | postgres
 public | events            | table | postgres
 public | gambling_limits   | table | postgres
 public | transactions      | table | postgres
 public | user_activity     | table | postgres
 public | users             | table | postgres
 public | wallets           | table | postgres
```

### Check Migration Status

```bash
sqlx migrate info
```

### Check Sample Data

```sql
psql -U postgres -d football_heritage -c "SELECT COUNT(*) FROM events;"
```

Should return: `10` (sample NFL events)

---

## Common Migration Patterns

### Adding a Column

```sql
-- migrations/20241019120000_add_user_timezone.sql

ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
```

### Modifying a Column

```sql
-- migrations/20241019120001_increase_email_length.sql

ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(500);
```

### Adding an Index

```sql
-- migrations/20241019120002_add_email_index.sql

CREATE INDEX idx_users_email_lower ON users(LOWER(email));
```

### Adding a Foreign Key

```sql
-- migrations/20241019120003_add_referral_system.sql

ALTER TABLE users ADD COLUMN referred_by UUID;
ALTER TABLE users ADD CONSTRAINT fk_users_referrer 
    FOREIGN KEY (referred_by) REFERENCES users(id);
```

### Dropping a Table (careful!)

```sql
-- migrations/20241019120004_remove_old_logs.sql

DROP TABLE IF EXISTS old_logs CASCADE;
```

---

## Summary

### Quick Commands

```bash
# Create database
sqlx database create

# Run migrations
sqlx migrate run

# Check status
sqlx migrate info

# Create new migration
sqlx migrate add <name>

# Revert last migration
sqlx migrate revert
```

### For Daily Development

Just run the application:
```bash
.\run.ps1
```

Migrations run automatically! ✨

---

## Current Status

✅ Migration file created: `migrations/20241019000001_initial_schema.sql`
✅ Contains complete database schema
✅ Includes sample data (10 NFL events)
✅ Application configured to run migrations automatically

**You're ready to go!** Just run `.\run.ps1` 🚀

---

**Last Updated:** October 19, 2024