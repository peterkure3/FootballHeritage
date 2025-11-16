# Start Football Heritage with ML Predictions
# This script starts both the backend and the pipeline API for predictions

Write-Host "Starting Football Heritage with ML Predictions..." -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if Node.js is installed
$node = Get-Command node -ErrorAction SilentlyContinue

if ($null -eq $node) {
    Write-Host "Node.js not found. Please install Node.js" -ForegroundColor Red
    exit 1
} else {
    $nodeVersion = node --version
    Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
}


Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
Write-Host ""

# Start Pipeline API in background
Write-Host "1. Starting Pipeline API (Port 5555)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd pipeline; python -m api.main" -WindowStyle Normal

Start-Sleep -Seconds 2

# Start Rust Backend in background
Write-Host "2. Starting Rust Backend (Port 8080)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; cargo run --bin football-heritage-backend" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "3. Starting React Frontend (Port 5173)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "Services running on:" -ForegroundColor Yellow
Write-Host "  - Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host "  - Backend API:  http://localhost:8080" -ForegroundColor White
Write-Host "  - Pipeline API: http://localhost:5555" -ForegroundColor White
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor Yellow
Write-Host "  - Pipeline API Docs: http://localhost:5555/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services" -ForegroundColor Blue
