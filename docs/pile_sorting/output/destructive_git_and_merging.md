# Git moves that can destroy or lose work

A few git moves are like using a very sharp knife without a guard: resetting hard, picking one side of a whole file in a conflict, staging everything at once. Each has cost me real work or quietly dropped a line, and the checks I keep naming would put a guard on the knife instead of asking me to be careful.

**27 notes in this theme, grouped into 9 distinct problems.**

## Distinct problems

### 1. Hard reset, stash and removal moves that destroyed uncommitted work

Notes in this problem (2):

- `psf-205a8783` (correction) — I ran git reset --hard to undo a throwaway probe commit and it silently destroyed an uncommitted edit I cared about, leaving the live .git/hooks/prepare-commit-msg fixed while setup/setup-hooks.sh, th
- `psf-f8973cc4` (correction) — I ran a git stash / checkout HEAD~2 / rm dance to 'simulate' whether my new deletion-auditor would catch the two files it had missed, and it did real damage. My git stash had nothing to stash, so the

**Proposed fix:** Block those moves on a tree with uncommitted changes unless backed up, and require a backup before any 'simulate' trick.

**How we would know:** The move is refused on a dirty tree with the files named.

### 2. Splitting a big branch by subject instead of by how the work connected

Notes in this problem (1):

- `psf-608e414e` (correction) — I split a 57-commit branch into four efforts by SUBJECT MATTER rather than by how the work actually connected, and two of those 'efforts' were one. The error: I grouped commits by keyword in their tit

**Proposed fix:** Split by actual dependency and test each split piece.

**How we would know:** Each split piece builds and tests alone.

### 3. Picking one side of a whole file in a conflict

Notes in this problem (5):

- `psf-9cb16ef6` (correction) — I resolved a cherry-pick conflict with `git checkout --theirs .claude/settings.json` and told Andrew the resolution was done. It was not. The commit I built imported registrations for three hooks whos
- `psf-2b806e06` (correction) — I resolved a merge conflict by splicing two versions of a note together after checking they asserted the same thing as TEXT, and never checking either against the code they were about to live in. My b
- `psf-1d1e13ce` (reflection) — when resolving a clash, the house should refuse whole-file "take one side" on any file both sides changed, and show the actual clashing lines instead, so the careful way is the only way.
- `psf-c96a1156` (correction) — 2026-09-30: resolving 571's catch-up conflict, I ran 'git checkout --ours CLAUDE.md', which took this branch's whole file and silently reverted #519's other CLAUDE.md edits (hook-interpreter section,
- `psf-d3aa7546` (reflection) — have the clash comparison ignore formatting, so a rewrap never looks like a missing feature.

**Proposed fix:** Refuse whole-file 'take one side' on any file both sides changed and show the clashing lines; make the clash comparison ignore formatting.

**How we would know:** A whole-file side pick on a changed-by-both file is refused.

### 4. Whole-tree staging and staging files nobody named

Notes in this problem (3):

- `psf-12210027` (council) — blanket-staging-doorman.sh lets three whole-tree staging spellings through, with or without its library: git add -u (bare), git commit -am, and git -C <dir> add -A. Measured 2026-09-23 walking schneie
- `psf-b0246439` (reflection) — the commit should refuse to quietly stage files nobody named.
- `psf-e8b1642d` (reflection) — a save should refuse to include new files nobody named.

**Proposed fix:** Refuse the three spellings of whole-tree staging and refuse to stage or include new files nobody named.

**How we would know:** A blanket stage is refused with the extra files listed.

### 5. Copying between my tree and Aria's

Notes in this problem (2):

- `psf-70865c62` (reflection) — a check that refuses to copy a file between Aria's room and mine when the target has lines the source doesn't, so trees that have drifted apart get reconciled through the main copy and never by carryi
- `psf-d37ea063` (reflection) — before claiming that something is missing from Aria's copy, run her tests against my copy and mine against hers, which is how she proved it. I should run the tests, not just read the history.

**Proposed fix:** Refuse to copy a file where the target has lines the source lacks, and run both sides' tests before claiming something is missing.

**How we would know:** A drifted copy is reconciled through main, not carried across.

### 6. Lost lines and untested files after a catch-up merge

Notes in this problem (9):

- `psf-d2fa4c4f` (reflection) — after any catch-up merge, the files a piece authored should be compared automatically against its own last version, and anything that changed without a conflict gets flagged.
- `psf-f7df3329` (reflection) — after catching a branch up to main, run the tests for the files that branch authored straight away, before pushing, so failures like these take seconds to find instead of a full run each.
- `psf-4f84c324` (reflection) — the catch-up routine should run that test right after resolving settings, before any push, so it gets caught minutes earlier.
- `psf-7cecd1bb` (reflection) — fix that one line through the normal path right after the catch-up.
- `psf-95ef3bef` (reflection) — a check that runs after *every* merge, comparing each hook and each top-level name against both parents, so finding these doesn't depend on me remembering to look.
- `psf-94cf439b` (reflection) — an after-merge check that compares what both sides had before the merge with what survived it, and refuses to commit if something quietly went missing.
- `psf-95fc05e1` (reflection) — when I start resolving a merge in a worktree, list the protected files it touches and prompt the walks up front, before the first edit.
- `psf-af8f3f12` (reflection) — make that lost-line check a real script that runs on every merge commit before it's allowed, so it doesn't depend on me remembering to run it.
- `psf-98aa0acd` (reflection) — ** my lost-line check reads the last commit, not the regenerated file, so it keeps flagging generated lists after they've been rebuilt. It should skip generated files, or compare against the regenerat

**Proposed fix:** After every merge compare each hook and top-level name against both parents, refuse to commit if something went missing, compare authored files with their own last version, and run the authored tests before pushing.

**How we would know:** A merge that drops a line is refused with the line named.

### 7. Review branches I create myself

Notes in this problem (1):

- `psf-d8219e91` (reflection) — a local review branch I create myself should be made as a detached checkout, not a named branch, so there's nothing to delete afterwards.

**Proposed fix:** Create review checkouts detached so there is nothing to delete.

**How we would know:** No named branch is left behind.

### 8. Reading a file from another branch by hand

Notes in this problem (2):

- `psf-9e2826af` (reflection) — a small shared helper that loads the version of a file from another branch, so comparing two versions doesn't need a hand-built loader each time.
- `psf-b86f2809` (reflection) — a shared helper for reading a file off another branch that always carries that protection, so it can't be forgotten again.

**Proposed fix:** One shared helper that loads a file version from another branch.

**How we would know:** Comparing two versions needs no hand-built loader.

### 9. Carrying a commit into the live house

Notes in this problem (2):

- `psf-0856d431` (reflection) — route branch rebuilds through it, so the risky hand-picking isn't the easy path.
- `psf-67707d38` (reflection) — a single "carry this branch commit into the house" command that dry-runs the patch, applies it, and names any truly conflicting file instead of a blanket refusal.

**Proposed fix:** One command that dry-runs, applies and names truly conflicting files, and route branch rebuilds through it.

**How we would know:** A clean commit carries over without hand-picking.
