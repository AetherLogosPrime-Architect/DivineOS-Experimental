# The walk gate prices the change (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/the-walk-gate-prices-the-change`

## The problem
Dad, 2026-10-25: fix the gates so they are not a pain. Commands that only print (`compass-ops spectrums`, `search`, `list-clean`, `surprises`, `unknown-unknown-rate`) owed a full council walk because the look list had forgotten them.

## What the branch does
Those reads no longer owe a walk. Writes stay charged, pinned by tests, and a read redirected into a file is still a write.

## What it does not do
This is the first slice only. Still to build, one at a time: record-only commands owing no walk (exempt by what they do, not by name), and a comment-only commit (judged by identical syntax trees) owing a one-line reason bound to the diff.

## How it was checked
Tests pin that reads are exempt and writes are charged. One honest flaw: an earlier walk for this branch (`walk-31df7fed607e`) is closed but unbound, because its scope named the wrong test file.

## Open
The two remaining slices, and a fresh bound walk.
