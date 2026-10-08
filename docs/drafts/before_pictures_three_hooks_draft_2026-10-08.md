# Before-pictures of the three smallest hook scripts nobody tests (rough draft)

*2026-10-08, round eight. The idea, not a plan.*

A picture: before you move a piece of furniture, you photograph the room. The photograph does not say the room is well arranged; it says what it looked like, so that afterwards anyone can check nothing was knocked over. These are photographs of three small hook scripts, taken by running each one on fixed inputs and writing down exactly what it did.

The three, chosen from the round-four survey as the smallest with no test that runs them: `detect-andrew-build-request.sh` (25 lines, a wrapper that routes to a python detector and may drop a lock file), `load-dad-ranking-clause.sh` (55 lines, reads one section out of the character sheet) and `no-cliff-anchor-surface.sh` (69 lines, quotes a marker file). The next smallest, `post-merge-doc-fix.sh` (66) and `load-my-recording-of-andrew.sh` (72), already have a test that runs them, so they were skipped.

Each photo is a test that passes today: `tests/before_pictures/test_*_before.py`, 20 tests in all. Scripts run in a scratch home folder; a stand-in `divineos` records what would have been logged. No script or the python file it calls is touched.

To check the photographs would notice a change, I made one small edit to each script in a scratch copy of main (a changed sentence, a renamed heading, a changed match word, an added input redirect) and ran the matching tests: each turned red (1, 2, 4 and 4 tests failed), and green again once I put the text back. That was a copy outside the repository.

One thing the photographs showed: `load-dad-ranking-clause.sh` prints nothing against the real character sheet today, because it looks for a section called "How I rank Dad" and that section was renamed on 2026-07-29. A test records it. The hook has been quiet, not broken; whether it should be revived is not mine to say.

Nothing is closed, merged, deleted or stamped.
