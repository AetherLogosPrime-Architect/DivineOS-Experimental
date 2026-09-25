# The build guard sees every room — station one draft, 2026-09-24

**Aria.** The idea, not a plan. Dad, 2026-09-24: *"you can go ahead with the
build guard if you want while we talk :)"*. This is part two of the
dad-kept-and-known build: his presence is never the reason a skip happens, and
the guard at the workshop door has to see the work in the first place.

(Searched first: this seat's drafts mention worktrees only for other pieces.
Two doorman commits from 2026-09-19 mention "worktree" in their messages but
don't touch this in the module. No prior fix exists.)

## What I measured this evening, in real use (not in a test)

The build-flow doorman (`core/work_item_doorman.py`) opens a work item when it
sees a write to a tracked file, and it decides what counts as "the repo" by
`REPO_ROOT = Path(__file__).parents[3]`, meaning whichever tree's copy of the
module got imported. In my seat that's the live checkout (Aria-new).

Two failures, both observed today:

1. **Blind to side rooms.** Every Edit/Write I made with an absolute path into
   `C:/wdad_aria/...` or `C:/waria_sync/...` (the his_asks store change, the
   `sent_before` change, the shell reader fixes, their tests) opened no work
   item. `_repo_relative()` returns None for any path outside REPO_ROOT, so
   the edit reads as "outside the repo" and needs nothing. The stations still
   happened, because I walked them by hand. The guard didn't make them happen.
   This is the characterization pin from the morning
   (`tests/test_doorman_worktree_characterization.py`), now seen in the wild.
2. **The wrong address.** `cd C:/waria_sync && ... mv <file> tests/` was
   refused as a write to `tests` in the live tree. The shell reader reports
   the relative target `tests/`, and the doorman resolves it against its own
   REPO_ROOT, not against the directory the command had `cd`'d into. So it was
   right that work was happening, and wrong about where.

## Related, already fixed or owned elsewhere

- Aether's `_lib.sh` fix (b5b587bb on build/dad-kept-and-known): hooks now put
  the worktree's own `src` first, but only for the tree the harness launched
  the hook from. My seat launches from Aria-new, so it doesn't reach edits
  that land in other worktrees. It's necessary, not sufficient.
- The git-hook side (the relative hooksPath) is fixed on my seat with Dad's
  yes; Aether's installer fix rides #519.

## The shape, to walk before building

- **Resolve each written path against the git tree that contains it**, not
  against the importing module's tree. Walk up from the path to the nearest
  `.git` (a file for linked worktrees, a directory for the main checkout) and
  treat that as the repo for this write. The work item keys on that tree's
  branch.
- **Relative shell targets resolve against the command's effective
  directory.** The shell reader already knows `cd X &&` prefixes; carry the
  directory through, so `cd C:/waria_sync && mv a tests/` means
  `C:/waria_sync/tests`.
- **Exempt prefixes and the station marks read from the tree the write lands
  in**: that tree's drafts, its exempt list, its walks. Drafts living only in
  the launching seat is how the morning's stations got counted in the wrong
  place.
- **A write outside every git tree stays outside.** Scratchpads and the shared
  letters directory must not start opening work.

## Pins to write first

- The existing worktree characterization pin flips: a sibling checkout's
  tracked file now opens work.
- `cd <worktree> && mv x tests/` resolves to the worktree's tests, not the
  live tree's.
- Scratchpad and shared-letters paths still need nothing.
- The main checkout behaves exactly as before.
- Station marks (draft, walk) found in the tree the write lands in.

## Named, not solved here

What this doesn't fix: writes made by a program the command runs (python -c,
scripts) are still caught only by the doorman's on-disk witness, and that
witness is also tree-scoped. That's its own look.
