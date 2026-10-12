# The council-walk pins stand as tests — draft, 2026-10-12

Not a new fix. A test file the helper wrote (#601) to prove problems with the council-walk gate, carried now that most of those problems have been repaired.

## What changed

The helper marked every case "expected to fail" so each could sit quietly until its problem was repaired. Run today against main: sixteen of the nineteen marked cases pass, because the gate now lets read-only look-ups (`audit list`, `prereg show`, `compass-ops history`, `journal list` and the rest) and `--help` through without a walk. A mark on a passing test is a wrong label, and with the strict setting it fails the run.

So this carries the file with those sixteen marks removed; they now stand as ordinary regression tests, red the day the repair is undone. Three cases keep their marks because they are still real:

| Case | Why it still fails today |
|---|---|
| `compass-ops spectrums` | still owes a walk (fires `substrate-write-cli`) |
| `journal search topic` | still owes a walk (same feature) |
| the same file in another working copy | the fingerprint keeps an absolute path (`edit:tmp/pytest/.../other_copy/src/example.py` against `edit:src/example.py`) |

## Proof

Normal run: 20 passed, 3 xfailed. Forced run with the marks off (`--runxfail`): the three fail with AssertionError, each for its stated reason, read from the failure text. The four control tests (a write still owes a walk, the gate still blocks a write, version and council-show are free, a path inside this checkout is already relative) pass in both runs, so the probe is alive.

## Not changed

No source file is touched. The helper's own draft note for #601 is not carried; this note replaces it.

## Falsifier

If any of the sixteen unmarked cases fails on main, the repair they pin has been undone and the fix is owed, not the test. If any of the three kept marks starts passing, its mark is stale and has to come off, as these sixteen did.
