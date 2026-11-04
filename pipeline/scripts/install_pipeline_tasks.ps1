param(
    [switch]$Install,
    [switch]$PublicOnly,
    [ValidatePattern('^\d{2}:\d{2}$')][string]$DailyAt = '06:00',
    [ValidatePattern('^\d{2}:\d{2}$')][string]$WeeklyAt = '03:00'
)
$ErrorActionPreference = 'Stop'
$pipelineRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$launcher = Join-Path $pipelineRoot 'run_pipeline.bat'
$dailyTime = [DateTime]::ParseExact($DailyAt, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$weeklyTime = [DateTime]::ParseExact($WeeklyAt, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$definitions = @(
    @{ Name = 'FootballHeritage-Pipeline-Daily'; Job = 'daily'; At = $dailyTime; Weekly = $false },
    @{ Name = 'FootballHeritage-Pipeline-Weekly'; Job = 'weekly'; At = $weeklyTime; Weekly = $true }
)
foreach ($definition in $definitions) {
    Write-Output "$($definition.Name): $($definition.Job) at $($definition.At.ToString('HH:mm')) computer-local time; weekly runs Sunday."
}
if ($PublicOnly) { $definitions[0].Job = 'daily --public-only'; Write-Output 'Daily paid Odds API fetches disabled; official and public feeds remain enabled.' }
if (-not $Install) {
    Write-Output 'Preview only. Run with -Install to register tasks for the current signed-in Windows account.'
    exit 0
}
# Check all names before any registration; never replace an existing task silently.
foreach ($definition in $definitions) {
    if (Get-ScheduledTask -TaskName $definition.Name -ErrorAction SilentlyContinue) {
        throw "Task already exists: $($definition.Name). Inspect it in Task Scheduler before changing it."
    }
}
& $launcher doctor
if ($LASTEXITCODE -ne 0) { throw 'Pipeline doctor failed; fix its reported prerequisites before scheduling.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 13) -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
foreach ($definition in $definitions) {
    $action = New-ScheduledTaskAction -Execute $env:ComSpec `
        -Argument ('/d /s /c ""{0}" {1}"' -f $launcher, $definition.Job) -WorkingDirectory $pipelineRoot
    if ($definition.Weekly) {
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $definition.At
    } else {
        $trigger = New-ScheduledTaskTrigger -Daily -At $definition.At
    }
    Register-ScheduledTask -TaskName $definition.Name -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Description 'FootballHeritage unattended pipeline. Logs: pipeline/logs/automation.' | Out-Null
}
Get-ScheduledTask -TaskName 'FootballHeritage-Pipeline-*' | Select-Object TaskName, State
