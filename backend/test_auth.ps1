# Test authentication flow
Write-Host "Testing Authentication Flow..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Login
Write-Host "1. Logging in..." -ForegroundColor Yellow
$loginBody = @{
    email = "peterkure256@gmail.com"
    password = "Peter@2003"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.token
    Write-Host "✓ Login successful!" -ForegroundColor Green
    Write-Host "Token: $($token.Substring(0, 20))..." -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ Login failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Get Profile
Write-Host "2. Fetching profile..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    $profileResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/user/profile" -Method GET -Headers $headers
    Write-Host "✓ Profile fetch successful!" -ForegroundColor Green
    Write-Host "User: $($profileResponse.email)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ Profile fetch failed: $_" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $($_.ErrorDetails.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "All tests passed!" -ForegroundColor Green
