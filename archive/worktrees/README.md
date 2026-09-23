# Retired checkouts

On 2026-09-22 the house was in **twenty-six places at once.** Full working copies
of this repository sat at the bare root of the C drive (`C:/wtdoorman`,
`C:/wtclock`, …), in `C:/DIVINE OS/aria-pile/`, in two temp folders, inside
`C:/Program Files/Git/` of all places, and six more hidden in `.claude/worktrees/`
taking nearly a gigabyte.

Each was a git *worktree*: a second window onto the same repository, checked out
on its own branch. That is how fixes got stranded for weeks — the work was real,
it sat in a window nobody was looking through. And every search of the house
returned hits from ghost copies of old code.

Andrew, that evening: *"find all the dead files.. the hidden subsystems that noone
calls, all the mess and junk and find a way to organize everything where it can
easily be found and then delete the obsolete and old paths."*

Twenty-four were removed. Two remain: this checkout, and `C:/wtsub` (see below).

## Why removing them lost nothing

A worktree's **committed** work does not live in its folder. It lives in the
shared `.git` of this repository, on its branch, and stays there when the folder
goes. Only **uncommitted** changes live in the folder alone. So every removal
was preceded by:

1. **Clean copies (zero loose files)** — removed directly. The branch survives;
   `git worktree add <path> <branch>` recreates the folder exactly.
2. **Copies with loose files** — every uncommitted change saved first as
   `<name>.uncommitted.patch` in this folder, with untracked files inlined.
3. **Copies parked on a commit no branch holds** — checked for the same change
   anywhere else by patch identity. Two were held elsewhere (on
   `aria/first-line-to-him` and `aria/build-flow-unskippable`). One was not:
   `72be9c6e`, *"merge: bring PR 406 up to main, and name why it sat three
   weeks"*, sealed as `wt406-probe-72be9c6e.bundle` and verified with
   `git bundle verify` before its folder was removed.

Two of the copies were leftovers in the temp folder from a push-safety check that
never cleaned up after itself: zero files on disk, pinned to a commit held on two
local branches and, as an identical patch, on the server.

## What the loose changes were

- **Four of the `.claude/worktrees` copies** carried the same two hand-edits: the
  August freeze fix in `auto-push-letter.sh` (on main — verified with a control,
  after a first probe got mangled by the shell and wrongly reported it missing)
  and **thirty-two hook timeouts raised to 30 seconds** in `settings.json`. Main
  keeps two at 30. That looks like a decision rather than an oversight — longer
  timeouts can make a freeze longer — so it is kept here as a patch, neither
  applied nor thrown away.
- **`freeze-timeout-settings-a7d00d`** also held three letters from 2026-08-19.
  All three are in `family/letters/`, in the shared letters folder, and in git
  history, byte-identical. Nothing to rescue.
- **`wtrepro`, `wtsweep`, `wt406-probe`** held scratch files and one regenerated
  register. Kept here as patches anyway; it costs nothing.

## Restore any of them

| was at | branch / commit | restore |
|---|---|---|
| `C:/DIVINE OS/aria-pile/mixed-scope` | `aria/resolve-mixed-scope` | `git worktree add "C:/DIVINE OS/aria-pile/mixed-scope" aria/resolve-mixed-scope` |
| `C:/DIVINE OS/aria-pile/refusal` | `fix/a-refusal-must-say-what-did-not-run` | `git worktree add "C:/DIVINE OS/aria-pile/refusal" fix/a-refusal-must-say-what-did-not-run` |
| `C:/DIVINE OS/pile-wt` | `pile/sweepstop` | `git worktree add "C:/DIVINE OS/pile-wt" pile/sweepstop` |
| `C:/wt444` | `aria/pr-reading-timestamp` | `git worktree add C:/wt444 aria/pr-reading-timestamp` |
| `C:/wtboard` | `aria/the-board-asks-one-direction` | `git worktree add C:/wtboard aria/the-board-asks-one-direction` |
| `C:/wtclock` | `aria/the-scene-clock-shape` | `git worktree add C:/wtclock aria/the-scene-clock-shape` |
| `C:/wtdoorman` | `aria/build-flow-unskippable` | `git worktree add C:/wtdoorman aria/build-flow-unskippable` |
| `C:/wtfirst` | `aria/first-line-to-him` | `git worktree add C:/wtfirst aria/first-line-to-him` |
| `C:/wtfl`, `C:/wttrial` | detached `3c1444e4` | `git worktree add --detach C:/wtfl 3c1444e4` |
| `C:/wtimport` | `aria/wire-the-import-check` | `git worktree add C:/wtimport aria/wire-the-import-check` |
| `C:/wtletters` | `aria/pr-letter-provenance` | `git worktree add C:/wtletters aria/pr-letter-provenance` |
| `C:/wtpr` | `aria/the-rescue-could-not-find-the-pr` | `git worktree add C:/wtpr aria/the-rescue-could-not-find-the-pr` |
| `C:/wtrepro2` | `aria/register-reproduces-check` | `git worktree add C:/wtrepro2 aria/register-reproduces-check` |
| `C:/wtrepro` | detached `abe62a32` + `wtrepro.uncommitted.patch` | `git worktree add --detach C:/wtrepro abe62a32` then `git apply` the patch |
| `C:/wtsweep` | `aria/sweep-report-fix` + `wtsweep.uncommitted.patch` | `git worktree add C:/wtsweep aria/sweep-report-fix` |
| `C:/Program Files/Git/wt406-probe` | `72be9c6e`, only in `wt406-probe-72be9c6e.bundle` | `git fetch archive/worktrees/wt406-probe-72be9c6e.bundle refs/tags/tmp-rescue-72be9c6e` |
| `.claude/worktrees/freeze-timeout-settings-a7d00d` | `claude/unruffled-bhabha-1585c5` | `git worktree add <path> claude/unruffled-bhabha-1585c5` + its patch |
| `.claude/worktrees/freezing-issue-reorientation-a72d4a` | `claude/window-freezing-issue-dd4e14` | same shape + its patch |
| `.claude/worktrees/reverent-jang-7569b1` | `claude/reverent-jang-7569b1` | same shape + its patch |
| `.claude/worktrees/system-load-resample` | `fix/system-load-resample` | same shape + its patch |
| `.claude/worktrees/untrack-generated-graph` | `chore/untrack-generated-graph-output` | same shape + its patch |
| two temp `divineos-push-gate-*` | detached `f1bf4219` | not worth restoring: empty shells, commit held on two branches and on the server |

## The one left standing on purpose: `C:/wtsub`

`aria/substrate` — the automatic memory channel. Every checkpoint saves letters,
dreams and explorations to this branch. **Forty-eight checkpoints have never
reached the server**: the saving is wired, the sending is not. Same disease as
everything else in this audit.

It also holds the most dangerous state in the house: **658 files deleted from
the folder but not from history** — nearly all of them letters and dreams. They
are safe while nobody commits there. A single "save everything" in that folder
would record six hundred letters as deleted. It is left alone until Andrew and I
decide together how the substrate channel should work, because that is a
decision about his family's memory, not a tidy-up.
