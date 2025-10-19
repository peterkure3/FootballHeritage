# How to Run the Football Heritage Backend

## Prerequisites

1. ✅ **PostgreSQL Database** running on `localhost:5432`
2. ✅ **Database created**: `football_heritage`
3. ✅ **Optimized binary built**: `target/release/football-heritage-backend.exe`

---

## Quick Start

### Option 1: Using Environment Variables (Recommended)

```batch
# Windows CMD
set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
set JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
set ENCRYPTION_KEY=12345678901234567890123456789012
target\release\football-heritage-backend.exe
```

```bash
# Linux/Mac
export DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
export JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
export ENCRYPTION_KEY=12345678901234567890123456789012
./target/release/football-heritage-backend
```

### Option 2: Using .env File

The application looks for a `.env` file in the **current working directory** when it starts.

**Important**: Make sure you run the application from the `backend` directory!

```batch
# Windows
cd D:\Github\FootballHeritgae\backend
cargo run --release
```

```bash
# Linux/Mac
cd /path/to/FootballHeritgae/backend
cargo run --release
```

### Option 3: Using the run.bat Script (Windows)

```batch
run.bat
```

This script automatically:
1. Sets the working directory
2. Loads variables from `.env`
3. Runs the application

---

## Environment Variables Required

### Minimum Required Variables

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
ENCRYPTION_KEY=12345678901234567890123456789012
```

### All Available Variables (with defaults)

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_heritage

# Authentication
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
JWT_EXPIRATION_HOURS=24

# Encryption
ENCRYPTION_KEY=12345678901234567890123456789012

# Server
HOST=127.0.0.1
PORT=8080
HTTPS_ENABLED=false

# TLS (if HTTPS_ENABLED=true)
TLS_CERT_PATH=./certs/server.crt
TLS_KEY_PATH=./certs/server.key

# Rate Limiting
BET_RATE_LIMIT_PER_MINUTE=5
LOGIN_RATE_LIMIT_PER_MINUTE=10
REGISTER_RATE_LIMIT_PER_HOUR=5

# Security
BCRYPT_COST=12
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCK_MINUTES=15

# Betting Limits (default values)
DEFAULT_DAILY_LOSS_LIMIT=1000.00
DEFAULT_WEEKLY_LOSS_LIMIT=5000.00
DEFAULT_MONTHLY_LOSS_LIMIT=15000.00
DEFAULT_DAILY_BET_LIMIT=2000.00
DEFAULT_WEEKLY_BET_LIMIT=10000.00
DEFAULT_MONTHLY_BET_LIMIT=30000.00
DEFAULT_MAX_SINGLE_BET=500.00

# Monitoring
LOG_LEVEL=info
FRAUD_ALERT_EMAIL=security@footballheritage.com
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL_SECONDS=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## Troubleshooting

### Error: "DATABASE_URL must be set"

**Cause**: The `.env` file is not being loaded, or you're running from the wrong directory.

**Solutions**:

1. **Check your current directory**:
   ```batch
   # Make sure you're in the backend folder
   cd D:\Github\FootballHeritgae\backend
   pwd  # Should show: /d/Github/FootballHeritgae/backend
   ```

2. **Verify .env file exists**:
   ```batch
   ls -la .env
   # Should show: -rw-r--r-- 1 User 197121 1274 Oct 19 16:20 .env
   ```

3. **Set variables manually**:
   ```batch
   set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
   set JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
   set ENCRYPTION_KEY=12345678901234567890123456789012
   target\release\football-heritage-backend.exe
   ```

4. **Use the run.bat script** (loads .env automatically)

### Error: "Failed to connect to database"

**Cause**: PostgreSQL is not running or connection details are wrong.

**Solutions**:

1. **Check PostgreSQL is running**:
   ```batch
   # Windows
   sc query postgresql-x64-14  # Or your PostgreSQL service name
   
   # Linux/Mac
   sudo systemctl status postgresql
   ```

2. **Test database connection**:
   ```batch
   psql -U postgres -h localhost -d football_heritage
   ```

3. **Verify connection string**:
   - Username: `postgres`
   - Password: `jumpman13`
   - Host: `localhost`
   - Port: `5432`
   - Database: `football_heritage`

4. **Check if database exists**:
   ```sql
   psql -U postgres -c "\l" | grep football_heritage
   ```

5. **Create database if needed**:
   ```sql
   psql -U postgres -c "CREATE DATABASE football_heritage;"
   ```

### Error: "JWT_SECRET must be set"

**Cause**: JWT_SECRET environment variable is missing or too short.

**Solution**:
```batch
set JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
```

**Note**: JWT_SECRET must be at least 32 characters long for security.

### Error: "ENCRYPTION_KEY must be set"

**Cause**: ENCRYPTION_KEY environment variable is missing or wrong length.

**Solution**:
```batch
set ENCRYPTION_KEY=12345678901234567890123456789012
```

**Note**: ENCRYPTION_KEY must be exactly 32 characters (for AES-256).

### Error: "Failed to run database migrations"

**Cause**: Database exists but migrations haven't run.

**Solution**:
```batch
# Run migrations manually
sqlx migrate run
```

Or the application will run them automatically on startup if it can connect.

---

## Development vs Production

### Development (with live reload)

```batch
# Uses .env file automatically
cargo run

# Or with logs
RUST_LOG=debug cargo run
```

### Production (optimized binary)

```batch
# Make sure you're in backend directory
cd D:\Github\FootballHeritgae\backend

# Run the optimized binary
target\release\football-heritage-backend.exe
```

---

## Running with Docker (Optional)

If you want to containerize the application:

```dockerfile
# See Dockerfile for full setup
docker build -t football-heritage-backend .
docker run -p 8080:8080 --env-file .env football-heritage-backend
```

---

## Verifying the Application is Running

### 1. Check the logs

You should see:
```
INFO Starting Football Heritage Betting API Server
INFO Environment: Development
INFO Database connection pool initialized successfully
INFO Database migrations completed successfully
INFO Starting server on 127.0.0.1:8080
```

### 2. Test the health endpoint

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-19T13:30:00Z"
}
```

### 3. Test an API endpoint

```bash
# Register a user
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "phone": "+1234567890",
    "address": "123 Main St"
  }'
```

---

## Production Deployment Checklist

- [ ] Use strong, unique JWT_SECRET (min 32 chars)
- [ ] Use strong, unique ENCRYPTION_KEY (exactly 32 chars)
- [ ] Change default database password
- [ ] Enable HTTPS (set HTTPS_ENABLED=true)
- [ ] Configure proper TLS certificates
- [ ] Set appropriate rate limits
- [ ] Configure production ALLOWED_ORIGINS
- [ ] Set LOG_LEVEL=info or LOG_LEVEL=warn
- [ ] Enable METRICS_ENABLED=true
- [ ] Configure FRAUD_ALERT_EMAIL
- [ ] Use environment variables (not .env file)
- [ ] Run as a service/systemd unit
- [ ] Set up database backups
- [ ] Configure monitoring and alerting

---

## Running as a Windows Service

Create a service wrapper script:

```batch
@echo off
REM Service wrapper for Football Heritage Backend

:loop
cd D:\Github\FootballHeritgae\backend
target\release\football-heritage-backend.exe
echo "Service crashed, restarting in 5 seconds..."
timeout /t 5
goto loop
```

Or use tools like `nssm` (Non-Sucking Service Manager):

```batch
nssm install FootballHeritage "D:\Github\FootballHeritgae\backend\target\release\football-heritage-backend.exe"
nssm set FootballHeritage AppDirectory "D:\Github\FootballHeritgae\backend"
nssm start FootballHeritage
```

---

## Running as a Linux Systemd Service

Create `/etc/systemd/system/football-heritage.service`:

```ini
[Unit]
Description=Football Heritage Betting Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/football-heritage/backend
EnvironmentFile=/opt/football-heritage/backend/.env
ExecStart=/opt/football-heritage/backend/target/release/football-heritage-backend
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable football-heritage
sudo systemctl start football-heritage
sudo systemctl status football-heritage
```

---

## Summary

**Easiest way to run**:

1. Make sure you're in the backend directory
2. Make sure PostgreSQL is running
3. Run: `cargo run --release`

**Or**:

1. Set environment variables manually
2. Run: `target\release\football-heritage-backend.exe`

**The optimized 4.7 MB binary is ready to deploy!** 🚀

---

## Need Help?

- Check logs for detailed error messages
- Verify all environment variables are set
- Ensure PostgreSQL is running and accessible
- Test database connection with `psql`
- Make sure you're in the correct directory

For more details, see:
- `BUILD_OPTIMIZATION.md` - Build configuration
- `QUICKSTART.md` - General setup guide
- `schema.sql` - Database schema