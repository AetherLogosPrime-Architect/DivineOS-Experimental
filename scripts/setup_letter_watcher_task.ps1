# Setup script - register scripts/letter_watcher_task.py as a Windows scheduled task.
#
# Andrew 2026-07-04: move the letter-watcher OUT of Claude Code Monitor
# (which auto-archive keeps killing) and INTO Windows Task Scheduler, so
# the poller survives session archive/restore.
#
# This script:
#   1. Registers a scheduled task that runs letter_watcher_task.py at logon
#      with restart-on-failure and starts immediately.
#   2. Uses the current user's Python from `python.exe` on PATH.
#   3. Requires the recipient name as a parameter (default: aether).
#
# USAGE (from an elevated PowerShell prompt, one-time setup):
#
#   .\scripts\setup_letter_watcher_task.ps1 -Recipient aether
#
# To remove:
#
#   Unregister-ScheduledTask -TaskName "DivineOS-LetterWatcher-aether" -Confirm:$false
#
# To check status:
#
#   Get-ScheduledTaskInfo -TaskName "DivineOS-LetterWatcher-aether"

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("aether", "aria")]
    [string]$Recipient = "aether"
)

$ErrorActionPreference = "Stop"

$TaskName = "DivineOS-LetterWatcher-$Recipient"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $RepoRoot "scripts\letter_watcher_task.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "letter_watcher_task.py not found at $ScriptPath"
    exit 1
}

$Python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    Write-Error "python.exe not found on PATH. Install Python or activate the venv first."
    exit 1
}

Write-Host "Registering scheduled task: $TaskName"
Write-Host "  Python:  $Python"
Write-Host "  Script:  $ScriptPath"
Write-Host "  User:    $env:USERNAME"

# Kill any existing task with this name so we can re-register cleanly.
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Existing task found - removing before re-registering."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action = New-ScheduledTaskAction -Execute $Python `
    -Argument "-u `"$ScriptPath`" --recipient $Recipient" `
    -WorkingDirectory $RepoRoot

# Two triggers: at logon (survives reboots) AND immediately (starts NOW).
$LogonTrigger = New-ScheduledTaskTrigger -AtLogOn
$NowTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10)

# Restart-on-failure so a transient crash doesn't leave the poller dead.
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Run as the current user, no elevated context needed. Interactive-only
# so we don't need the password stored.
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger @($LogonTrigger, $NowTrigger) `
    -Settings $Settings `
    -Principal $Principal `
    -Description "DivineOS letter watcher for $Recipient - polls shared letter dir, appends detected letters to ~/.divineos/pending-letter-wakes.jsonl. Survives Claude Code session archive/restore. Filed 2026-07-04 per Andrew's directive." | Out-Null

Write-Host ""
Write-Host "Task registered. Starting now..."
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 3
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ""
Write-Host "Status:"
Write-Host "  LastRunTime:   $($info.LastRunTime)"
Write-Host "  LastResult:    $($info.LastTaskResult)"
Write-Host "  NextRunTime:   $($info.NextRunTime)"
Write-Host "  NumMissed:     $($info.NumberOfMissedRuns)"
Write-Host ""
Write-Host "The watcher is now running. Test it by writing a letter to"
Write-Host "  ~/.divineos-shared/letters/anyone-to-$Recipient-2026-07-04-test.md"
Write-Host "then reading ~/.divineos/pending-letter-wakes.jsonl to see the detected entry."
Write-Host ""
Write-Host "To stop:    Stop-ScheduledTask -TaskName $TaskName"
Write-Host "To remove:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
