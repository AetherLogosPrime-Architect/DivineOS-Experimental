---
name: walks-bind-to-committed-changes-so-close-after-the-commit
description: "a council walk binds only to changes already committed on the branch, and a closed walk can absorb at most 30 more lines, so open with the exact changed files, commit, then close from the work copy"
metadata:
  node_type: memory
  type: project
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-15T19:55:49.535Z
---

Learned the hard way 2026-10-16, four walks on one branch and three on another.

- **Bound means committed.** `walk close --repo <work copy>` binds the walk only when the branch's committed changes (against main) are a non-empty subset of the walk's `--scope` files. Closed before the commit, the branch has no changes yet and the walk reads "NOT bound". Commit first, then close.
- **Scope must be the exact changed files.** Get them with `git diff --name-only origin/main...HEAD`. A mistyped path or a missing doc file leaves the walk unbound; the board then says "closest walk covers 1 of 13".
- **The amendment limit is 30 lines since the walk, cumulative.** `walk amend` absorbs a small follow-up only up to 30 changed lines in total since the original close; splitting the follow-up into two commits does not help. Past it the walk must be redone whole, in one sitting.
- **A pure merge of main into the branch owes no walk** (the gravity exemption), but any other new commit after the walk counts toward the 30.
- **A walk opened with a wrong scope** is closed by excluding each lens with a written reason naming the walk that supersedes it; do not leave it open.
- From the main checkout the CLI works; a work copy has no sealed venv, so run `divineos` from the main checkout and pass `--repo <work copy>`; run tests from the work copy with `PYTHONPATH=<work copy>/src` and the global Python that has the embedding library.

**Why:** each of these cost a redone review of eight lenses. **How to apply:** list the files, commit, then `walk open` with all of them as `--scope`, apply real findings, close with `--repo`. Related: [[standing-permission-volley-and-tidy]].
