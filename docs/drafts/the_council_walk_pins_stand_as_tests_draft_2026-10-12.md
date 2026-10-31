# The council-walk pins stand as tests — draft, 2026-10-12

Not a new fix. A test file the helper wrote (#601) to prove problems with the council-walk gate, carried now that most of those problems have been repaired.

## What changed

The helper marked every case "expected to fail" so each could sit quietly until its problem was repaired. Run today against main: sixteen of the nineteen marked cases pass, because the gate now lets read-only look-ups (`audit list`, `prereg show`, `compass-ops history`, `journal list` and the rest) and `--help` through without a walk. A mark on a passing test is a wrong label, and with the strict setting it fails the run.

So this carries the file with those marks removed; they now stand as ordinary regression tests, red the day the repair is undone. **Update 2026-10-30, on today's main:** two of the three cases first kept (`compass-ops spectrums` and `journal search topic`) have also been repaired, and the strict marks turned into failures (XPASS) when I merged main in, which is exactly what a strict mark is for; those two marks are removed too. One case keeps its mark because it is still real:

| Case | Why it still fails today |
|---|---|
| the same file in another working copy | the fingerprint keeps an absolute path (`edit:tmp/pytest/.../other_copy/src/example.py` against `edit:src/example.py`) |

## Proof

On the branch merged with today's main: 22 passed, 1 xfailed (before the two marks came off: 20 passed, 2 failed as XPASS(strict), 1 xfailed). The four control tests (a write still owes a walk, the gate still blocks a write, version and council-show are free, a path inside this checkout is already relative) pass, so the probe is alive. I have not run the forced `--runxfail` pass again on this head; the earlier one (2026-10-12) showed the three failing each for its stated reason.

## Not changed

No source file is touched. The helper's own draft note for #601 is not carried; this note replaces it.

## Falsifier

If any unmarked case fails on main, the repair it pins has been undone and the fix is owed, not the test. If the one kept mark starts passing, it is stale and has to come off, as the others did.
