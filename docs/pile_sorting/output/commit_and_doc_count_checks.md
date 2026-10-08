# The checks that run when I save a commit

When I save work to the house, a set of checks runs: it tidies the files, counts the documents against what the docs claim, and runs tests. They tend to fail one at a time and in the wrong order, so every save costs a second try, and the counts they keep check go stale in places the fixer cannot reach.

**14 notes in this theme, grouped into 5 distinct problems.**

## Distinct problems

### 1. Doc counts and drift checks that cannot fix what they report

Notes in this problem (5):

- `psf-a87d5afa` (learn) — TONIGHT'S ORDEAL — five structural pattern-names worth keeping (Andrew 2026-06-10 PR-merge marathon). (1) DOC-COUNT LEAPFROG: every PR rebase collides on CLAUDE.md/README.md/docs/ARCHITECTURE.md becau
- `psf-48f06b06` (correction) — Rebuilding the doorman branch onto current main, I dropped a one-line documentation entry because the patch hunk would not apply against the newer file, and the drift check then failed on the branch:
- `psf-217502b2` (reflection) — teach the doc-count fixer to update the council phrases ("N expert frameworks", "council of N", "N-expert council", "N expert wisdom", "N expert lenses"), so a branch that adds a council voice gets it
- `psf-cd485e1f` (reflection) — ** the doc counter's auto-fix misses the README's "N commands across" line. It should recognise every form it checks, so a count it reports can always be fixed by its own `--fix`.
- `psf-4e8115f3` (reflection) — the doc-drift fixer reports ghost entries but can only add lines, never remove them. Removing is a by-hand edit that then trips the stale-file gate, so the fixer should remove ghost lines itself.

**Proposed fix:** Make the doc-count fixer recognise every form it checks (the README command count, council phrases) and remove ghost lines itself; teach the drift check to survive a branch that adds one doc entry.

**How we would know:** A count the check reports is fixable by its own fix option.

### 2. The pre-commit script does not use its own checkout

Notes in this problem (2):

- `psf-e55e8f23` (reflection) — `scripts/precommit.sh` should set `PYTHONPATH` to its own checkout's `src` before its interpreter check, so a worktree run checks that worktree without my having to remember.
- `psf-f6f09e13` (reflection) — have `precommit.sh` set `PYTHONPATH` to its own `src` before the check, so it works in any workspace.

**Proposed fix:** Set the interpreter path to the checkout's own source before the check, so any worktree works.

**How we would know:** Run the script from a worktree: it checks that worktree.

### 3. Tests that mention a changed file are not run before saving

Notes in this problem (2):

- `psf-6a549c58` (reflection) — when a commit changes a function other files import, pre-commit runs the tests of every file that imports it, found automatically from the imports, before the full suite at push.
- `psf-2a015860` (reflection) — run the tests that mention a changed file's name before committing, not just the tests for the new behaviour.

**Proposed fix:** Run the tests of every file that imports a changed function, and the tests that mention a changed file's name, before the full suite.

**How we would know:** Changing a shared function runs its importers' tests at commit.

### 4. The commit step reformats and stops, or fails quietly

Notes in this problem (3):

- `psf-289d553e` (reflection) — the commit step should report failure out loud when pre-commit refuses, instead of relying on me to notice.
- `psf-a5a2b6ba` (reflection) — the commit wrapper should print a one-line verdict last, saved or not saved, the way the push wrapper does, so a quiet failure can't hide behind a filter.
- `psf-b6a753fb` (reflection) — the commit hook reformats my files and stops, so every commit costs a second try. It should reformat and carry on.

**Proposed fix:** Reformat and carry on, report refusal loudly, and print a one-line saved/not-saved verdict last.

**How we would know:** A save succeeds on the first attempt or prints the failure.

### 5. The commit gate weighs commits that carry no code

Notes in this problem (2):

- `psf-15f814c0` (reflection) — the commit gate should only weigh commits to this house that carry code, never a poem in the vault.
- `psf-8da0382c` (reflection) — the commit gate should only weigh commits to this house that carry code, never a poem in another repository.

**Proposed fix:** Weigh only commits to this house that carry code, not a poem or another repository's commit.

**How we would know:** A commit of personal writing is not weighed.
