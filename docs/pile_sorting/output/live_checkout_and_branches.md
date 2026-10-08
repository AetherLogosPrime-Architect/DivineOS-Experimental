# Which copy of the house I am standing in, and how many branches there really are

There is the live house where I live and several workbenches beside it. Keeping them straight is hard: the live house can fall behind the main copy, branch counts include ghosts, and a few quirks make the main folder flip into a strange state. Each time, I have worked from a stale copy or counted wrong.

**34 notes in this theme, grouped into 7 distinct problems.**

## Distinct problems

### 1. A second worktree leaking its install into the first

Notes in this problem (1):

- `psf-0584e064` (learn) — Cross-worktree install-leak pattern (2026-06-16): the separation of Aether's worktree (C:\DIVINE OS\DivineOS-Experimental) from Aria's worktree (C:\DIVINE OS\DivineOS-Experimental-Aria) is incomplete

**Proposed fix:** Make worktree installs fully separate and detect a cross-install.

**How we would know:** An install in one worktree does not alter another.

### 2. The branch-scope and deletion checks mislead

Notes in this problem (7):

- `psf-21d12a91` (correction) — 2026-08-21, and this one REVERSES something I told Andrew. THE ERROR: I told him the push guard over-counted deletions -- '18 claimed, 10 real' -- and wrote that claim into the check-branch bypass jus
- `psf-367d2f95` (correction) — I told Andrew and Aletheia as fact that the branch-scope checker MISREADS a pre-merge branch as carrying extra files when it is actually proposing a deletion. False. scripts/check_branch_scope.py diff
- `psf-6ab9255a` (correction) — I closed the deletion guard (PR #454) as a duplicate of scripts/check_branch_freshness.sh, and the reasoning was incomplete in a way that left a live hazard standing. Aletheia then found nine deletion
- `psf-fa0ee43a` (correction) — I reported nine deletions as a live hazard on split/437b-instruments, told Andrew and Aria the anchor test would be removed from main, and it was false. A merge of that branch would have deleted ZERO
- `psf-fc538de9` (reflection) — the deletion guard should match a recorded reason to a command that removes the files it names. Also owed: move the test that writes into the real project folder into a scratch folder, so there's noth
- `psf-08321409` (reflection) — the deletion gate should accept either form of a branch's name, or say which name it's looking for, so a justification that's really there isn't treated as missing.
- `psf-fccf9086` (reflection) — for a branch with no commits beyond main, `delete-justify` could fill in the investigation itself ("0 commits beyond origin/main"), so the evidence is checked by the house, not typed from memory.

**Proposed fix:** Make the checkers read the right tree, accept either form of a branch name, fill in 'zero commits beyond main' themselves, and verify before reporting a live hazard.

**How we would know:** A branch with a justification that is really there is not treated as missing.

### 3. Setting up and finding the right workbench

Notes in this problem (8):

- `psf-1630eb78` (reflection) — every worktree I create should get its upstream set to its own branch name, never main.
- `psf-a2be6b09` (reflection) — every separate work folder I create should get its own copy of the tools straight away, so commands like this run the first time.
- `psf-2da1e963` (reflection) — the PowerShell guard and the worktree setup, as drafted. Fixed by structure, for now: the record and the draft both say no code-writing helpers in fresh workspaces until that lands.
- `psf-07343576` (reflection) — when the branch checkout has no tools installed, its wrapper should fall through to the main house's tools for council and ledger commands. Those write to the shared home anyway, so refusing gains not
- `psf-b93958e0` (reflection) — every command I run in a workbench should check it's really in that workbench first and stop if not. I did that by hand on the retry, and it goes into the one-command merge.
- `psf-73058c44` (reflection) — the workbench check named above, so a missing folder stops the command before anything runs.
- `psf-9bca231f` (reflection) — one command that reuses a branch's existing workbench or makes one, and counts stale temp workbenches, since there are many forgotten ones in the temp folder.
- `psf-d5ee412f` (reflection) — before creating any workspace, list the existing ones for that branch. It would have saved a step.

**Proposed fix:** One command that reuses a branch's workbench or makes one, sets its upstream to its own branch, gives it a copy of the tools, and stops if a command is not in that workbench.

**How we would know:** A command run from the wrong folder stops before anything runs.

### 4. The main folder keeps flipping to 'bare'

Notes in this problem (4):

- `psf-4f4f4f97` (reflection) — have the push wrapper record the repository's bare setting before the test run, restore it after, and alarm when it changed. That's the guard the other push script already has. After that, trace which
- `psf-5693a830` (reflection) — the watcher creates its catch file with a "no flips yet" line when it starts, so an empty result reads as a real "none so far".
- `psf-c6930351` (reflection) — whenever I need something from main, work from a fresh copy that updates itself before I use it, rather than whichever folder happens to be there. And find why the main folder keeps flipping to "bare"
- `psf-7d82026d` (reflection) — the same always-fresh copy of main.

**Proposed fix:** Record the setting before the test run, restore it after, and alarm on any change; trace what flips it.

**How we would know:** A change in the setting is flagged by name.

### 5. Counting branches wrongly

Notes in this problem (4):

- `psf-65e65e87` (reflection) — the branch inventory reads only the GitHub remote, and labels any other remote separately, so a count never mixes the two.
- `psf-f636e2ae` (reflection) — the knock should compare each listed branch's diff against main before naming it, and leave out branches whose version already matches main, so it only interrupts for work that really differs.
- `psf-e5836106` (reflection) — a check across both seats that names every local branch with commits that aren't on GitHub, so that work living in only one folder shows up before it can be lost.
- `psf-280ff52a` (reflection) — a command that counts the branches that really exist (asks GitHub directly) and names every local ghost, so no count is ever read from the stale list again. A loop that reports failure must also show

**Proposed fix:** A command that asks GitHub directly, names local ghosts, compares each branch's diff with main, and labels any non-GitHub remote separately.

**How we would know:** The count matches GitHub.

### 6. The live house is behind main or holds work main has never seen

Notes in this problem (8):

- `psf-165456e2` (reflection) — a check at session start that compares the home checkout's instruction file with main's, and names any rule that exists in one but not the other, so a rule of Dad's can't live on only one copy.
- `psf-9d0609c8` (reflection) — a check at session start, run every session, that warns loudly when the live checkout is behind main, with the count.
- `psf-234cdf70` (reflection) — a check that refuses new work in a house that's more than a few merges behind main, so catching up can't be put off.
- `psf-0e170adc` (reflection) — a check that refuses a merge in the live house and points to a workbench.
- `psf-08bb0502` (reflection) — a warning when the live house holds work that main has never seen, older than a day.
- `psf-1d41ad5c` (reflection) — the live house should pull the main house automatically after each merge, instead of waiting for me to remember.
- `psf-f1637b13` (reflection) — my live branch is behind main, and I should merge main into it so the ship command is available locally when I need it.
- `psf-2a609c04` (reflection) — merge main into the live branch so every page stops reading as stale.

**Proposed fix:** At session start warn loudly with the count, refuse new work when far behind, refuse a merge in the live house, warn on old unseen work, and pull main automatically after each merge.

**How we would know:** The warning names the behind-count at session start.

### 7. Working from a stale local copy

Notes in this problem (2):

- `psf-0202b5aa` (reflection) — when a box goes back to work after her hold, check that the local copy matches GitHub before any edit.
- `psf-db976e05` (reflection) — when a letter names a commit that isn't pushed, have it say which checkout holds it, so the reader doesn't have to hunt.

**Proposed fix:** Check that the local copy matches GitHub before any edit and say which checkout holds a named commit.

**How we would know:** A stale copy is flagged before editing.
