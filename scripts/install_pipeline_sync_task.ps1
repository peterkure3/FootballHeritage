[CmdletBinding()]
param([string]$EnvFile, [switch]$StartNow, [ValidateSet('publication','gateway')][string]$Service = 'publication')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $EnvFile) { $EnvFile = Join-Path $root $(if ($Service -eq 'gateway') { 'pipeline/.env.gateway' } else { 'pipeline/.env.sync' }) }
$launcher = Join-Path $PSScriptRoot 'start_pipeline_sync.ps1'
if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'Private sync environment file is required' }
$EnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
# Task registration is explicit. Never overwrite an existing task silently.
$taskName = 'FootballHeritage-NeonPublication'
if ($Service -eq 'gateway') { $taskName = 'FootballHeritage-NeonGateway' }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw 'Publication task already exists; inspect it before updating'
}
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
    '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $launcher + '" -EnvFile "' + $EnvFile + '" -Service ' + $Service)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal | Out-Null
if ($StartNow) { Start-ScheduledTask -TaskName $taskName }
Write-Output 'Publication task registered for sign-in. The computer must be awake and the user signed in.'
