# Backend Environment Verification Script
# This script checks if the .env file is correctly configured for CORS

Write-Host "🔍 Checking Backend Environment Configuration..." -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "   Please create a .env file in the backend directory" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Minimum required content:" -ForegroundColor Yellow
    Write-Host "   DATABASE_URL=postgresql://postgres:password@localhost:5432/betting_db" -ForegroundColor Gray
    Write-Host "   JWT_SECRET=your-secret-key-here" -ForegroundColor Gray
    Write-Host "   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000" -ForegroundColor Gray
    exit 1
}

Write-Host "✓ .env file found" -ForegroundColor Green
Write-Host ""

# Read .env file
$envContent = Get-Content ".env"

# Check for required variables
$requiredVars = @{
    "DATABASE_URL" = $false
    "JWT_SECRET" = $false
    "ALLOWED_ORIGINS" = $false
}

$allowedOrigins = ""

foreach ($line in $envContent) {
    $line = $line.Trim()

    # Skip comments and empty lines
    if ($line.StartsWith("#") -or $line -eq "") {
        continue
    }

    # Check each required variable
    foreach ($var in $requiredVars.Keys) {
        if ($line.StartsWith("$var=")) {
            $requiredVars[$var] = $true

            # Extract ALLOWED_ORIGINS value
            if ($var -eq "ALLOWED_ORIGINS") {
                $allowedOrigins = $line.Substring($var.Length + 1)
            }
        }
    }
}

# Report results
Write-Host "📋 Environment Variables Check:" -ForegroundColor Cyan
Write-Host ""

foreach ($var in $requiredVars.Keys) {
    if ($requiredVars[$var]) {
        Write-Host "  ✓ $var is set" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $var is MISSING!" -ForegroundColor Red
    }
}

Write-Host ""

# Check ALLOWED_ORIGINS specifically
if ($requiredVars["ALLOWED_ORIGINS"]) {
    Write-Host "🌐 CORS Configuration:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ALLOWED_ORIGINS = $allowedOrigins" -ForegroundColor White
    Write-Host ""

    # Parse origins
    $origins = $allowedOrigins -split ","
    $hasFrontendOrigin = $false

    Write-Host "  Allowed Origins:" -ForegroundColor Yellow
    foreach ($origin in $origins) {
        $origin = $origin.Trim()
        Write-Host "    • $origin" -ForegroundColor Gray

        if ($origin -eq "http://localhost:5173") {
            $hasFrontendOrigin = $true
        }
    }

    Write-Host ""

    if ($hasFrontendOrigin) {
        Write-Host "  ✓ Frontend origin (http://localhost:5173) is included!" -ForegroundColor Green
    } else {
        Write-Host "  ❌ WARNING: Frontend origin (http://localhost:5173) is NOT included!" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Add this to your .env file:" -ForegroundColor Yellow
        Write-Host "  ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ ALLOWED_ORIGINS is not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Add this to your .env file:" -ForegroundColor Yellow
    Write-Host "  ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000" -ForegroundColor Gray
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if all required variables are set
$allSet = $true
foreach ($var in $requiredVars.Values) {
    if (-not $var) {
        $allSet = $false
        break
    }
}

if ($allSet -and $hasFrontendOrigin) {
    Write-Host "✅ Configuration looks good!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run: .\run.ps1" -ForegroundColor White
    Write-Host "  2. Check logs for: 'CORS allowed origins'" -ForegroundColor White
    Write-Host "  3. Test login in browser" -ForegroundColor White
} else {
    Write-Host "⚠️  Configuration has issues!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please fix the issues above, then run:" -ForegroundColor Cyan
    Write-Host "  .\check_env.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Once fixed, start the server with:" -ForegroundColor Cyan
    Write-Host "  .\run.ps1" -ForegroundColor White
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Additional tips
Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "  • ALLOWED_ORIGINS should NOT have trailing slashes" -ForegroundColor Gray
Write-Host "  • Use http:// not https:// for local development" -ForegroundColor Gray
Write-Host "  • Multiple origins are separated by commas" -ForegroundColor Gray
Write-Host "  • Always restart backend after changing .env" -ForegroundColor Gray
Write-Host ""
