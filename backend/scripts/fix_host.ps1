# Fix Backend Host Configuration
# This script updates the HOST setting in .env to allow connections from browsers

Write-Host "🔧 Fixing Backend Host Configuration..." -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "   Please create a .env file first" -ForegroundColor Yellow
    exit 1
}

# Read current .env content
$envContent = Get-Content ".env"
$newContent = @()
$hostFound = $false
$hostValue = ""

foreach ($line in $envContent) {
    $trimmedLine = $line.Trim()

    if ($trimmedLine.StartsWith("HOST=")) {
        $hostFound = $true
        $hostValue = $trimmedLine.Substring(5)

        if ($hostValue -eq "127.0.0.1") {
            Write-Host "⚠️  Found HOST=127.0.0.1 (only accepts local connections)" -ForegroundColor Yellow
            Write-Host "   Changing to HOST=0.0.0.0 (accepts all connections)" -ForegroundColor Green
            $newContent += "HOST=0.0.0.0"
        } else {
            Write-Host "✓ HOST is already set to: $hostValue" -ForegroundColor Green
            $newContent += $line
        }
    } else {
        $newContent += $line
    }
}

# If HOST not found, add it
if (-not $hostFound) {
    Write-Host "⚠️  HOST not found in .env" -ForegroundColor Yellow
    Write-Host "   Adding HOST=0.0.0.0" -ForegroundColor Green
    $newContent += "HOST=0.0.0.0"
}

# Write back to .env
$newContent | Set-Content ".env"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Configuration Updated!" -ForegroundColor Green
Write-Host ""
Write-Host "Current .env settings:" -ForegroundColor Cyan

# Display current HOST and PORT
Get-Content ".env" | Select-String -Pattern "^HOST=|^PORT=|^ALLOWED_ORIGINS=" | ForEach-Object {
    Write-Host "  $_" -ForegroundColor White
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  IMPORTANT: You MUST restart the backend server!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Steps:" -ForegroundColor Cyan
Write-Host "  1. Stop the backend (Ctrl+C)" -ForegroundColor White
Write-Host "  2. Run: .\run.ps1" -ForegroundColor White
Write-Host "  3. Check logs for: 'Starting server on 0.0.0.0:8080'" -ForegroundColor White
Write-Host "  4. Try login in browser" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 What changed:" -ForegroundColor Cyan
Write-Host "  • HOST=127.0.0.1 (only local) → HOST=0.0.0.0 (all interfaces)" -ForegroundColor Gray
Write-Host "  • This allows browser connections to localhost:8080" -ForegroundColor Gray
Write-Host "  • Required for CORS to work properly" -ForegroundColor Gray
Write-Host ""
