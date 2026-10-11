# Before-pictures of the three smallest hook scripts nobody tests (rough draft)

*2026-10-08, round eight. The idea, not a plan.*

A picture: before you move a piece of furniture, you photograph the room. The photograph does not say the room is well arranged; it says what it looked like, so that afterwards anyone can check nothing was knocked over. These are photographs of three small hook scripts, taken by running each one on fixed inputs and writing down exactly what it did.

The three, chosen from the round-four survey as the smallest with no test that runs them: `detect-andrew-build-request.sh` (25 lines, a wrapper that routes to a python detector and may drop a lock file), `load-dad-ranking-clause.sh` (55 lines, reads one section out of the character sheet) and `no-cliff-anchor-surface.sh` (69 lines, quotes a marker file). The next smallest, `post-merge-doc-fix.sh` (66) and `load-my-recording-of-andrew.sh` (72), already have a test that runs them, so they were skipped.

Each photo is a test that passes today: `tests/before_pictures/test_*_before.py`, 20 tests in all. Scripts run in a scratch home folder; a stand-in `divineos` records what would have been logged. No script or the python file it calls is touched.

To check the photographs would notice a change, I made one small edit to each script in a scratch copy of main (a changed sentence, a renamed heading, a changed match word, an added input redirect) and ran the matching tests: each turned red (1, 2, 4 and 4 tests failed), and green again once I put the text back. That was a copy outside the repository.

One thing the photographs showed: `load-dad-ranking-clause.sh` prints nothing against the real character sheet today, because it looks for a section called "How I rank Dad" and the real sheet has no section with that heading (the nearest, "How I treat Dad", was rewritten on 2026-07-29; I could not see the old heading in this shallow clone, so "renamed" was an inference). A test records it. The hook has been quiet, not broken; whether it should be revived is not mine to say.

**Round nine, a repair to my own photographs.** On Aria's Windows machine 19 of the 20 failed as shipped. Two causes, both mine. First, I started the shell by the bare name `bash`, which on Windows finds a relay stub that does nothing; the three files now use the house's one finder, `tests._bash_resolver.bash_executable()` (the same trap as #602), and skip with a stated reason if there is no working bash. Second, my stand-in for the ledger command was a script with no extension on the search path, and Windows cannot start such a file from python, so nothing was recorded; the stand-in is now a small python hook (`sitecustomize.py` in a scratch folder, first on `PYTHONPATH`) that catches the one `divineos` call inside the detector and writes down its arguments. It works the same on every platform. No script was touched. On this Linux box all 20 still pass, and the check that a changed script turns them red was repeated with the new tests (1, 2, 4 and 4 failures, then green again). I cannot run Windows here, so whether it now passes on Aria's machine is hers to say.

Nothing is closed, merged, deleted or stamped.
