# The merge check tests what I changed, in a fixed order (built)

Aria, 2026-10-27. Dad, after the third refused commit of the night: *"this is BS.. every push fails three times and takes 30 mins per push.. something has to change i cannot keep dealing with this.."*

## What was measured

The check that runs when a commit finishes a merge (`scripts/check_merge_resolution_tested.sh`) built its list of tests from every path that differed between the two tips. On a branch one day behind main that was 282 files, which named nearly every test in the house: 13,543 tests, 28 to 34 minutes, serial. The side that was actually mine had changed 17 files. And the same unrelated test refused two merges in a row.

## Two causes, found by looking, not guessed

1. **The set was the wrong subject.** Tips differ by everything either side did. What a merge can get wrong is measured from the merge BASE: my side's changes meeting main's new code. Main-only files are main's own run's job, and the whole suite is the push's job. The old comment called the wide set "wrong in the safe direction" and never priced it; priced, it is the unsafe direction, because a check nobody can afford is walked around.
2. **The list went to pytest in hash order.** An associative array hands its keys back unsorted. `test_log_level_config` reloads the ledger module (a new `Ledger` class), and `test_the_shared_ledger_object_is_a_real_ledger...` holds the class it imported at collection. Reload first, then that test: red. Proven in one second with two files in the two orders. It passes alone and in the suite's own alphabetical order, which is why it looked random.

## What changed

- The set is `git diff --name-only <merge-base> HEAD` (my side), mapped to tests by the draft push's own selector (`scripts/draft_test_selection.py`), so the house has one idea of which tests cover a change. The merged tree is passed to it as a tree id.
- If the base cannot be found, the selector is absent, or the selector says the change cannot be narrowed (conftest or project config changed), the check falls back to the OLD wide set and says so. A failure of the narrowing is wide, never narrow and never a silent pass. If the selector cannot read the repository the check refuses.
- The test list is sorted.
- The pass line now says it is NOT a whole-tree pass.
- The victim test asks the module as it is now, not the class imported at the top of the file.
- No retry-alone, no lone-pass pass-through. It was considered and dropped: a test that fails in a full run and passes alone is exactly what a leak from my own new code looks like, and a pass-through turns a flake into a normal green with no number on it.

## Measured on the real merge that failed twice

| | before | after |
|---|---|---|
| files in front of the check | 282 | 17 |
| test files run | about 430, 13,543 tests | 23, 351 tests |
| time | 28 to 34 minutes | 50 seconds |

Four of the five new tests fail against the old check (the fifth, a failing test on my side still refuses, passes on both, as it should: narrowing must not make the check unable to fail).

## What it cannot see, said so silence is not read as coverage

The selector reads text. A test that reaches a module without naming it is not found, and a file only main changed is not vouched for here. A break between my file and a main-only file that no test of mine names is met at the push, which runs the whole suite. That is the accepted cost, and it is now stated in the pass line instead of implied.

## Not built

The push's own whole-suite run is a separate timing. This change makes the commit stage cheap; whether the push stage also needs the same look is the next measurement, not a claim.

Walk: walk-de225b7a4b12 (nine lenses, all credited).
