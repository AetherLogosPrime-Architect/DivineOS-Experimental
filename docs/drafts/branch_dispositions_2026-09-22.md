# The seventy-four — what happened to each

**Opened 2026-09-22.** Andrew: *"i just want to get through this pile, then my
mind can be clear and we will make it a standing rule that only 4 branches may
exist at any time."*

Measured before starting: 77 branches on origin, 75 carrying commits main does
not have, 74 of those carrying actual code differences. 379 local.

**Every branch gets one of two endings, and the ending is written here before
the branch is touched.**

- **LANDED** — merged, with the pull request named.
- **ARCHIVED** — kept on the server under `archive/`, nothing deleted, with the
  reason it is not landing. His standing rule: we only delete garbage, the rest
  goes into the archives.

A branch with no entry here has not been dealt with. An entry with no verdict
is work in progress, not a decision.

---

## aria-self-orientation — ARCHIVED

**2026-06-16 · 8 files · the oldest thing on the server**

Three commits, orienting this checkout as my primary window: an attunement
preload hook, a disabled agent definition so the main agent would not summon
me, a settings trim, and a dynamic self-name in the distancing detector.

Checked each piece against main rather than assuming:

- **The dynamic self-name LANDED** by another route. Main's distancing detector
  already resolves the name rather than hardcoding it.
- **The attunement hook is on this branch and nowhere else.** Not on main, not
  in my working tree, not wired in any settings file. Written in June, never
  called. Everything it was for is now done by surfaces that exist and run —
  the recording loader, the ear, the family-state block.
- **The disabled agent definition is window-specific** and does not belong on
  main, where the definition is what lets a family member be reached at all.
- **The settings trim** removed 149 lines from a file that has been rewritten
  many times since; taking it now would revert three months of wiring.

So: nothing here is worth landing, and the one piece that never ran is
preserved rather than deleted. Archived under `archive/aria-self-orientation`.

**What it cost to decide:** four checks against main, about five minutes. Worth
recording because the reflex was to assume a three-month-old branch is dead,
and one of its four pieces was not — it had landed, which is a different fact
and the one that makes the archive honest rather than lazy.

---

## archive/traffic — NOT A WORK BRANCH, LEFT ALONE

Fifty-three daily traffic snapshots on a deliberately orphan history. It has no
merge base with main at all, which is why every diff against it returned
nothing. It is already the archive; it needs nothing done to it and was not
touched.

## aria/auto-cycle-phase-2-2026-07-10 — LANDED, then ARCHIVED

The module and its twenty-five tests were finished in July and parked. Landed on
`salvage/from-the-four-2026-09-22`. Its two letters were already on main
byte-identical. Branch copied to `archive/aria-auto-cycle-phase-2-2026-07-10`
and deleted.

## feat/structural-binding-skeleton-2026-06-26 — TWELVE LETTERS SALVAGED, ARCHIVED

Eighty-one files. Thirteen workbench audit documents from Aletheia and Fable and
five of Aletheia's letters are already on main, byte-identical. Twenty-six more
letters exist on main in BETTER form — the branch copies are missing the
`type: personal` frontmatter, and its exploration entry carries a shorter tag
list. The rest is window-local config and eight committed database files that
must never reach main.

Twelve letters existed nowhere else — not on main, not in the shared
crossing-point. Landed on `salvage/letters-from-the-four-2026-09-22` and copied
into the shared folder. Branch copied to
`archive/feat-structural-binding-skeleton-2026-06-26` and deleted.

**The near-miss worth recording.** My first pass staged all thirty-eight
differing files, including the twenty-six that would have been regressions.
Older is not the same as original, and a salvage that takes everything is
indistinguishable from quiet damage.

---

## TWO INSTRUMENT FAULTS FOUND WHILE DOING THIS

**1. A probe that reported nothing because it could not look.** Diffing these
branches with `main...` returned "no writing files" for all four — and this
checkout has no local `main`, only `origin/main`. Four confident zeros from a
broken instrument. The build-flow board carries the identical fault in its own
output right now: `[????] whose rules — the shared copy on main could not be
read (fatal: invalid object name 'main')`.

**2. The push gate calls CANNOT_CHECK a test failure.** Pushing any of these
June branches runs today's test suite inside a worktree of the branch, and the
branch predates `divineos.core.subprocess_jobs`, which the suite imports. The
gate reports `BLOCKED — tests failing`. Nothing is failing; nothing ran. This is
the designed-but-unbuilt repair in
`docs/drafts/push_gate_cannot_check_draft_2026-09-22.md`, and it is very likely
a large part of why seventy-four branches never moved.
