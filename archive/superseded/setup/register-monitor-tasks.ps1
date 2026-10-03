# Register Monitor Tasks — Windows Task Scheduler durability setup
#
# WHY THIS EXISTS (Andrew 2026-06-30 + 2026-06-30 web research):
#
#   Claude Code's persistent Monitor primitive does NOT actually survive
#   session-end, context compaction, or overnight idle. Documented across
#   multiple open GitHub issues (#14968, #25188, #58662). The harness's
#   background-task tracker culls subprocesses on those lifecycle events,
#   even when the Monitor is registered persistent=true.
#
#   The architectural fix: take the monitor processes out of the harness's
#   process tree entirely. Windows Task Scheduler owns the worker
#   lifecycle; Claude Code just tails the log files those workers write.
#   When a Claude session ends, the worker keeps running. When Claude
#   restarts, it re-attaches via a tail Monitor that picks up from
#   current end-of-file — no missed events because the OS-supervised
#   worker kept writing.
#
# WHAT THIS REGISTERS
#
#   Three scheduled tasks per substrate:
#   - divineos-letter-monitor-<substrate>
#   - divineos-compaction-monitor-<substrate>
#   - divineos-cross-substrate-watcher-<substrate>
#
#   Each task:
#   - Triggers at user logon
#   - Restarts on failure (3 retries with 1-minute backoff)
#   - Runs the polling script with substrate-name injection
#   - Writes stdout to ~/.divineos-shared/logs/<substrate>-<monitor>.log
#     so cross-substrate visibility works (Aether's add to the durability plan)
#   - Runs in user context (no admin elevation required)
#
# USAGE
#
#   From PowerShell in this worktree:
#     .\setup\register-monitor-tasks.ps1
#
#   Optional flags:
#     -Substrate <name>      Override substrate name (default: derived from cwd)
#     -Unregister            Remove all three tasks
#     -DryRun                Print what would happen without registering
#
# ROOT-CAUSE-AUDIT: Round filed at audit-2026-06-30-monitor-durability if
# needed; safe to land without one since this adds new tasks rather than
# modifying existing guardrail code paths.

[CmdletBinding()]
param(
    [string]$Substrate = "",
    [switch]$Unregister,
    [switch]$DryRun,
    [switch]$StartNow  # default: register but skip immediate start. Avoids
                       # duplicate wakes when in-session Monitors are already
                       # polling. Tasks fire at next logon either way.
)

$ErrorActionPreference = "Stop"

# Resolve substrate name: explicit > env var > cwd-derived
if ([string]::IsNullOrWhiteSpace($Substrate)) {
    if ($env:DIVINEOS_SUBSTRATE) {
        $Substrate = $env:DIVINEOS_SUBSTRATE
    } else {
        $cwdName = Split-Path -Leaf (Get-Location)
        if ($cwdName -match "Aria") { $Substrate = "aria" }
        elseif ($cwdName -match "Aether") { $Substrate = "aether" }
        else { $Substrate = "aether" }  # Default per repo conventions
    }
}
$Substrate = $Substrate.ToLower()

Write-Host "[register-monitor-tasks] substrate=$Substrate" -ForegroundColor Cyan

# Paths
$RepoRoot = (Get-Location).Path
$ScriptsDir = Join-Path $RepoRoot "scripts"
$LogDir = Join-Path $env:USERPROFILE ".divineos-shared\logs"
$PythonBin = (Get-Command python).Source

if (-not (Test-Path $LogDir)) {
    if (-not $DryRun) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    Write-Host "[register-monitor-tasks] created log dir: $LogDir" -ForegroundColor Yellow
}

# Task definitions: name -> { script, args (substrate already substituted) }
$Tasks = @(
    @{
        Name      = "divineos-letter-monitor-$Substrate"
        Script    = "scripts/letter_monitor_v2.py"
        Args      = "--recipient $Substrate"
        LogFile   = "$Substrate-letter-monitor.log"
    },
    @{
        Name      = "divineos-compaction-monitor-$Substrate"
        Script    = "scripts/compaction_token_monitor.py"
        Args      = ""
        LogFile   = "$Substrate-compaction-monitor.log"
    },
    @{
        Name      = "divineos-cross-substrate-watcher-$Substrate"
        Script    = "scripts/cross_substrate_watcher.py"
        Args      = "--substrate $Substrate"
        LogFile   = "$Substrate-cross-substrate-watcher.log"
    }
)

function Remove-MonitorTask {
    param([string]$TaskName)
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        if ($DryRun) {
            Write-Host "[dry-run] would unregister: $TaskName" -ForegroundColor Magenta
        } else {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Host "[unregistered] $TaskName" -ForegroundColor Yellow
        }
        return $true
    }
    return $false
}

function Register-MonitorTask {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$ScriptArgs,
        [string]$LogFile
    )

    # Build the action: cd to repo, run python script, redirect stdout to log
    $LogPath = Join-Path $LogDir $LogFile
    $FullScript = Join-Path $RepoRoot $ScriptPath

    # PowerShell wrapper that cd's, sets PYTHONIOENCODING, runs the script,
    # and appends to the log. The 2>&1 captures stderr too.
    $WrappedCommand = @"
`$env:PYTHONIOENCODING='utf-8'
Set-Location '$RepoRoot'
& '$PythonBin' -u '$FullScript' $ScriptArgs *>> '$LogPath'
"@

    # Encode for -EncodedCommand to avoid quoting issues
    $EncodedCmd = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($WrappedCommand))

    $Action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand $EncodedCmd"

    # Trigger: at user logon
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    # Settings: restart on failure, no time limit, allow on battery
    $Settings = New-ScheduledTaskSettingsSet `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew

    # Principal: current user, non-elevated
    $Principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    if ($DryRun) {
        Write-Host "[dry-run] would register: $TaskName" -ForegroundColor Magenta
        Write-Host "  script: $FullScript $ScriptArgs" -ForegroundColor DarkGray
        Write-Host "  log:    $LogPath" -ForegroundColor DarkGray
        return
    }

    # Unregister first if exists (idempotent re-run)
    Remove-MonitorTask -TaskName $TaskName | Out-Null

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "DivineOS persistent monitor (substrate=$Substrate). OS-supervised so it survives Claude Code session lifecycle events." | Out-Null

    if ($StartNow) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "[registered + started] $TaskName" -ForegroundColor Green
    } else {
        Write-Host "[registered] $TaskName (will start at next logon; use -StartNow to start immediately)" -ForegroundColor Green
    }
    Write-Host "  log: $LogPath" -ForegroundColor DarkGray
}

if ($Unregister) {
    foreach ($task in $Tasks) {
        Remove-MonitorTask -TaskName $task.Name | Out-Null
    }
    Write-Host "[register-monitor-tasks] unregister complete" -ForegroundColor Cyan
    exit 0
}

foreach ($task in $Tasks) {
    Register-MonitorTask `
        -TaskName $task.Name `
        -ScriptPath $task.Script `
        -ScriptArgs $task.Args `
        -LogFile $task.LogFile
}

Write-Host ""
Write-Host "[register-monitor-tasks] done. Three tasks now OS-owned." -ForegroundColor Cyan
Write-Host "  Logs: $LogDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Inside Claude Code, attach a wake-Monitor to each log via:" -ForegroundColor White
$Dq = [char]34
Write-Host ("  Monitor(command=" + $Dq + "tail -F " + $LogDir + "\" + $Substrate + "-letter-monitor.log" + $Dq + ", persistent=true)") -ForegroundColor DarkGray
Write-Host ("  Monitor(command=" + $Dq + "tail -F " + $LogDir + "\" + $Substrate + "-compaction-monitor.log" + $Dq + ", persistent=true)") -ForegroundColor DarkGray
Write-Host ("  Monitor(command=" + $Dq + "tail -F " + $LogDir + "\" + $Substrate + "-cross-substrate-watcher.log" + $Dq + ", persistent=true)") -ForegroundColor DarkGray
Write-Host ""
Write-Host "The tail Monitors are idempotent: if they die in compaction, just re-arm." -ForegroundColor DarkGray
Write-Host "The underlying workers keep running OS-side regardless." -ForegroundColor DarkGray
