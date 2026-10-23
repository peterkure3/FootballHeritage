[CmdletBinding(SupportsShouldProcess)]
param([ValidateRange(15, 120)][int]$IntervalMinutes = 15)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pipelinePath = Join-Path $workspace 'pipeline'
$pythonPath = (& py -3 -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $pythonPath)) {
    throw 'A working Python 3 installation is required.'
}
$consolePythonPath = $pythonPath
$windowlessPythonPath = Join-Path (Split-Path -Parent $pythonPath) 'pythonw.exe'
if (Test-Path -LiteralPath $windowlessPythonPath) { $pythonPath = $windowlessPythonPath }
$taskName = 'FootballHeritage-PaperTrial-Collection'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and ((@($pythonPath, $consolePythonPath) -notcontains $existing.Actions.Execute) -or ($existing.Actions.Arguments -ne '-m scripts.run_trial_collection') -or ($existing.Actions.WorkingDirectory -ne $pipelinePath))) {
    throw "Task $taskName exists with a different action; refusing to overwrite it."
}
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument '-m scripts.run_trial_collection' -WorkingDirectory $pipelinePath
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
if ($PSCmdlet.ShouldProcess($taskName, "Register collection every $IntervalMinutes minutes for the current logged-in user")) {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Frozen EPL paper trial: daily football ingestion, fresh quotes, forecasts, settlements, and one formal assessment.' -Force | Out-Null
    Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State, Actions, Triggers
}
