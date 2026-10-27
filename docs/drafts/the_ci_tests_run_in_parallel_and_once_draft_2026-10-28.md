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

## Added the same day: the checks answer the merge queue

Dad, 2026-10-28, asked for the merge queue and, when it was put to him a second time, said yes to the review-check change below in so many words. The rule on main (`main protection`, ruleset 17092080) requires every pull request to be exactly up to date (`strict_required_status_checks_policy: true`). That is why each landing makes every other branch BEHIND and sends it back for a fresh 30 to 45 minute run: eight finished pieces were landing one an hour.

A merge queue keeps that safety (the combined result is tested) and removes the reset, but it asks for the same required checks on the combined result, and a check whose workflow does not listen for the queue's event never starts, so the queue would wait forever and nothing would merge. This change makes the three required checks answer:

- `tests.yml`: a `merge_group` trigger, and the test job runs on it. The full suite runs on the combined result.
- `integrity-audit.yml`: a `merge_group` trigger, and the required `multi-party-review` job runs on it but, on that event only, prints that the trailer was verified when the pull request entered the queue and skips its own range check (its checkout and verify steps are skipped on `merge_group`). The check is unchanged on `pull_request` and on `push` to main, so a piece still cannot be queued without it and main is still checked after it lands.

**The thing to read hardest.** This is the one place the review gate is not re-run on the combined result. The reasoning is that the trailer is bound to the pull request's own tree, which does not change when main is folded in; the push-to-main run catches a missing trailer after the fact. If that reasoning is wrong, the cost is a bad trailer noticed after merge instead of before it on that one path.

**Not in this change, and why it is separate.** The ruleset itself (adding the `merge_queue` rule) is turned on only after this change is on main. Turning it on first would freeze every merge. It is an API call, not a file, and it can be switched off the same way.

**Falsifier, counted in uses.** If a queued piece is held for more than two hours by a check that never reports, or lands without a trailer the pull-request run would have refused, the queue is switched off and this section is revisited.
