# Football Heritage Backend - Run Script
# This script loads .env and runs the application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Football Heritage Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory to backend root (parent of scripts folder)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Split-Path -Parent $scriptPath
Set-Location $backendRoot

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env file with required variables" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Required variables:" -ForegroundColor Yellow
    Write-Host "  DATABASE_URL=postgresql://user:pass@localhost:5432/football_heritage"
    Write-Host "  JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please"
    Write-Host "  ENCRYPTION_KEY=12345678901234567890123456789012"
    pause
    exit 1
}

# Load .env file
Write-Host "Loading environment variables from .env..." -ForegroundColor Green
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        Write-Host "  Set $name" -ForegroundColor Gray
    }
}

# Override HTTPS_ENABLED to false for easier local testing
Write-Host ""
Write-Host "Setting HTTPS_ENABLED=false for local development..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("HTTPS_ENABLED", "false", "Process")

Write-Host ""
Write-Host "Starting application..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""

# Run the application
& ".\target\release\football-heritage-backend.exe"

# Keep window open if there's an error
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Application exited with error code: $LASTEXITCODE" -ForegroundColor Red
    pause
}
