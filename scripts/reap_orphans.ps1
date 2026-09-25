# Reap orphaned hook children — bash/git/python processes whose parent has died.
# Read-only by default. Pass -Kill to actually terminate them.
param([switch]$Kill)

$live = @{}
Get-CimInstance Win32_Process | ForEach-Object { $live[$_.ProcessId] = $true }

$orphans = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^(bash|git|python|python3)\.exe$' -and
        $_.ParentProcessId -gt 0 -and
        -not $live.ContainsKey($_.ParentProcessId)
    }

if (-not $orphans) { Write-Output "No orphaned bash/git/python processes."; exit 0 }

Write-Output "Orphaned processes (parent no longer exists):"
$orphans | Select-Object ProcessId, Name, CreationDate,
    @{n='Cmd';e={ $_.CommandLine.Substring(0,[Math]::Min(120,$_.CommandLine.Length)) }} |
    Format-Table -AutoSize | Out-String -Width 300 | Write-Output

if ($Kill) {
    $orphans | ForEach-Object {
        try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop; Write-Output "killed $($_.ProcessId) $($_.Name)" }
        catch { Write-Output "could not kill $($_.ProcessId): $_" }
    }
} else {
    Write-Output "`nDry run. Re-run with -Kill to terminate these."
}
