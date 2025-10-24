# PowerShell script to run database migration
# Usage: .\run_migration.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Football Heritage - Database Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables
if (Test-Path .env) {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "  Set $key" -ForegroundColor Gray
        }
    }
    Write-Host ""
} else {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    exit 1
}

$DATABASE_URL = $env:DATABASE_URL

if (-not $DATABASE_URL) {
    Write-Host "ERROR: DATABASE_URL not set in .env file!" -ForegroundColor Red
    exit 1
}

Write-Host "Database: $DATABASE_URL" -ForegroundColor Green
Write-Host ""

# Find the latest migration file
$migrationFile = Get-ChildItem -Path "migrations" -Filter "*.sql" | Sort-Object Name -Descending | Select-Object -First 1

if (-not $migrationFile) {
    Write-Host "ERROR: No migration files found in migrations folder!" -ForegroundColor Red
    exit 1
}

Write-Host "Running migration: $($migrationFile.Name)" -ForegroundColor Yellow
Write-Host ""

# Run the migration using psql
try {
    $env:PGPASSWORD = ($DATABASE_URL -split ':' | Select-Object -Last 1) -split '@' | Select-Object -First 1
    $dbHost = ($DATABASE_URL -split '@' | Select-Object -Last 1) -split ':' | Select-Object -First 1
    $dbPort = (($DATABASE_URL -split '@' | Select-Object -Last 1) -split ':' | Select-Object -Last 1) -split '/' | Select-Object -First 1
    $dbName = ($DATABASE_URL -split '/' | Select-Object -Last 1)
    $dbUser = (($DATABASE_URL -split '//' | Select-Object -Last 1) -split ':' | Select-Object -First 1)
    
    Write-Host "Connecting to PostgreSQL..." -ForegroundColor Yellow
    Write-Host "  Host: $dbHost" -ForegroundColor Gray
    Write-Host "  Port: $dbPort" -ForegroundColor Gray
    Write-Host "  Database: $dbName" -ForegroundColor Gray
    Write-Host "  User: $dbUser" -ForegroundColor Gray
    Write-Host ""
    
    # Execute migration
    psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -f "migrations\$($migrationFile.Name)"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✅ Migration completed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Change admin password immediately!" -ForegroundColor Yellow
        Write-Host "  2. Rebuild backend: cargo build --release" -ForegroundColor Gray
        Write-Host "  3. Start backend: cargo run --release" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Admin credentials (CHANGE IMMEDIATELY):" -ForegroundColor Yellow
        Write-Host "  Email: admin@footballheritage.com" -ForegroundColor White
        Write-Host "  Password: Admin123!" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "❌ Migration failed!" -ForegroundColor Red
        Write-Host "Check the error messages above." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error running migration: $_" -ForegroundColor Red
    exit 1
}
