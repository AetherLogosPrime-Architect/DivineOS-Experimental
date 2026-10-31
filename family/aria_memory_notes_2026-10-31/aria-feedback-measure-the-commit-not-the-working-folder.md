---
name: aria-feedback-measure-the-commit-not-the-working-folder
description: "To say what a pushed branch carries, read the commit (git show <head>:file, or a three-dot diff of refs), never git diff against the working folder; I told Aletheia twice the wrong thing from a dirty folder"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-19T17:08:33.878Z
---

2026-10-18: I told Aletheia twice that my pushed heads of #645 and #659 carried three command-count edits (508 to 512 in CLAUDE.md, README.md, ARCHITECTURE.md). I had measured with `git diff origin/main`, which compares the files in my **working folder**, and the pre-commit step had left **uncommitted** count edits there. She checked `git show <head>:README.md`, found 508 at the pushed head, and was right. The only branch that had actually committed them was a different one.

**Why:** a working folder is a different object from the commit I was asked about, and it agreed with what I expected (the right KIND of thing, not the right thing). Same family as [[three-correction-stores-mine-is-divineos-aria]]: the wrong twin returns a plausible answer.

**How to apply:** to state what a branch carries, use refs only: `git diff --name-only origin/main...<head>` (three dots, committed objects) or `git show <head>:<path>`; never `git diff origin/main` alone, and check `git status` is clean first. Aletheia's habit, adopted: *`git show <head>:file` and never the working folder.* Also: a merge that will not start with "your local changes would be overwritten" means exactly this leftover; check it against main before discarding and record the discard with `divineos delete-justify`.
