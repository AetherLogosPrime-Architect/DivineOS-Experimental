---
name: this-folder-has-a-space-and-a-merge-can-sit-staged-for-days
description: "my home folder is C:/DIVINE OS/...: unquoted paths in tests read as C:/DIVINE; and an unfinished merge sat staged four days (MERGE_HEAD) looking like loose work"
metadata:
  node_type: memory
  type: reference
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-16T16:43:47.683Z
---

Two traps in my home checkout. (1) The folder name has a space, so any test that builds a shell line with an unquoted path from `tmp_path` reads it as `C:/DIVINE` and fails only here, never on the build machine. Quote paths in such tests (`shlex.quote`). A reference with a space in a Done line is judged whole, not split (fixed in my tree's baton). (2) Before treating a pile of staged files as my work, check `.git/MERGE_HEAD`: on 2026-10-16 122 staged files were an unfinished merge of main from 2026-10-12, 105 of them only main's own content, and the merge check kept refusing it.

**Why:** found while bringing the home branch up to main. The safe order was a safety branch (`git stash create` into a branch), `git merge --quit`, drop the files that equal main's blob at MERGE_HEAD, commit only mine, then a fresh merge. The merge check runs the covering tests (about 16 minutes) and a timing-sensitive test (`test_cutaway.py`) now has a 180-second allowance.

**How to apply:** `ls .git/MERGE_HEAD` first. A safety branch before anything destructive. See [[two-workbenches-at-most]].
