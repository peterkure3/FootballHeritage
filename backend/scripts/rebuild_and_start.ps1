# Rebuild and Start Backend Server
# This script rebuilds the backend with the latest changes and starts it

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Rebuild and Start Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Cleaning old build..." -ForegroundColor Yellow
cargo clean
Write-Host "  Done!" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Building with latest changes..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes..." -ForegroundColor Gray
cargo build --release

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Build failed! Check errors above." -ForegroundColor Red
    exit 1
}

Write-Host "  Done!" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Starting backend server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Run the server
.\run.ps1
