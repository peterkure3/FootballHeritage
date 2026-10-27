[CmdletBinding()]
param([string]$EnvFile, [switch]$Once, [ValidateSet('publication','gateway')][string]$Service = 'publication')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pipeline = Join-Path $root 'pipeline'
if (-not $EnvFile) { $EnvFile = Join-Path $pipeline $(if ($Service -eq 'gateway') { '.env.gateway' } else { '.env.sync' }) }
$python = Join-Path $pipeline '.venv-sync/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run setup_pipeline_sync.ps1 first' }
if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'Create the private sync environment file first' }
$EnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
$logs = Join-Path $pipeline 'logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$log = Join-Path $logs ($Service + '-' + (Get-Date -Format 'yyyyMMdd') + '.jsonl')
$module = if ($Service -eq 'gateway') { 'sync.gateway' } else { 'sync.scheduler' }
$arguments = @('-u', '-m', $module, '--env', $EnvFile)
if ($Once) { $arguments += '--once' }
Push-Location $pipeline
try {
    & $python @arguments >> $log 2>&1
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
