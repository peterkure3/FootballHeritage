param([string]$SshHost = 'peterkure3@pegasus')

$ErrorActionPreference = 'Stop'
$keyPath = Join-Path $env:USERPROFILE '.ssh\footballheritage_pegasus_ed25519'
if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
    throw 'Dedicated SSH key is missing. Follow pipeline/docs/PEGASUS_SYNC.md.'
}

$hostname = & ssh.exe -i $keyPath -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 $SshHost hostname
if ($LASTEXITCODE -ne 0 -or "$hostname".Trim() -ne 'pegasus') {
    throw 'Pegasus key authentication failed. Install the public key before enabling this task.'
}

$syncScript = Join-Path $PSScriptRoot 'sync_pegasus.ps1'
& $syncScript -SshHost $SshHost -IdentityFile $keyPath -Limit 5

$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}" -SshHost "{1}" -Apply' -f $syncScript, $SshHost
$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $account),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30))
)
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$existing = Get-ScheduledTask -TaskName 'FootballHeritagePegasusSync' -ErrorAction SilentlyContinue
if ($existing) {
    throw 'FootballHeritagePegasusSync already exists; inspect it before replacing its configuration.'
}
Register-ScheduledTask -TaskName 'FootballHeritagePegasusSync' -Action $action -Trigger $triggers `
    -Principal $principal -Settings $settings -Description 'Pull verified Pegasus fixtures into the local backend.' | Out-Null
Start-ScheduledTask -TaskName 'FootballHeritagePegasusSync'
Get-ScheduledTask -TaskName 'FootballHeritagePegasusSync' | Select-Object TaskName, State
Write-Output 'Task installed: at sign-in and every 30 minutes while this Windows user is signed in.'
