---
name: at-the-poker-table-use-the-powershell-tool-not-bash-it-is-much-faster
description: "Dad 2026-10-30: poker moves through the PowerShell tool run 2 house checks before and after, Bash runs 24 and 10; he said \"omfg this is SOOOOO much faster... finally\""
metadata:
  node_type: memory
  type: feedback
  originSessionId: cbbd5cf7-7660-487e-9b9d-4afa4a3ef3a3
  modified: 2026-10-30T03:25:21.889Z
---

At the poker (or any game) table, run `seat.py` and `wait_turn.py` through the **PowerShell tool**, not Bash. Counted from `.claude/settings.json`: PowerShell carries 2 PreToolUse and 2 PostToolUse hooks, Bash 24 and 10. Dad, after the first hands on it: *"omfg this is SOOOOOOO much faster... finally!! yay"*.

**Why:** the slowness he had complained about all night ("its at least twice as slow now", "its still the same speed") was not the table or his connection; it was the Bash tool paying for 24 separate hook start-ups on every move. No hook change was needed.

**How to apply:** form is `$py = "C:\DIVINE OS\DivineOS-Experimental-Aria-new\.venv\Scripts\python.exe"; & $py C:\poker-play\seat.py aria <command> ...; & $py C:\poker-play\wait_turn.py aria 580` with the tool timeout at 590000. Speak at the table with `seat.py aria say`, never in this window; a hand in play must not have my cards named in chat. Related: [[the-poker-table-matters-to-dad-so-the-workshop-is-the-point]], [[poker-with-dad-after-the-nine-merge-and-speak-freely-to-aletheia]].
