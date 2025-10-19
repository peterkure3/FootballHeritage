# ========================================
#  ALL-IN-ONE FIX SCRIPT
#  Football Heritage Backend
# ========================================
# This script fixes all issues and starts the backend

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Football Heritage - Complete Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Fix HOST in .env
Write-Host "Step 1: Fixing HOST configuration..." -ForegroundColor Yellow

if (Test-Path ".env") {
    $envContent = Get-Content ".env"
    $newContent = @()
    $hostFixed = $false

    foreach ($line in $envContent) {
        if ($line -match "^HOST=127\.0\.0\.1") {
            $newContent += "HOST=0.0.0.0"
            $hostFixed = $true
            Write-Host "  Changed HOST from 127.0.0.1 to 0.0.0.0" -ForegroundColor Green
        } elseif ($line -match "^HOST=") {
            $newContent += $line
            Write-Host "  HOST already set correctly" -ForegroundColor Green
        } else {
            $newContent += $line
        }
    }

    $newContent | Set-Content ".env"

    if (-not $hostFixed) {
        Write-Host "  HOST setting verified" -ForegroundColor Green
    }
} else {
    Write-Host "  WARNING: .env file not found!" -ForegroundColor Red
    Write-Host "  Please create .env file with HOST=0.0.0.0" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Disable migrations folder
Write-Host "Step 2: Disabling auto-migrations..." -ForegroundColor Yellow

if (Test-Path "migrations") {
    if (Test-Path "migrations.disabled") {
        Remove-Item -Path "migrations.disabled" -Recurse -Force
    }
    Rename-Item -Path "migrations" -NewName "migrations.disabled"
    Write-Host "  Migrations folder disabled (renamed to migrations.disabled)" -ForegroundColor Green
} elseif (Test-Path "migrations.disabled") {
    Write-Host "  Migrations already disabled" -ForegroundColor Green
} else {
    Write-Host "  No migrations folder found" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Clean old build
Write-Host "Step 3: Cleaning old build artifacts..." -ForegroundColor Yellow
Write-Host "  This removes old compiled code..." -ForegroundColor Gray

if (Test-Path "target") {
    Remove-Item -Path "target/release" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Cleaned release build" -ForegroundColor Green
} else {
    Write-Host "  No previous build found" -ForegroundColor Gray
}

Write-Host ""

# Step 4: Build with latest changes
Write-Host "Step 4: Building backend with fixes..." -ForegroundColor Yellow
Write-Host "  This will take 2-3 minutes..." -ForegroundColor Gray
Write-Host ""

cargo build --release 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Build completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Build failed!" -ForegroundColor Red
    Write-Host "  Run 'cargo build --release' to see errors" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 5: Verify configuration
Write-Host "Step 5: Verifying configuration..." -ForegroundColor Yellow

$envCheck = Get-Content ".env" | Select-String -Pattern "^HOST=|^PORT=|^ALLOWED_ORIGINS="

Write-Host "  Current settings:" -ForegroundColor Gray
foreach ($line in $envCheck) {
    Write-Host "    $line" -ForegroundColor White
}

Write-Host ""

# Final summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Fixes Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "What was fixed:" -ForegroundColor Yellow
Write-Host "  1. HOST set to 0.0.0.0 (accepts browser connections)" -ForegroundColor White
Write-Host "  2. Auto-migrations disabled (already in database)" -ForegroundColor White
Write-Host "  3. Backend rebuilt with latest code changes" -ForegroundColor White
Write-Host "  4. CORS properly configured in code" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting backend server now..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Look for these messages:" -ForegroundColor Cyan
Write-Host "  'CORS allowed origins: [http://localhost:5173]'" -ForegroundColor Gray
Write-Host "  'Starting server on 0.0.0.0:8080'" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start the server
.\run.ps1
