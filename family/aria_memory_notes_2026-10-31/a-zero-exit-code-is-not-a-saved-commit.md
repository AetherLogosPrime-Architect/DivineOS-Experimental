---
name: a-zero-exit-code-is-not-a-saved-commit
description: "A background commit or push that reports exit code 0 may have been refused or failed; verify by the repository (git log, MERGE_HEAD, ls-remote) and never by the notice; plus the two traps that burned an hour on 2026-10-26."
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T01:06:23.551Z
---

2026-10-26, three times in one evening: a background task reported exit code 0 and the thing had not happened. (1) `git commit; git stash pop` chained with `;` returned the stash pop's code while the merge-test had REFUSED the commit. (2) A background commit's "completed (exit code 0)" was the trailing `git log` line. (3) A background `git push` ended before I looked, and I wrote "running" about something the freshness check had already stopped. Every time, the true state was one command away.

**Check the record, not the notice:** after a commit, `git log --oneline -1` and `git rev-parse -q --verify MERGE_HEAD` (a merge still pending means it was refused) plus the check's own verdict lines (`grep "merge-test\]\|passed,\|^FAILED"` in the output file). After a push, compare `git rev-parse HEAD` to `git ls-remote origin refs/heads/<branch>`.

**Two traps from the same evening:**
- Never `git worktree add` (it writes branch entries to the shared git config) or push with `-u` while a long check is running: the real-repository-config tripwire fires on a test and the merge check refuses. A false alarm of my own making, ~20 minutes lost, twice.
- The merge check takes 12 to 25 minutes and main moves meanwhile: push IMMEDIATELY after a fold, and if the push's freshness check stops it, the second fold is short (one new commit) so redo it at once.

Also learned: a refusal is a gate doing its job; read which test and why before touching it. Related: [[look-in-the-folders-where-unpushed-work-lives]].
