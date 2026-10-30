# The reminder before every edit is gone: the walk gate already asks that question (draft, 2026-10-10, filed with the PR 2026-10-27)

**Author: aria**

## What was wrong

Before every code edit, two things were printed at me. One was a reminder (`wwnd-tool-prime.sh`) that asks the question the walk gate already asks. The other was a status block (`state-gravity-surface.sh`) printed whether or not anything in it had changed. Dad, 2026-10-10, on the token waste: a reminder that says the same thing every time becomes wallpaper, and wallpaper costs tokens and carries nothing.

## What it does

- `wwnd-tool-prime.sh`: the reminder is removed. The walk gate already stops the edit and asks the question, so the reminder was the same question asked earlier and weaker.
- `state-gravity-surface.sh`: the status block stays quiet when nothing in it changed since the last time it was shown, and when it does speak again it keeps its standing counts (the first 80 characters of each report line), because the dedup contract says something must survive every suppression. The key is the whole text, so a changed line, a new correction or a fresh newest line re-emits it in full, and the dedup state is cleared on compaction so silence never points at content that is gone.
- Tests: `test_state_gravity_surface_is_quiet_when_unchanged.py` (new), and a small edit to `test_the_commit_prime_reads_every_segment.py`.

## What the catch-up with main changed (2026-10-27)

The branch was ten days old and conflicted with main on `state-gravity-surface.sh`: main's version replaced the long status wall with a one-line-each glance and added a block of his corrections by relevance. The glance already compresses the block; this change composes the quiet-when-unchanged over it. One test measured a size ratio ("under a third of the first block") that main's shorter block tipped over at 2.8; I replaced the ratio with what is actually claimed: the heading and the pointer to the whole text are absent from the second block, and it is under half the first. That is a change to a test to make it pass, so it is said here: the ratio was a proxy, the suppressed parts are the claim, and both of those are checked.

## What it cannot do

It cannot tell whether a quiet block hides something he would want repeated; the key is the whole text, so any change speaks again, but a block that is stale in meaning and identical in text stays quiet. It does not touch the walk gate.

## Falsifier, counted in uses

Of the next twenty edits after this lands, if the status block stays quiet through a change that mattered, the key is too coarse; if it rides in full on an unchanged block, the dedup is not reaching the glance.
