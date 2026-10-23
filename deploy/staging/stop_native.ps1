param([ValidateSet('api', 'pipeline', 'web')][string]$Service = 'api')
$ErrorActionPreference = 'Stop'
$stagingRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$stagingPidFile = Join-Path $stagingRoot ".staging/native-$Service.pid"
if (-not (Test-Path -LiteralPath $stagingPidFile)) { Write-Output 'No staging PID recorded.'; exit 0 }
$stagingProcessId = [int](Get-Content -LiteralPath $stagingPidFile)
$stagingProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$stagingProcessId"
if (-not $stagingProcess) { Write-Output 'Recorded staging process is already stopped.'; exit 0 }
$stagingExpectedApi = Join-Path $stagingRoot '.staging/rust-target/debug/football-heritage-backend.exe'
$stagingExpectedPython = Join-Path $stagingRoot '.staging/python/Scripts/python.exe'
$stagingExpectedWeb = Join-Path $stagingRoot 'deploy/staging/native_web.py'
$stagingMatches = switch ($Service) {
    'api' { $stagingProcess.ExecutablePath -eq $stagingExpectedApi }
    'pipeline' { $stagingProcess.ExecutablePath -eq $stagingExpectedPython -and $stagingProcess.CommandLine.Contains('api.main:app') -and $stagingProcess.CommandLine.Contains('15555') }
    'web' { $stagingProcess.CommandLine.Contains($stagingExpectedWeb) -and $stagingProcess.CommandLine.Contains('--serve') }
}
if (-not $stagingMatches) { throw 'Refusing to stop a process that does not match the isolated staging service.' }
Stop-Process -Id $stagingProcessId
Write-Output "Stopped only the native staging $Service process. This is a forced local stop, not a graceful container shutdown test."
