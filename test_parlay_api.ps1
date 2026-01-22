# Test Parlay Calculator API

Write-Host "Testing Parlay Calculator API..." -ForegroundColor Cyan

# Test 1: Calculate Parlay with 2 legs
Write-Host "`n1. Testing POST /api/v1/parlay/calculate (2-leg parlay)..." -ForegroundColor Yellow

$body = @{
    bets = @(
        @{
            event_id = "00000000-0000-0000-0000-000000000001"
            team = "Kansas City Chiefs"
            odds = -150
            win_prob = $null
            bet_type = "MONEYLINE"
            selection = "HOME"
        },
        @{
            event_id = "00000000-0000-0000-0000-000000000002"
            team = "San Francisco 49ers"
            odds = -125
            win_prob = $null
            bet_type = "MONEYLINE"
            selection = "HOME"
        }
    )
    stake = 100
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/parlay/calculate" `
        -Method POST `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "Combined Odds: $($response.combined_odds)" -ForegroundColor White
    Write-Host "Combined Probability: $([math]::Round($response.combined_probability * 100, 2))%" -ForegroundColor White
    Write-Host "Expected Profit: `$$($response.expected_profit)" -ForegroundColor White
    Write-Host "Projected Payout: `$$($response.projected_payout)" -ForegroundColor White
    Write-Host "Break-even Probability: $([math]::Round($response.break_even_probability * 100, 2))%" -ForegroundColor White
    Write-Host "Expected Value: $([math]::Round($response.expected_value * 100, 2))%" -ForegroundColor White
    Write-Host "Kelly Criterion: $([math]::Round($response.kelly_criterion * 100, 2))%" -ForegroundColor White
    Write-Host "Risk Level: $($response.risk_level)" -ForegroundColor White
    Write-Host "Recommendation: $($response.recommendation)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 2: Calculate Parlay with 3 legs (higher risk)
Write-Host "`n2. Testing 3-leg parlay (higher risk)..." -ForegroundColor Yellow

$body2 = @{
    bets = @(
        @{
            event_id = "00000000-0000-0000-0000-000000000001"
            team = "Team A"
            odds = 150
            win_prob = $null
            bet_type = "MONEYLINE"
            selection = "HOME"
        },
        @{
            event_id = "00000000-0000-0000-0000-000000000002"
            team = "Team B"
            odds = 200
            win_prob = $null
            bet_type = "MONEYLINE"
            selection = "AWAY"
        },
        @{
            event_id = "00000000-0000-0000-0000-000000000003"
            team = "Team C"
            odds = 180
            win_prob = $null
            bet_type = "SPREAD"
            selection = "HOME"
        }
    )
    stake = 50
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/parlay/calculate" `
        -Method POST `
        -Body $body2 `
        -ContentType "application/json"
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "Combined Odds: $($response.combined_odds)" -ForegroundColor White
    Write-Host "Risk Level: $($response.risk_level)" -ForegroundColor White
    Write-Host "Recommendation: $($response.recommendation)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Validation error (only 1 bet)
Write-Host "`n3. Testing validation (should fail with 1 bet)..." -ForegroundColor Yellow

$body3 = @{
    bets = @(
        @{
            event_id = "00000000-0000-0000-0000-000000000001"
            team = "Team A"
            odds = -150
            win_prob = $null
            bet_type = "MONEYLINE"
            selection = "HOME"
        }
    )
    stake = 100
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/parlay/calculate" `
        -Method POST `
        -Body $body3 `
        -ContentType "application/json"
    
    Write-Host "❌ Should have failed!" -ForegroundColor Red
} catch {
    Write-Host "✅ Validation working: $($_.ErrorDetails.Message)" -ForegroundColor Green
}

Write-Host "`n✅ API Testing Complete!" -ForegroundColor Cyan
