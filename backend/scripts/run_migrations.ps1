# ============================================================================
#  Football Heritage - Database Migrations Runner (PowerShell)
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Database Migrations" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set database URL
$env:DATABASE_URL = "postgresql://postgres:jumpman13@localhost:5432/football_heritage"
$DB_NAME = "football_heritage"
$DB_USER = "postgres"
$DB_HOST = "localhost"
$DB_PORT = "5432"

Write-Host "Database: $DB_NAME" -ForegroundColor White
Write-Host "User:     $DB_USER" -ForegroundColor White
Write-Host "Host:     $DB_HOST`:$DB_PORT" -ForegroundColor White
Write-Host ""

# Check if PostgreSQL is accessible
Write-Host "[Step 1/3] Checking PostgreSQL connection..." -ForegroundColor Yellow
try {
    $pgVersion = psql -U $DB_USER -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ PostgreSQL is accessible" -ForegroundColor Green
    } else {
        Write-Host "✗ Cannot connect to PostgreSQL" -ForegroundColor Red
        Write-Host "Please ensure PostgreSQL is running and credentials are correct" -ForegroundColor Yellow
        pause
        exit 1
    }
} catch {
    Write-Host "✗ PostgreSQL not found or not accessible" -ForegroundColor Red
    pause
    exit 1
}

# Check if database exists
Write-Host ""
Write-Host "Checking if database exists..." -ForegroundColor Yellow
$dbExists = psql -U $DB_USER -lqt | Select-String -Pattern $DB_NAME
if (-not $dbExists) {
    Write-Host "Database does not exist. Creating..." -ForegroundColor Yellow
    psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Created database successfully!" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to create database!" -ForegroundColor Red
        pause
        exit 1
    }
} else {
    Write-Host "✓ Database already exists" -ForegroundColor Green
}

# Run migrations
Write-Host ""
Write-Host "[Step 2/3] Running migrations..." -ForegroundColor Yellow
Write-Host ""

# Check if sqlx-cli is installed
$sqlxInstalled = Get-Command sqlx -ErrorAction SilentlyContinue
if ($sqlxInstalled) {
    Write-Host "Using SQLx CLI..." -ForegroundColor Cyan
    sqlx migrate run

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Migrations completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Migration status:" -ForegroundColor Cyan
        sqlx migrate info
    } else {
        Write-Host ""
        Write-Host "✗ Migration failed!" -ForegroundColor Red
        Write-Host "Check the error messages above" -ForegroundColor Yellow
        pause
        exit 1
    }
} else {
    Write-Host "SQLx CLI not found. Installing..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Gray
    Write-Host ""

    cargo install sqlx-cli --no-default-features --features postgres

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ SQLx CLI installed successfully!" -ForegroundColor Green
        Write-Host "Running migrations..." -ForegroundColor Yellow
        Write-Host ""

        sqlx migrate run

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Migrations completed successfully!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "✗ Migration failed!" -ForegroundColor Red
            pause
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "✗ Failed to install SQLx CLI!" -ForegroundColor Red
        Write-Host "Please install manually: cargo install sqlx-cli --no-default-features --features postgres" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Verify tables
Write-Host ""
Write-Host "[Step 3/3] Verifying database schema..." -ForegroundColor Yellow
Write-Host ""

$tables = psql -U $DB_USER -d $DB_NAME -c "\dt" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $tables

    Write-Host ""
    Write-Host "Checking sample data..." -ForegroundColor Cyan
    $eventCount = psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM events;" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Sample events in database: $($eventCount.Trim())" -ForegroundColor White
    }
}

# Success summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Tables created:" -ForegroundColor Cyan
Write-Host "  ✓ users             - User accounts" -ForegroundColor White
Write-Host "  ✓ wallets           - Encrypted balances" -ForegroundColor White
Write-Host "  ✓ transactions      - Transaction history" -ForegroundColor White
Write-Host "  ✓ events            - Betting events" -ForegroundColor White
Write-Host "  ✓ bets              - User bets" -ForegroundColor White
Write-Host "  ✓ gambling_limits   - Responsible gambling" -ForegroundColor White
Write-Host "  ✓ user_activity     - Activity tracking" -ForegroundColor White
Write-Host "  ✓ betting_patterns  - Fraud detection" -ForegroundColor White
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run the application: .\run.ps1" -ForegroundColor White
Write-Host "  2. Or with cargo: cargo run --release" -ForegroundColor White
Write-Host ""

Write-Host "Database ready for use! 🚀" -ForegroundColor Green
Write-Host ""

pause
