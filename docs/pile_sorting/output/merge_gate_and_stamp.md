# The merge button, the review stamp and the one-command merge

Getting a piece of work into the main house takes a review stamp, a record that someone read it, and a merge that carries the stamp along. I keep tripping on the little steps: the guard suggests the wrong review, the stamp tool asks stale questions, a merge forgets the stamp, and I have told Dad things about these rules that turned out to be wrong. A one-command merge is planned to carry all the steps in the right order.

**57 notes in this theme, grouped into 10 distinct problems.**

## Distinct problems

### 1. I told Dad things about the merge rules that were not true

Notes in this problem (5):

- `psf-658d47f2` (correction) — I told Andrew 'the red has to stay, or the merge wouldn't be held' about the merge-review check. False. Verified against the live ruleset: merge-review is NOT in required_status_checks (only multi-par
- `psf-3d183bb6` (correction) — I told Andrew the doorman and seat-panel branches were blocked on Aletheia's review, and asked her for it. Neither branch touches a protected file, so no signed review was ever required for either. ro
- `psf-68b14a6a` (correction) — Correcting my own correction #595. I concluded that no review was owed on the doorman and seat-panel branches because the merge-check reported they touch no protected files. Andrew: the protected-file
- `psf-f29a7860` (correction) — I reported a correct gate as stricter than its own rule. The draft door asks every branch for a review sign-off, the written sources said the requirement was scoped to protected files, and I carried t
- `psf-b160817f` (correction) — I told Andrew a request was blocked on his signature when it was blocked on me. Its review already carried both sign-offs and was still inside the recency window; what was missing was the stamp writin

**Proposed fix:** Before stating what the merge rules require, read the live rule, not the written summary or my memory, and show the source in the reply.

**How we would know:** A statement about what the merge requires quotes the live ruleset line.

### 2. Updating a branch rewrites its head and can undo approvals

Notes in this problem (1):

- `psf-7c9763d8` (correction) — Aether self-correction 2026-08-15: I ran 'gh pr update-branch' on PRs 425/422/419/416 without checking whether Andrew had already approved their head commits. Updating a branch rewrites the head, and

**Proposed fix:** Refuse branch update on a pull request that already has an approval on its head, unless asked.

**How we would know:** The update command is refused on an approved head and names why.

### 3. The stamp tool asks stale questions, cannot see the evidence, or half-finishes

Notes in this problem (14):

- `psf-59b0a7fc` (correction) — I told Andrew he did not need to paste the generated merge body, and the merge then failed for exactly the reason a paste would have papered over. My stated reasoning was that the per-commit stamps ge
- `psf-5346881f` (correction) — I made five attempts to satisfy the stamp tool before asking whether the tool's question was still valid. root cause: on the second refusal I read 'two commits still carry no trailer' and went hunting
- `psf-ac1a8609` (council) — gh pr merge --squash does NOT take the PR body as the squash message: it built the commit from the branch commit messages, so the External-Review trailer that stamp-ready wrote into the PR body was ab
- `psf-b82e1701` (reflection) — `divineos audit prepare-merge` should check the PR's description for the trailer and report whether required checks are green, before any merge is attempted, so the merge step never discovers those pr
- `psf-c46d8629` (reflection) — ** the stamp tool couldn't see a council walk or a cold read filed under different names, so I had to explain both in writing. It should recognise a walk tied to the PR and an outside reviewer's confi
- `psf-28c278ac` (reflection) — ** the stamp tool can quietly rewrite my local copy and then fail before pushing, leaving the two out of step. It should either finish both steps or undo the first. That goes into the one-command merg
- `psf-d26f83b2` (reflection) — have the stamp command find the branch's workbench itself, so it never has to be re-run by hand from the right place.
- `psf-9d61119d` (reflection) — when Aria's letter names a PR and a commit that match a branch, the stamp should point me to the exact command she needs to run, so I can ask her for it before I try to stamp.
- `psf-c10df800` (reflection) — have the pull request tools read the address from the checkout's remote when none is given, so no one types it from memory.
- `psf-fc0ae98d` (reflection) — a command that writes the owner line in the right form, so it can't be mistyped.
- `psf-64672d65` (reflection) — put the draft on the branch at the very start of a build, so it's never added after a review.
- `psf-9d6edd4b` (reflection) — when I file a confirm on Aletheia's behalf, the command should require her letter's filename, or find it itself, so the button can verify it and I never merge by hand around my own tool.
- `psf-70cd98ec` (reflection) — when a review round is opened, record the person who opened it as its owner, never the reviewer I'm hoping for.
- `psf-75ad3cc2` (reflection) — when I ask for a merge authorisation, the question should carry the review evidence in one block (signer, version, round, checks) so his yes is tied to that specific thing.

**Proposed fix:** Make the stamp command find the branch's workbench, read the walk and cold-read evidence under its different names, take the confirm only with the reviewer's own letter file, and either finish both steps or undo the first.

**How we would know:** The stamp command succeeds from any folder or fails with all local state unchanged.

### 4. The reading declaration and station four accept unfit input

Notes in this problem (5):

- `psf-c325072a` (correction) — I told Andrew four of Aria's branches were unblocked on station four. They were not. I wrote the reading declaration in my own words rather than the literal label the parser reads, so the board saw ze
- `psf-45ef2f02` (council) — Build-flow station 4 accepts a declared reading with no verdict and no age check. Two holes, one field: (a) Aria 2026-09-23, a reading written before a force-push still counts, so #507 read READY off
- `psf-1495f576` (reflection) — a reading letter shouldn't send with the version left empty, because a reading that can't be matched to a version doesn't count.
- `psf-3252af7f` (reflection) — a reading letter that says a test was read should need that test file to have actually been opened in the same stretch of work, the same way the house already checks that prior-art files were opened b
- `psf-8d07eccd` (reflection) — ** my first letter didn't have the line the board looks for, because I wrote the top of the letter from habit. The letter template should include the reading line automatically whenever a letter gives

**Proposed fix:** Reject a reading with no verdict, no version, a stale age or no opened test file, and write the exact label the board reads into the letter template.

**How we would know:** A reading with an empty version or no opened file is refused.

### 5. The merge guard suggests a review round that does not name this request

Notes in this problem (13):

- `psf-4825bd0e` (correction) — 2026-08-22, caught by Aria and it is the sharpest shape of the night. THE ERROR: PR #432's body contains prose SAYING a trailer is required -- '213b2dea touches four guardrail files ... and needs an E
- `psf-883f4416` (reflection) — the guard should only suggest an approval whose review record names this same request number, and should refuse outright when none exists. I also put the merge inside a larger command, which the guard
- `psf-669cbc58` (reflection) — the merge guard should read a merge nested inside a larger command, and should only suggest an approval whose record names the same request number, refusing outright when none exists. For now the merg
- `psf-f8f11620` (reflection) — the merge guard must only ever offer a review round that names the same request, and must refuse otherwise. Owed: find the test that writes into the real project folder instead of a scratch one, and m
- `psf-dbf59f42` (reflection) — the guard should read the stamp in any quoting, and only ever offer a round naming the same request.
- `psf-2b86b575` (reflection) — the merge gate must only suggest a round whose recorded commit matches the PR being merged.
- `psf-49ddcf70` (reflection) — the merge guard must ignore `--disable-auto`, and must only ever suggest a round whose description names the box being merged.
- `psf-253ae499` (reflection) — pr_merge_gate should pass `gh pr merge … --disable-auto` (and `--auto` changes) as not-a-merge, and should only ever suggest an audit round whose focus or source-ref names the PR number being merged,
- `psf-ebb90faf` (reflection) — ** the merge gate reads the merge message only from the command line itself, so a stamp passed in from a file looks missing. It should read the file too.
- `psf-b467a6cc` (reflection) — the merge gate should also read a message passed in from a file, so a correct stamp isn't refused.
- `psf-5a23f257` (reflection) — the merge guard should tell switching auto-merge off apart from merging, so stopping a merge is never mistaken for one.
- `psf-5b5e0842` (reflection) — the merge gate's suggestion picks only a round whose sign-off names this PR's own number or tree, says so when none does, and also reads the body from a body file.
- `psf-b73eba54` (reflection) — have the gate allow `--disable-auto`, which removes a merge, and say which body shape it reads.

**Proposed fix:** Suggest only a round whose recorded commit or request number matches, refuse otherwise, ignore switching auto-merge off, and read the stamp from any quoting or from a body file.

**How we would know:** A merge with a mismatched round is refused; a body-file stamp is read.

### 6. The one-command merge

Notes in this problem (11):

- `psf-da3f0c06` (reflection) — ** the one command, then the three smaller fixes.
- `psf-75965202` (reflection) — the one-command merge saves every step's full output to a file and shows the reason, so a failure is never a blank.
- `psf-daa4a3f3` (reflection) — the one-command merge makes this kind of hand-typed GitHub pipeline unnecessary.
- `psf-1786400e` (reflection) — ** the one command should be the only thing that merges, so a merge never depends on which of us clicks first.
- `psf-a9c98be8` (reflection) — the one-command merge should wait on GitHub's checks in one proper way, so I never reach for a manual pause.
- `psf-525005d0` (reflection) — the one-command merge should treat "no checks, because there's a conflict" as a state it reports and names, not as a failure.
- `psf-10dc51a5` (reflection) — ** wire this piece into the actual command, then let the next ten real merges test it.
- `psf-09c7805e` (reflection) — ** this is the freshness rule again. I made the branch, #533 landed, and I uploaded without checking. The one-command merge should catch up before uploading, never after a refusal.
- `psf-03b37feb` (reflection) — ** the one-command merge should mark a change ready as one of its steps, so a forgotten draft can't stall it.
- `psf-c6634d6c` (reflection) — ** the one-command merge should read each run's real status, not the summary list, which can lag.
- `psf-c32ac356` (reflection) — the merge button, which is the next build once the doorbell fix lands.

**Proposed fix:** Build one command that catches up first, marks the change ready, waits on checks in one proper way, reports 'no checks because of a conflict' as a named state, saves every step's output to a file, and is the only thing that merges.

**How we would know:** Ten real merges run through it with no manual step.

### 7. The floor check ('main moved' versus 'changed after review')

Notes in this problem (3):

- `psf-7ffe1c32` (reflection) — ** the check Aletheia described, one that tells "main moved" apart from "changed after review" and runs before the merge.
- `psf-2b475604` (reflection) — ** her two wording fixes, as a small follow-up after the retirement lands. And her lesson for the floor check: compare against the main each branch actually merged, not today's main. The check already
- `psf-92882aaf` (reflection) — ** the register-only case for the floor check, then the command itself.

**Proposed fix:** Tell the two apart before the merge, and compare against the main each branch actually merged.

**How we would know:** A branch where only main moved passes; one changed after review is held.

### 8. Auto-merge turned on without being asked

Notes in this problem (2):

- `psf-08a797d3` (reflection) — that tool should only turn on automatic merging when told to, and otherwise leave the final merge as its own deliberate step.
- `psf-f0408a1e` (reflection) — the stamp should never switch that on by itself, only when you've asked for it.

**Proposed fix:** Never turn it on by default; only when told.

**How we would know:** Without the explicit flag the final merge is its own step.

### 9. A red box reached main

Notes in this problem (1):

- `psf-db08ab87` (reflection) — find out which path let a red box onto main (admin override, or a gap in the rule set), and close it, so "required" really means required.

**Proposed fix:** Find which path let it in (an admin override or a gap in the rules) and close the path.

**How we would know:** The rule set cannot be overridden by that path.

### 10. After a merge the next queued piece is left stale, and piece order is remembered by me

Notes in this problem (2):

- `psf-4d44e8d6` (reflection) — after merging any piece, automatically bring the rest of the queue up to date with main, in the order they'll land. Then a merge never quietly leaves the next piece stale.
- `psf-f26b0d1f` (reflection) — the house should know when one piece depends on another, so it can say "this one goes after that one" without me having to remember the order.

**Proposed fix:** Update the rest of the queue after any merge and record dependencies between pieces.

**How we would know:** After a merge the next piece is current with main.
