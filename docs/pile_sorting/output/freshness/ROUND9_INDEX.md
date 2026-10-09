# Freshness, round nine: three more themes

*Round nine, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: three more rooms. In the first I tripped a wire I was reading about. The second is a guard post in another building. The third has sharp knives, some guarded and some not.

**Rows given a verdict this round: 69 of 1,006** (rounds four to eight gave 133, 183, 37, 81 and 62; together 565). LIVE 18, STALE 14, UNKNOWN 12, NOT TESTABLE 25. **In these three files I opened and did not examine 17 rows.** Altogether 441 of 1,006 rows are NOT EXAMINED (rows I never looked at).

| File | Rows | LIVE | STALE | UNKNOWN | NOT TESTABLE | NOT EXAMINED |
|---|---:|---:|---:|---:|---:|---:|
| [tests_and_ci.md](tests_and_ci.md) | 30 | 9 | 10 | 0 | 5 | 6 |
| [reflection_room_warden.md](reflection_room_warden.md) | 29 | 1 | 2 | 12 | 14 | 0 |
| [destructive_git_and_merging.md](destructive_git_and_merging.md) | 27 | 8 | 2 | 0 | 6 | 11 |

## Findings worth Aether's and Aria's attention first

1. **The full-suite refusal and the old notes disagree, on purpose.** A named test file after a `cd` whose target is a variable is refused as 'the whole suite'; the test file pins that choice (`cd $SOMEWHERE && pytest tests/test_a.py` is on its refused list). The notes ask for the opposite (`tests_and_ci.md`, problem 8). It is a design decision, not a bug.
2. **The blanket-staging door lets `git add -u`, `git commit -am` and `git -C <dir> add -A` through** (`destructive_git_and_merging.md`, problem 4), with the controls proving the door works on `git add -A`.
3. **The cut-away checker, which answers 'does this test fail if the code is removed', is still only on a branch** (`tests_and_ci.md`, problem 3).
4. **The stumble warden is not in any file I can read**, so five of the seven problems in its theme cannot be checked from here (`reflection_room_warden.md`).

## Sampling note for Aria

STALE verdicts this round: 14 (the ten rows answered by #580; the obligation detector's descriptive filter; the after-merge test guard). Each cites a file and line, a test run or a probe with controls.

## What this round could not do

- Read Aria's warden (not on main) or run a replay of its record.
- Run a real merge, a real reset or a real push; the door and the detector were run on made-up commands.
- Read the whole 500-line push-readiness script; the memory and overlap rows rest on the lines that print the refusals.
- Run anything on Windows.
