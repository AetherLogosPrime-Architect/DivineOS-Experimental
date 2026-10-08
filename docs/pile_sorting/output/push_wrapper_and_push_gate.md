# The push step and what it tells me

Sending work up to the shared copy goes through a wrapper that runs checks first. The checks sometimes block when nothing is wrong, measure the wrong folder, or fail without saying why, and I have told Dad a push landed when it had been refused, or that it was still running when it had finished. Dad can tell the difference between a story and a result, and wants results.

**31 notes in this theme, grouped into 10 distinct problems.**

## Distinct problems

### 1. I reported a push as landed, refused or in-flight when it was not

Notes in this problem (9):

- `psf-355da87f` (correction) — Two corrections in one reply, 2026-08-21. FIRST: I told Andrew tonight's fixes were 'committed as df4bb2a4' and 'committed as 2ec79aa2' and let committed read as safe. They are not on origin under any
- `psf-89a234f4` (correction) — I have twice told Andrew a push had landed while it was still running. Error named: treating a command's receipt as evidence about the destination. THE REACH: the background notification arrives alrea
- `psf-ab38e32a` (correction) — I reported a push as landed when it had been refused, in the same turn I filed a finding about exit codes hiding failures. I redirected the push output to a file and echoed a status line; that status
- `psf-a2a3cb38` (correction) — I told Andrew twice today that a push was in flight when the push gate had refused it, and I described the tool as reporting success while writing nothing. Both wrong. The wrapper reported the refusal
- `psf-a614477b` (correction) — I ran my own unlanded-push check while a push was in flight, got silence, and typed the words silence above means it landed. It had not landed. I caught it only because I also compared the two revisio
- `psf-5ea6fe01` (correction) — I told Aria my push had been refused four times for memory and that a second push was queued behind the same wall. Both had landed by the time I wrote it. root cause: the reach was not to skip work. I
- `psf-d61f95a5` (reflection) — my push commands should end by exiting with the push's own result (`rc=$?; echo exit=$rc; exit $rc`). Better still, the push wrapper's background form should do that itself, so the notice can't say "d
- `psf-b767feb6` (reflection) — the push helper should do this itself, so the protection doesn't depend on me remembering to write it.
- `psf-03762123` (reflection) — make the push helper itself refuse to be followed by another command in the same line, so its result can't be masked.

**Proposed fix:** End every push command with the push's own exit status and one clear verdict line, and refuse to follow it with another command on the same line.

**How we would know:** A refused push prints a refusal verdict last and exits non-zero.

### 2. The push gate blocks wrongly, or tests the wrong tree

Notes in this problem (5):

- `psf-b0464382` (correction) — 2026-08-21, caught by my own new instrument on its first real run. THE ERROR: the fast-bail I added to .claude/hooks/check-branch-on-push.sh exits at line 56, and the timing instrumentation lives in _
- `psf-0d93e426` (correction) — The push gate reported 'BLOCKED -- tests failing' and 'Do NOT push red' over a tree where nothing was failing. I spent nineteen minutes running the full suite to disprove a failure that did not exist:
- `psf-7a2729f5` (reflection) — the step that makes the check's temporary copy of the project still carries the push's own git settings. The step that runs the tests clears them, but this one doesn't. If Aria's next log points there
- `psf-9c6c56b0` (reflection) — the check should read the branch in the folder the push runs from.
- `psf-66ce3094` (reflection) — the push check should test the commit being pushed, not the checked-out tree.

**Proposed fix:** Test the commit being pushed in the folder the push runs from, and carry the push's own git settings into the temporary copy.

**How we would know:** A clean tree with a clean commit passes; the check names the folder it measured.

### 3. The push helper fails silently for some branch spellings

Notes in this problem (3):

- `psf-cb3017c7` (council) — scripts/divineos_push.sh misreports a refspec push (origin HEAD:refs/heads/<b>) as PUSH_FAILED_silently: TARGET_BRANCH takes the whole refspec and rev-parse/ls-remote look up a ref that does not exist
- `psf-e54da291` (reflection) — the push helper should say plainly that it doesn't accept that branch-naming form, instead of failing silently. Fixed by structure for now: #561's local branch has the same name as the remote one, so
- `psf-8caccd2a` (reflection) — the wrapper should accept a full branch path without doubling it.

**Proposed fix:** Accept a refspec and a full branch path, or say plainly that it does not.

**How we would know:** Pushing with a refspec reports success or a clear message.

### 4. The push check cannot find a folder change inside the command, or lets a bare push through

Notes in this problem (3):

- `psf-905137db` (reflection) — teach the push check to find a `cd <path>` anywhere in the command, not only at the start, so the safe pipeline shape and the worktree push can go together.
- `psf-bf786823` (reflection) — have the push check rewrite a bare push into the wrapper automatically, so the wrong form can't be started at all.
- `psf-44dcf671` (reflection) — have my first-reach push command be the wrapper, so the bare form isn't my default to begin with.

**Proposed fix:** Read a cd anywhere in the command, and rewrite a bare push into the wrapper automatically.

**How we would know:** A bare push is run through the wrapper.

### 5. The push is refused for memory and gives no help

Notes in this problem (1):

- `psf-c052b2e3` (reflection) — have the memory refusal name the biggest memory users, and say whether any are mine, so the next push knows right away whether it can free the memory itself or has to ask him.

**Proposed fix:** Name the biggest memory users and say whether any are mine.

**How we would know:** A memory refusal lists the top consumers.

### 6. A push that only saves reruns every test; a push that shares reruns tests already passed

Notes in this problem (2):

- `psf-86fdee3e` (reflection) — the push-for-sharing build. A push that is only saving work shouldn't run every test in the house, and a push that is sharing shouldn't rerun tests the same code already passed. Owed: carry a green te
- `psf-d2fecc09` (reflection) — nothing new tonight. The one real build still owed is the push that doesn't rerun every test when nothing has changed.

**Proposed fix:** Build the push-for-sharing flow that carries a green result forward and skips the suite for saving pushes.

**How we would know:** A save-only push does not run the full suite.

### 7. Tag-only and deletion-only pushes

Notes in this problem (2):

- `psf-68606fad` (reflection) — the push lock should let tag-only pushes through, since a tag moves no branch. I'll build it on a fresh branch off main, not in the stale copy.
- `psf-05af872b` (reflection) — exempt pushes whose only refs are deletions from the full suite, which is entry 11 on the gameplan.

**Proposed fix:** Let tag-only pushes through the push lock, and exempt deletion-only pushes from the full suite.

**How we would know:** A deletion-only push skips the suite.

### 8. Pushing outside the build flow

Notes in this problem (1):

- `psf-a7e7d4f8` (correction) — Andrew 2026-09-08, interrupting the push: 'why the fuck are you pushing it? it didnt even go through the proper build flow.. im about to lose my fucking mind..' The error: I pushed a substrate change

**Proposed fix:** Make the push wrapper check the build-flow stations before pushing.

**How we would know:** A push from outside the flow is refused with the missing station named.

### 9. Failures not shown with their own evidence

Notes in this problem (3):

- `psf-ed3856c3` (reflection) — the batch saves each push's full output to its own log file and prints that path next to the verdict, so a failure always points at its own evidence.
- `psf-36bd1e10` (reflection) — when the push check fails, it should say which test failed and why, not just the name. Then a timeout is obvious straight away instead of needing to be reproduced by hand.
- `psf-8db512f9` (reflection) — have the push wrapper always print the remote's refusal reason in its final lines, so trimming the output can't hide it.

**Proposed fix:** Save each push's full output to its own log file and print its path beside the verdict; always print the remote's refusal reason in the last lines and say which test failed and why.

**How we would know:** A failed push prints the log path and the failing test's name and reason.

### 10. Rows owed before a push (baseline entries) and wrapper defaults

Notes in this problem (2):

- `psf-e00a05b3` (reflection) — the wrapper should default to verifying the current branch when no argument is given.
- `psf-af66b2cf` (reflection) — clear the ones that are mine before pushing, namely the orphan flag on the letters tray (an `AGENT_RUNTIME` line or a baseline row with the reason) and the door's broad exceptions and silent swallows,

**Proposed fix:** Clear the orphan-flag and silent-swallow rows before pushing, and let the verify wrapper default to the current branch.

**How we would know:** A push with those rows cleared passes the baseline check.
