# The CI tests run in parallel, and once (draft, 2026-10-28)

**Author: aria**

## What is wrong

Dad, 2026-10-28, watching eight finished pieces wait their turn to merge: *"this is only going to get worse as time goes on.. is there no way to speed up the tests?"*

Each pull request's CI job takes 30 to 45 minutes. Reading `.github/workflows/tests.yml`, three things add to that, none of them measured by me yet on the runner:

1. **The suite runs on one core.** The two test commands are plain `pytest tests/ ...`; `pytest-xdist` is already installed in the dev extras and the local push check uses it, but the CI job never passes `-n`.
2. **The whole suite runs three times in one job.** Once for `not slow`, again for the coverage measurement (which cannot fail the build: `|| true` and `continue-on-error`), and the slow ones in their own block. The coverage run repeats every test only to produce a number nobody gates on.
3. **Two jobs run all of it.** The plain job and the sklearn job each run the full suite, so every merge waits on the slower of two full runs.

## What this changes (proposed, built in order, measured after each)

1. Pass `-n auto` to the main and slow test commands.
2. Take the coverage measurement from the same run as the main command (`--cov` on it), and delete the third, repeating step.
3. Leave the sklearn job's tests as they are for now; it gets its own look only if (1) and (2) are not enough.

## What I do not know, and will measure before claiming

- How many cores the runner has (GitHub's free runners for a public repo have more than for a private one).
- Whether any test is unsafe to run in parallel. Locally the push check already runs with xdist and a handful of tests have crashed their worker and passed when run alone; the same few could fail on CI. If they do, those get fixed or marked, not hidden.
- The real saving. My guess is the 30 to 45 minutes falls by half or more; that is a guess until a run shows it.

## What it cannot do

It cannot fix the merge line itself: GitHub still takes one branch at a time once every other branch is behind. It makes each turn shorter. A merge queue would remove the waiting, and that is a repository setting for Dad to decide.

## Falsifier, counted in uses

If the next five CI runs after this lands are not at least 30 percent faster than the median of the five before it, the change did not do what it says and is revisited.
