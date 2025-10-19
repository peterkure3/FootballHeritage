# Quick Start Guide - Football Heritage Backend

Get the betting service running in 5 minutes! 🚀

## Prerequisites

- ✅ Rust (1.70+) - [Install from rustup.rs](https://rustup.rs/)
- ✅ PostgreSQL (12+) - [Download](https://www.postgresql.org/download/)
- ✅ Git

## 1. Clone & Navigate

```bash
git clone <repository-url>
cd FootballHeritgae/backend
```

## 2. Environment Setup

### Option A: Automatic (Recommended)

**Windows:**
```batch
setup_dev.bat
```

**Linux/Mac:**
```bash
chmod +x setup_dev.sh
./setup_dev.sh
```

### Option B: Manual

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and set these critical values:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage_betting
JWT_SECRET=<generate-random-64-char-string>
ENCRYPTION_KEY=<generate-random-32-byte-base64-string>
```

**Generate secure keys:**
```bash
# JWT Secret (64 bytes)
openssl rand -base64 64

# Encryption Key (32 bytes)
openssl rand -base64 32
```

## 3. Database Setup

### Create Database
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE football_heritage_betting;
\q
```

### Apply Schema
```bash
psql -U postgres -d football_heritage_betting -f schema.sql
```

You should see:
```
CREATE DATABASE
CREATE EXTENSION
CREATE TABLE (multiple times)
CREATE INDEX (multiple times)
INSERT 0 10 (sample NFL games)
```

## 4. Build & Run

```bash
# Install dependencies and build
cargo build

# Run the server
cargo run
```

Expected output:
```
🏈 Football Heritage Betting API
Server running on http://127.0.0.1:8080
Database: Connected ✓
Encryption: Enabled ✓
Rate Limiting: Active ✓
```

## 5. Verify It Works

### Check Health Endpoint
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database": "connected"
}
```

### View Available Events
```bash
curl http://localhost:8080/api/events
```

Should return 10 pre-populated NFL games with odds.

## 🎯 Quick Test - Place a Bet

### 1. Register a User
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Save the JWT token from response.

### 3. Deposit Funds
```bash
curl -X POST http://localhost:8080/api/wallet/deposit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "amount": "1000.00",
    "description": "Initial deposit"
  }'
```

### 4. Place Bet
```bash
# First, get an event ID from /api/events
# Then place bet:

curl -X POST http://localhost:8080/api/bets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "event_id": "<event-uuid-from-events>",
    "bet_type": "moneyline",
    "selection": "home",
    "odds": "1.85",
    "amount": "50.00"
  }'
```

## 🔧 Development Tools

### Hot Reload
```bash
# Install cargo-watch
cargo install cargo-watch

# Run with auto-reload
cargo watch -x run
```

### Run Tests
```bash
# All tests
cargo test

# Specific module
cargo test betting_simple

# With output
cargo test -- --nocapture
```

### Code Quality
```bash
# Format code
cargo fmt

# Lint
cargo clippy

# Check compilation without building
cargo check
```

## 📚 What's Included

### Pre-populated Data
- ✅ 10 NFL games with realistic odds
- ✅ Moneyline, spread, and totals for each game
- ✅ Events dated 2-11 days in the future

### Features Ready
- ✅ User registration with age verification (21+)
- ✅ JWT authentication
- ✅ Encrypted wallet balances (AES-256-GCM)
- ✅ Bet placement (moneyline, spread, over/under)
- ✅ Responsible gambling limits
- ✅ Fraud detection
- ✅ Complete transaction audit trail
- ✅ Rate limiting

## 📖 Next Steps

### Essential Reading
1. **BETTING_SERVICE_GUIDE.md** - Complete API documentation
2. **SIMPLIFIED_BETTING_README.md** - Service architecture
3. **QUICK_REFERENCE.md** - Code snippets and examples

### Using the Simplified Betting Service

The new `SimpleBettingService` is production-ready:

```rust
use crate::betting_simple::SimpleBettingService;
use crate::crypto::CryptoService;

// Initialize
let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
let betting_service = SimpleBettingService::new(crypto_service);

// Place bet
let bet = betting_service.place_bet(&pool, user_id, bet_request).await?;
```

See `examples/betting_integration.rs` for complete examples.

## 🐛 Troubleshooting

### "DATABASE_URL must be set"
- ✅ Check `.env` file exists
- ✅ Verify `DATABASE_URL` is set correctly
- ✅ Test connection: `psql "$DATABASE_URL"`

### "Connection refused"
- ✅ PostgreSQL is running: `pg_ctl status`
- ✅ Port 5432 is available
- ✅ Check firewall settings

### "Encryption key must be exactly 32 bytes"
- ✅ Generate new key: `openssl rand -base64 32`
- ✅ Paste entire output into `ENCRYPTION_KEY` in `.env`

### Compilation Errors
```bash
# Clean and rebuild
cargo clean
cargo build
```

### "sqlx-postgres" Warning
This is a future compatibility warning, safe to ignore for now.
Can be addressed by updating sqlx in the future.

## 🔒 Security Checklist

Before deploying to production:

- [ ] Change all default credentials
- [ ] Use strong, random JWT_SECRET (64+ chars)
- [ ] Use strong, random ENCRYPTION_KEY (32 bytes)
- [ ] Enable HTTPS/TLS in production
- [ ] Set `HTTPS_ENABLED=true`
- [ ] Use proper TLS certificates (not self-signed)
- [ ] Configure CORS allowed origins
- [ ] Set appropriate rate limits
- [ ] Enable database SSL connection
- [ ] Review and set gambling limits
- [ ] Configure fraud detection thresholds
- [ ] Set up monitoring and alerting
- [ ] Regular database backups
- [ ] Never commit `.env` to version control

## 📞 Support

### Documentation
- **Complete Guide**: `BETTING_SERVICE_GUIDE.md`
- **API Reference**: See code examples in `examples/`
- **Deployment**: `DEPLOYMENT_CHECKLIST.md`
- **Technical Details**: `TRANSACTION_FIXES.md`

### Common Issues
1. Check error logs: `RUST_LOG=debug cargo run`
2. Verify database schema matches `schema.sql`
3. Test database connection independently
4. Ensure all required fields in `.env` are set

### Getting Help
1. Review documentation above
2. Check GitHub issues
3. Review error logs with debug logging enabled
4. Verify environment configuration

## 🎉 You're Ready!

Your sports betting backend is now running with:
- ✅ Secure authentication (JWT)
- ✅ Encrypted wallet balances
- ✅ ACID-compliant transactions
- ✅ Fraud detection
- ✅ Responsible gambling limits
- ✅ Complete audit trail

**Start betting with confidence!** 🏈💰

---

**Quick Commands Reference:**

```bash
# Development
cargo run                    # Start server
cargo test                   # Run tests
cargo watch -x run           # Hot reload

# Database
psql "$DATABASE_URL"         # Connect to DB
psql -f schema.sql          # Apply schema

# Code Quality
cargo fmt                    # Format
cargo clippy                 # Lint
cargo check                  # Quick check

# Production
cargo build --release        # Optimized build
```

**Happy Coding! 🚀**