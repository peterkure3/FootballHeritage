[CmdletBinding()]
param([switch]$ApplyLocalMigrations, [string]$EnvFile)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pipeline = Join-Path $root 'pipeline'
if (-not $EnvFile) { $EnvFile = Join-Path $pipeline '.env.sync' }
$python = Join-Path $pipeline '.venv-sync/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & py -3 -m venv (Join-Path $pipeline '.venv-sync')
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment setup failed' }
}
& $python -m pip install -r (Join-Path $pipeline 'requirements-sync.txt')
if ($LASTEXITCODE -ne 0) { throw 'Sync dependency installation failed' }
if ($ApplyLocalMigrations) {
    & $python (Join-Path $PSScriptRoot 'apply_local_publication_migrations.py') --env $EnvFile
    if ($LASTEXITCODE -ne 0) { throw 'Local publication migrations failed' }
}
Write-Output 'Sync environment prepared. Review private env, migration/role contracts and source registration before startup.'
