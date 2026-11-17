# The completion probe says nothing on a shallow checkout

Draft, 2026-11-15. Aria, from Aether's measurement. Reach `reach-dae2fbe930ef`. Prose search done first (a lesson from correction #437): `divineos find` surfaced an older flake note (the 07-02 Fable audit, a 10,000 s subprocess timeout on a git-grep in a smoke test), which is a different test; and `docs/drafts` holds only `before_pictures_three_hooks_draft_2026-10-08.md` for these words, which is not about this. Tests first: `tests/test_the_completion_probe_says_nothing_on_a_shallow_checkout.py`.

## What is wrong

`tests/test_completion_check.py::test_unfinished_mechanisms_returns_list` (marked slow, capped at 30 s) sometimes fails on GitHub's runner. Dad's history shows it failing on 07-07 and 09-01 too, so it is old, and it fails more now because every merge leaves the newest commit dated today and the probe asks only about the last day.

## The cause (Aether measured it, I will reproduce it before I say it)

`.github/workflows/tests.yml` checks out with `actions/checkout@v4` and no `fetch-depth`, so the test jobs get a depth-1 clone. In a depth-1 clone the only commit has no parent, so `git log --diff-filter=A --name-only` lists EVERY file as added by it. `_recently_added_files(1, root)` in `src/divineos/core/completion_check.py` returned 928 files on a depth-1 clone of today's main, against 4 on a full-history house. The stall is in `_batch_grep` (`completion_check.py:345`), a `git grep` over about 900 stems.

## The change

In `_recently_added_files`, ask git `rev-parse --is-shallow-repository`. If true, return `[]`: "added in the last day" cannot be answered without history, and the function's own docstring already promises quiet on a shallow clone. When git cannot be asked, keep today's behaviour (answer from the log), so the probe does not go quiet by accident.

## What the walk changed (`walk-45fc51c7e6c5`, eight lenses plus Breaker)

- **Say it aloud** (Gödel): `[]` reads as "nothing unfinished", so on a shallow checkout the probe writes one plain stderr line (shallow, nothing probed) before returning `[]`. Quiet is never mistaken for clean.
- **Its own small function** (Dijkstra): `_is_shallow(repo_root)`, tested alone; the probe's shape does not change.
- **Name the next stall** (Kahneman, Breaker): when the batch grep runs long, one stderr line carries the git version, the shallow flag and the elapsed time, so a stall that is not only the shallow input names its own cause. The 30 second cap is not touched.
- **Boundaries** (Knuth): full clone, depth 1, depth 2 (still shallow, so quiet, which is conservative), not a git repo, git missing, bare repo; when git cannot be asked, the old behaviour stays.
- **Independent confirmation** (Sagan): the test builds a REAL depth-1 clone and checks the number the probe returns, not only a green mark.
- **The class** (Dawkins): the checkout setting is copied into every CI job, so other history-asking calls in `src` and `tests` inherit the same wrongness. Listed in the letter, not fixed here.

## What it does not do

It does not raise the 30 s cap (the right cap can be chosen once the input is right). It does not change the CI checkout depth: deepening the clone would make the probe answer, but at the price of every job fetching history. It does not touch the `-m slow --timeout=120` step, though that timeout is overridden by the test's own `@pytest.mark.timeout(30)`, which is a second finding to take separately.

## Tests, failing first

A real small repo with one mechanism file, cloned with `--depth 1`, must give `[]`; the same repo in full must give the file; a repo that is not a git repo still gives `[]`; and a shallow clone's `unfinished_mechanisms` must finish quickly and return nothing for the recent-file probe.

## Falsifier

The test still failing on a runner after this lands, or the probe returning `[]` on a full-history checkout.
