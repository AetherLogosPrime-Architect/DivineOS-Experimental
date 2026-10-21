# A quiet sweep for leftover processes: it ends only things that are clearly leaks, says nothing when it finds none,
# and writes one line to a log when it does end something. Dad's idea, 2026-10-16: "something that pings every so often
# to check for any orphaned processes", and not another screen to read.
#
# A process is a leak when ALL of these hold:
#   - it is bash, git, python or pytest-related (the kinds our hooks and test runs leave behind),
#   - its parent no longer exists,
#   - it has been running longer than -MinutesOld (default 30), so a job just started is never touched,
#   - and it is NOT one of the things that are meant to run on their own after their shell is gone: the poker table
#     (server.py), the letter doorbell, the model server, a waiter, a session monitor.
# Default is a dry run that only prints what it would end. Pass -Kill to actually end them (a scheduled task does).
param([switch]$Kill, [int]$MinutesOld = 30, [string]$Log = "$HOME\.divineos\orphan_sweep.log")

$keep = 'server\.py|letter_doorbell|wait_turn|ollama|monitor|watch|claude'
$live = @{}
Get-CimInstance Win32_Process | ForEach-Object { $live[$_.ProcessId] = $true }

$cutoff = (Get-Date).AddMinutes(-$MinutesOld)
$leaks = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(bash|git|python|python3|pytest)\.exe$' -and
    $_.ParentProcessId -gt 0 -and
    -not $live.ContainsKey($_.ParentProcessId) -and
    $_.CreationDate -lt $cutoff -and
    -not ($_.CommandLine -match $keep)
}

if (-not $leaks) { exit 0 }  # nothing to say

$lines = $leaks | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(100, $_.CommandLine.Length)) } else { '' }
    "{0} pid {1} {2} (since {3}) {4}" -f (Get-Date -Format s), $_.ProcessId, $_.Name, $_.CreationDate.ToString('s'), $cmd
}

if ($Kill) {
    foreach ($p in $leaks) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch { $lines += "could not end pid $($p.ProcessId): $_" }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
    $lines | ForEach-Object { "ended $_" } | Add-Content -Path $Log
} else {
    $lines | ForEach-Object { "would end $_" }
}
