# Reset Database Migrations Script
# This script drops and recreates the database to fix migration conflicts

Write-Host "🔄 Database Migration Reset Script" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Load .env file
if (Test-Path ".env") {
    Write-Host "📁 Loading environment variables from .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Host "❌ Error: .env file not found!" -ForegroundColor Red
    exit 1
}

$DATABASE_URL = $env:DATABASE_URL

if (-not $DATABASE_URL) {
    Write-Host "❌ Error: DATABASE_URL not set in .env!" -ForegroundColor Red
    exit 1
}

# Parse database URL to get connection details
if ($DATABASE_URL -match "postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)") {
    $DB_USER = $matches[1]
    $DB_PASS = $matches[2]
    $DB_HOST = $matches[3]
    $DB_PORT = $matches[4]
    $DB_NAME = $matches[5]
} else {
    Write-Host "❌ Error: Could not parse DATABASE_URL!" -ForegroundColor Red
    Write-Host "   Format should be: postgresql://user:pass@host:port/dbname" -ForegroundColor Yellow
    exit 1
}

Write-Host "📊 Database Information:" -ForegroundColor Cyan
Write-Host "   Host: $DB_HOST" -ForegroundColor White
Write-Host "   Port: $DB_PORT" -ForegroundColor White
Write-Host "   Database: $DB_NAME" -ForegroundColor White
Write-Host "   User: $DB_USER" -ForegroundColor White
Write-Host ""

# Warn user
Write-Host "⚠️  WARNING: This will DROP and RECREATE the database!" -ForegroundColor Yellow
Write-Host "   All data will be LOST!" -ForegroundColor Yellow
Write-Host ""

# Ask for confirmation
$confirmation = Read-Host "Type 'YES' to continue"

if ($confirmation -ne "YES") {
    Write-Host "❌ Cancelled by user" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🗑️  Step 1: Dropping existing database..." -ForegroundColor Yellow

# Set PGPASSWORD environment variable for psql
$env:PGPASSWORD = $DB_PASS

# Drop database (connect to postgres database)
$dropCmd = "DROP DATABASE IF EXISTS $DB_NAME;"
echo $dropCmd | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Database dropped" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Database might not exist (this is OK)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📦 Step 2: Creating new database..." -ForegroundColor Yellow

# Create database
$createCmd = "CREATE DATABASE $DB_NAME;"
echo $createCmd | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Database created" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to create database" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔧 Step 3: Running migrations..." -ForegroundColor Yellow

# Check if sqlx CLI is installed
$sqlxInstalled = Get-Command sqlx -ErrorAction SilentlyContinue

if ($sqlxInstalled) {
    Write-Host "   Using sqlx CLI..." -ForegroundColor Gray
    sqlx migrate run

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Migrations completed successfully" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Migrations failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   sqlx CLI not found, migrations will run on app startup" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Database reset completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update backend/.env with HOST=0.0.0.0" -ForegroundColor White
Write-Host "  2. Run: .\run.ps1" -ForegroundColor White
Write-Host "  3. Backend will run migrations on startup" -ForegroundColor White
Write-Host "  4. Register new user in browser" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Clean up
Remove-Item Env:\PGPASSWORD
