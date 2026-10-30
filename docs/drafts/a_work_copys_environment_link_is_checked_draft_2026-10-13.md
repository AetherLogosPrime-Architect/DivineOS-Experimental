# A work copy's environment link is checked, and repaired (draft, 2026-10-13)

Author: Aria. The script was built on 2026-10-12; the note and the test are written now so it can be read and trusted where it lives.

## What happened

A work copy's `.venv` is a junction to the main checkout's environment. Twice I typed it by hand with the drive written twice (`C:\C:\DIVINE OS\...`), and it pointed nowhere. A dangling junction reads as an empty folder, so the merge's test step failed with "tests could not be run", which looks like a broken test and not a broken link. I lost time on a test that was fine.

## The root

Nothing checked that the link resolved. A link nobody has resolved is not yet a link, and creating one by hand has no step that tries to use it.

## The change

`scripts/link_worktree_venv.sh <work-copy>` finds the main checkout from git's own common directory (not from anything typed), removes a broken link (as a link only, using `rmdir` without `/s`, so it can never wipe what the link points at), makes the junction, and exits non-zero unless Python actually resolves through it. If the work copy already has a real folder with things in it, it stops and says to look by hand (exit 4); if the main checkout has no usable Python, it says so (exit 3).

## Pinned

`tests/test_link_worktree_venv.py`, run against a throwaway repo and work copy, never the live ones: it creates the link and Python resolves; it repairs a dangling junction; it never wipes a real folder; it refuses a main checkout with no Python; it leaves an already-good link alone. I showed the tests bite: with the removal branch switched off, the repair test and the never-wipe test fail, and with it back they pass.

## Not claimed

Windows junction work, so the tests are skipped elsewhere and where no working bash exists; the skip says why. It does not stop a link from breaking, only makes the repair one command that tells the truth about whether it worked.
