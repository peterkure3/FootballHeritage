# Frontend Start Script for Windows
# This script starts the React development server

Write-Host "🏈 SportsBet Frontend - Starting Development Server" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeVersion = node --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Node.js is not installed!" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Node.js version: $nodeVersion" -ForegroundColor Green

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host ""
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Failed to install dependencies!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚙️  Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ .env file created" -ForegroundColor Green
    Write-Host "⚠️  Remember to update VITE_API_URL in .env if needed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Starting development server..." -ForegroundColor Green
Write-Host ""
Write-Host "Frontend will be available at:" -ForegroundColor Cyan
Write-Host "  http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend should be running at:" -ForegroundColor Cyan
Write-Host "  https://localhost:8443" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the development server
npm run dev
