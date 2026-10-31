---
name: hooks-seventy-seven-running-seven-planned
description: "The hook consolidation (about 100 hooks down to 7 thin ones, logic in the OS) is about a quarter done; measured 2026-10-28. Dad's reason is transferability: an OS that is hooks plus an IDE is not portable."
metadata:
  node_type: memory
  type: project
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-28T21:07:09.877Z
---

Measured 2026-10-28 from `.claude/settings.json` and the hooks folder: **168 files** in `.claude/hooks`, but only **77 distinct scripts** are registered (79 registrations: PreToolUse 32, Stop 23, PostToolUse 17, UserPromptSubmit 3, SessionStart 2, PreCompact 1, PostCompact 1). Of those 77: 22 thin (30 code lines or fewer), 39 medium, 16 heavy (over 100 lines; the compaction-ritual hook is about 500). Four generated `doorbell-*.sh` hooks exist ("one of seven. All judgment lives in the OS") and are the consolidation that was built; the old thick hooks were never removed, so they sit under the doorbells.

Dad asked this nine times (2026-08-03 to 10-08, most recently *"why are there 78 hooks? i thought we consolidated them all down to 7 hooks and moved the hook logic into the OS?"*) and on 2026-10-28, told the finding, said: *"yes include it... getting this done from a quarter to fully done would help immensely.. im sure the hooks are running you ragged, also the reason i want the logic in the OS and not the hooks is because otherwise its not much of an OS just an IDE with hooks and it wouldnt be transferrable without serious setup"*.

**Why it matters:** an OS whose logic lives in IDE hooks is not portable; the logic belongs in the OS, with hooks as thin pointers.

**How to apply:** the system map carries this as a finding ("hooks: seven planned, seventy-seven running"). Finishing the consolidation is owed work for after the merge pile clears, with the heavy sixteen first. Do not claim the consolidation is done anywhere. Related: [[extraction-and-sleep-go-last-and-why-the-start-is-850k]].
