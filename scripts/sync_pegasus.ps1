param(
    [string]$SshHost = 'peterkure3@pegasus',
    [int]$LocalPort = 55433,
    [string]$IdentityFile = '',
    [string]$PipelineEnv = (Join-Path $env:LOCALAPPDATA 'FootballHeritage\pegasus-db.env'),
    [int]$Limit = 0,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $PipelineEnv -PathType Leaf)) {
    throw 'Pegasus credentials are missing. Follow pipeline/docs/PEGASUS_SYNC.md to copy them over SSH.'
}
if ($LocalPort -lt 1024 -or $LocalPort -gt 65535 -or $Limit -lt 0) {
    throw 'Use a local port from 1024 to 65535 and a nonnegative fixture limit.'
}

$tunnelProcess = $null
$logRoot = Split-Path -Parent $PipelineEnv
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$errorLog = Join-Path $logRoot "ssh-$stamp.log"
$dedicatedKey = Join-Path $env:USERPROFILE '.ssh\footballheritage_pegasus_ed25519'
if (-not $IdentityFile -and (Test-Path -LiteralPath $dedicatedKey -PathType Leaf)) {
    $IdentityFile = $dedicatedKey
}
if ($IdentityFile -and -not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw 'The specified SSH identity file does not exist.'
}
try {
    $listener = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
        $sshArguments = @('-N', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3', '-L', "127.0.0.1:${LocalPort}:127.0.0.1:55432")
        if ($IdentityFile) {
            $sshArguments += @('-i', ('"{0}"' -f $IdentityFile), '-o', 'IdentitiesOnly=yes')
        }
        $sshArguments += $SshHost
        $tunnelProcess = Start-Process -FilePath (Get-Command ssh.exe).Source `
            -ArgumentList $sshArguments -WindowStyle Hidden -PassThru -RedirectStandardError $errorLog
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        do {
            $tunnelProcess.Refresh()
            if ($tunnelProcess.HasExited) {
                throw "SSH tunnel failed. Check key login to $SshHost and $errorLog."
            }
            $listener = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
            if (-not $listener) { Start-Sleep -Milliseconds 250 }
        } while (-not $listener -and [DateTime]::UtcNow -lt $deadline)
        if (-not $listener) { throw 'SSH tunnel did not become ready within 15 seconds.' }
    }

    $pythonArguments = @('-3', (Join-Path $repoRoot 'pipeline\sync_to_backend.py'),
        '--pipeline-env', $PipelineEnv, '--pipeline-host', '127.0.0.1',
        '--pipeline-port', "$LocalPort", '--backend-env', (Join-Path $repoRoot 'backend\.env'))
    if (-not $Apply) { $pythonArguments += '--dry-run' }
    if ($Limit -gt 0) { $pythonArguments += @('--limit', "$Limit") }
    Push-Location (Join-Path $repoRoot 'pipeline')
    try {
        & py @pythonArguments
        if ($LASTEXITCODE -ne 0) { throw "Database sync failed with exit code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
} finally {
    if ($null -ne $tunnelProcess) {
        $tunnelProcess.Refresh()
        if (-not $tunnelProcess.HasExited) { Stop-Process -Id $tunnelProcess.Id }
    }
}
