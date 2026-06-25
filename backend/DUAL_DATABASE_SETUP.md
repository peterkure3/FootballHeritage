# Dual Database Setup Guide

## Overview

The Football Heritage backend supports connecting to **two separate databases**:

1. **Primary Database** - User accounts, bets, transactions, wallets, admin logs
2. **Sports Database** - Events, odds, leagues, sports data (can be shared/external)

This allows you to:
- ✅ Separate concerns (user data vs sports data)
- ✅ Connect to an external sports data provider
- ✅ Scale databases independently
- ✅ Share sports data across multiple applications

---

## Configuration

### Environment Variables (`.env`)

```env
# Primary Database - User data, bets, transactions
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage

# Sports Database - Events, odds, leagues (can be different server)
SPORTS_DATABASE_URL=postgresql://postgres:password@localhost:5432/sports_data
```

**Note:** If `SPORTS_DATABASE_URL` is not set, it defaults to `DATABASE_URL` (same database).

---

## Database Schema Split

### Primary Database Tables
```sql
- users
- bets
- transactions
- wallets
- admin_logs
- sessions
- fraud_alerts
```

### Sports Database Tables
```sql
- events
- leagues
- sports
- odds_history
- teams
```

---

## Implementation

### 1. Database Pools Module (`src/db.rs`)

```rust
use crate::db::DatabasePools;

// Initialize dual database pools
let db_pools = DatabasePools::new(
    &config.database_url,
    &config.sports_database_url
).await?;

// Use in handlers
let primary_pool = db_pools.primary();  // For users, bets
let sports_pool = db_pools.sports();    // For events, odds
```

### 2. Update Handlers

**Before (single database):**
```rust
pub async fn get_events(pool: web::Data<PgPool>) -> HttpResponse {
    sqlx::query!("SELECT * FROM events")
        .fetch_all(pool.get_ref())
        .await
}
```

**After (dual database):**
```rust
pub async fn get_events(pools: web::Data<DatabasePools>) -> HttpResponse {
    sqlx::query!("SELECT * FROM events")
        .fetch_all(pools.sports())  // Use sports database
        .await
}
```

### 3. Update main.rs

```rust
use crate::db::DatabasePools;

// Replace single pool with dual pools
let db_pools = DatabasePools::new(
    &config.database_url,
    &config.sports_database_url
).await?;

// Pass to app
HttpServer::new(move || {
    App::new()
        .app_data(web::Data::new(db_pools.clone()))
        // ...
})
```

---

## Migration Strategy

### Option A: Same Database (Default)
Keep both schemas in one database:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage
SPORTS_DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage
```

### Option B: Separate Databases
Split into two databases:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage
SPORTS_DATABASE_URL=postgresql://postgres:password@localhost:5432/sports_data
```

### Option C: External Sports Database
Connect to a remote sports data provider:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage
SPORTS_DATABASE_URL=postgresql://sports_user:password@external-server.com:5432/sports_api
```

---

## Handlers to Update

### Use Sports Database:
- `handlers/sports.rs` - Get sports, leagues
- `handlers/admin/events.rs` - CRUD operations on events
- `handlers/betting.rs` - Get events for betting (read-only)

### Use Primary Database:
- `handlers/auth.rs` - User authentication
- `handlers/betting.rs` - Place bets, get user bets
- `handlers/wallet.rs` - Deposits, withdrawals
- `handlers/admin/users.rs` - User management
- `handlers/admin/bets.rs` - Bet management

### Use Both Databases:
- `handlers/betting.rs` - Fetch events (sports DB) + create bet (primary DB)
- `handlers/admin/analytics.rs` - Join user data + event data

---

## Example: Cross-Database Query

```rust
pub async fn place_bet(
    pools: web::Data<DatabasePools>,
    body: web::Json<PlaceBetRequest>,
) -> HttpResponse {
    // 1. Get event from sports database
    let event = sqlx::query!("SELECT * FROM events WHERE id = $1", body.event_id)
        .fetch_one(pools.sports())
        .await?;

    // 2. Create bet in primary database
    let bet = sqlx::query!(
        "INSERT INTO bets (user_id, event_id, stake) VALUES ($1, $2, $3)",
        user_id, event.id, body.stake
    )
    .execute(pools.primary())
    .await?;

    Ok(HttpResponse::Ok().json(bet))
}
```

---

## BetPawa Integration

The `import_betpawa_data.js` script can import directly to the sports database:

```javascript
const pool = new Pool({
  connectionString: process.env.SPORTS_DATABASE_URL || process.env.DATABASE_URL
});
```

---

## Benefits

### 1. **Scalability**
- Scale user database and sports database independently
- Different read/write patterns optimized separately

### 2. **Security**
- Isolate sensitive user data from public sports data
- Different access controls per database

### 3. **Data Sharing**
- Multiple apps can share the same sports database
- Centralized sports data management

### 4. **Performance**
- Dedicated connection pools per database
- Reduce contention on primary database

### 5. **Flexibility**
- Easy to switch sports data providers
- Can use external APIs as sports database

---

## Testing

### Test with Same Database
```bash
DATABASE_URL=postgresql://localhost/test_db
SPORTS_DATABASE_URL=postgresql://localhost/test_db
cargo test
```

### Test with Separate Databases
```bash
DATABASE_URL=postgresql://localhost/test_primary
SPORTS_DATABASE_URL=postgresql://localhost/test_sports
cargo test
```

---

## Deployment

### Docker Compose Example

```yaml
version: '3.8'
services:
  primary_db:
    image: postgres:15
    environment:
      POSTGRES_DB: football_heritage
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  sports_db:
    image: postgres:15
    environment:
      POSTGRES_DB: sports_data
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"

  backend:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:password@primary_db:5432/football_heritage
      SPORTS_DATABASE_URL: postgresql://postgres:password@sports_db:5432/sports_data
```

---

## Rollback

To revert to single database, simply:

1. Set both URLs to the same database:
```env
DATABASE_URL=postgresql://localhost/football_heritage
SPORTS_DATABASE_URL=postgresql://localhost/football_heritage
```

2. The `DatabasePools` module will automatically reuse the same connection pool.

---

## Next Steps

1. ✅ Update `.env` with `SPORTS_DATABASE_URL`
2. ✅ Create sports database (if separate)
3. ✅ Run migrations on both databases
4. ✅ Update handlers to use `DatabasePools`
5. ✅ Test with both configurations
6. ✅ Deploy

---

## Questions?

- **Q: Do I need two databases?**  
  A: No, you can use the same database. Just set both URLs to the same value.

- **Q: Can I use a remote sports database?**  
  A: Yes! Set `SPORTS_DATABASE_URL` to any PostgreSQL connection string.

- **Q: What about transactions across databases?**  
  A: PostgreSQL doesn't support distributed transactions. Use application-level transaction management or keep related data in the same database.

- **Q: Performance impact?**  
  A: Minimal if using the same database. Separate databases may have network latency but better isolation.
