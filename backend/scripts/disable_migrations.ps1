# Disable Migrations Script
# This script disables auto-migrations by renaming the migrations folder

Write-Host "Disabling Auto-Migrations..." -ForegroundColor Cyan
Write-Host ""

# Check if migrations folder exists
if (Test-Path "migrations") {
    Write-Host "Found migrations folder" -ForegroundColor Yellow

    # Check if already disabled
    if (Test-Path "migrations.disabled") {
        Write-Host "Migrations already disabled (migrations.disabled exists)" -ForegroundColor Green
        Write-Host ""
        Write-Host "To re-enable, run:" -ForegroundColor Gray
        Write-Host "  Rename-Item migrations.disabled migrations" -ForegroundColor Gray
    } else {
        # Rename migrations to migrations.disabled
        Rename-Item -Path "migrations" -NewName "migrations.disabled"
        Write-Host "Renamed migrations -> migrations.disabled" -ForegroundColor Green
    }
} elseif (Test-Path "migrations.disabled") {
    Write-Host "Migrations already disabled" -ForegroundColor Green
} else {
    Write-Host "No migrations folder found (nothing to disable)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Build: cargo build --release" -ForegroundColor White
Write-Host "  2. Start: .\run.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Backend will start without trying to run migrations" -ForegroundColor Green
Write-Host ""
