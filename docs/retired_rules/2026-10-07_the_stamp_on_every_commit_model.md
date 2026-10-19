<!-- retired-rule
id: stamp-on-every-commit
retired: 2026-10-07
retired-by: Andrew
successor: the review stamp lives on the cover only -- the External-Review trailer in the PR body (written by divineos stamp-ready) and in the squash-merge message GitHub builds from it. Commits carry nothing.
pattern: (?i)\bdivineos\s+push-ready\b
pattern: (?i)\brun_push_ready\b
pattern: (?i)amends?\s+(?:the\s+)?trailers?\s+onto\s+(?:the\s+)?branch\s+commits
pattern: (?i)on\s+each\s+guardrail-touching\s+COMMIT\b
-->

# The stamp on every commit

**Retired 2026-10-07 by Andrew. Replaced by a stamp on the cover only.**

## What it said

A branch that touches the reviewed files has to carry an `External-Review` trailer on every one of those commits, not only in the pull request. `divineos push-ready` did it: it found the commits without one, opened an audit round, rewrote each commit's message with `git filter-branch`, filed an aether self-CONFIRMS, and force-pushed with a lease. `divineos stamp-ready` called it as a stage before writing the trailer into the PR body.

## Why it was retired

Dad's rule, said five times and last on 2026-08-19: *"commits do not require an external trailer only merging to main."* On 2026-10-07 I told him what the routine did and he answered *"yes retire it"*.

It was already half-wrong when it was built. The per-commit requirement was removed from the server-side check on 2026-08-13, because it was unmeetable after a force-push, and the check now reads the trailer from the PR body when a commit has none (`scripts/ci_check_guardrail_trailer.sh`, lines about 380 to 387). So a branch with unstamped commits and a stamped body clears it, and the rewrite bought nothing.

It also cost things. Rewriting a commit's message changes its hash, which invalidates any earlier review that named that hash. It needed a force-push, and the routine had to carry a refusal for the case where the local branch was behind the server, because rewriting a stale local branch put old history over the newer work. That went wrong twice on 2026-09-05. The check that guarded it, and the helpers that explained its failures, existed only to make the rewrite safe.

The reason it lasted: the rule changed in speech and the tool that taught the old rule kept running, and the instruction file kept teaching it to me. The same defect as the protected-list model, a fortnight earlier.

## What replaced it

`divineos stamp-ready <pr>` validates the round, writes the trailer into the PR body, and takes the PR out of draft. It no longer touches the branch's commits, and no longer refuses because a branch is behind main. (Corrected 2026-10-18: this line first called that "GitHub's rule at merge". It is not: the ruleset's strict up-to-date policy is false, so nothing refuses a behind branch at merge, and a merge-gate refusal is owed.) `divineos audit prepare-merge` prints the block for the squash-merge message.

The retired code is in `archive/superseded/` at its original paths, with a row in its `LEDGER.md`.
