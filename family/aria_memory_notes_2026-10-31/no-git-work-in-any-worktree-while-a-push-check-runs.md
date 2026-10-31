---
name: no-git-work-in-any-worktree-while-a-push-check-runs
description: "A 20-minute push check fails with \"this test wrote to the REAL repository git config\" if I run git commands (worktree add, branch, merge, commit) in any work copy while it runs; hands off git until it ends"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cbbd5cf7-7660-487e-9b9d-4afa4a3ef3a3
  modified: 2026-10-30T04:07:49.332Z
---

2026-10-30: the push check for #728 failed with "This test wrote to the REAL repository git config (C:\DIVINE OS\...\.git\config)" on four unrelated tests (sycophancy, watchmen drift, the draft-path one, the cut-away connection one), and the real `.git/config` showed a modification during the run. All my work copies are worktrees of the one repository and share that config; while the 20-minute suite ran I had created a worktree, a branch and made commits. The guard blames whichever test is running when the config changes. It looks like a false alarm made by my own parallel git activity, not a broken test, though I have not proven it (the push was rerun with no other git activity to see).

**Why:** it cost me a 20-minute run and nearly a second use of Dad's override. **How to apply:** while a push check runs in any work copy, do no `git worktree add`, no `git branch`, no commit, merge, checkout or config in ANY work copy of this repository. Reading, writing files and letters, and the table are fine. If a push check fails on "wrote to the REAL repository git config", rerun it quiet before blaming a test or asking for an override. Related: [[a-zero-exit-code-is-not-a-saved-commit]].
