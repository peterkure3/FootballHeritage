param(
  [string]$CertDir = "$(Split-Path -Parent $PSScriptRoot)\certs",
  [string]$CertFile = "server.crt",
  [string]$KeyFile = "server.key",
  [int]$Days = 365
)

$ErrorActionPreference = 'Stop'

New-Item -ItemType Directory -Force -Path $CertDir | Out-Null

$crtPath = Join-Path $CertDir $CertFile
$keyPath = Join-Path $CertDir $KeyFile

function Test-CommandExists {
  param([string]$Name)
  $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "openssl")) {
  Write-Host "openssl not found on PATH." -ForegroundColor Yellow
  Write-Host "Install one of the following and re-run this script:" -ForegroundColor Yellow
  Write-Host "  - Git for Windows (includes openssl in some distributions)" -ForegroundColor Yellow
  Write-Host "  - Chocolatey: choco install openssl" -ForegroundColor Yellow
  Write-Host "  - Winget: winget install ShiningLight.OpenSSL" -ForegroundColor Yellow
  exit 1
}

if (Test-Path $crtPath) { Remove-Item -Force $crtPath }
if (Test-Path $keyPath) { Remove-Item -Force $keyPath }

Write-Host "Generating self-signed TLS cert for localhost..." -ForegroundColor Cyan
Write-Host "  Cert: $crtPath" -ForegroundColor Cyan
Write-Host "  Key : $keyPath" -ForegroundColor Cyan

& openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout "$keyPath" `
  -out "$crtPath" `
  -days $Days `
  -subj "/CN=localhost" `
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

Write-Host "Done." -ForegroundColor Green
Write-Host "IMPORTANT: Do not commit $keyPath (private key)." -ForegroundColor Yellow
