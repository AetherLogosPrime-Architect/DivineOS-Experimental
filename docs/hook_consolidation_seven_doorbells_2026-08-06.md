# Seven doorbells — measured state of the hook layer

**Written:** 2026-08-06 (Aria), at Andrew's direction — *"you had a brilliant
idea of consolidating the 100 hooks to 7 hooks and routing the logic into the
OS itself :) see what you find"*

Continues [`hook_migration_tracker.md`](hook_migration_tracker.md), started
2026-06-30 by Aether on Andrew's principle:

> *"Make the hooks dumber so they can't be wrong; put the logic in the OS so
> the decision happens where the contract is. Replace the decision with
> structure so it makes the choice for you."*

Everything below is measured this session, not recalled.

---

## Why seven, and it is not a round number

The harness offers **exactly seven hook event types**, and every registration
lives under one of them:

```
SessionStart        14 registered
UserPromptSubmit    30
PreCompact           1
PostCompact          1
PreToolUse          26
PostToolUse         11
Stop                17
                   ---
                   100
```

So "100 hooks → 7" is not a compression target chosen for tidiness. **Seven is
the number of doors the building actually has.** One doorbell per door, and the
OS decides who is behind it.

## Measured state of the 102 hook files

The tracker lists 13 migrated and 24 still thick. Both numbers are stale, and
the shape turns out to matter more than the count, because "thick" means two
different things:

```
DOORBELL     23      665 code lines   delegates to a divineos.core module
TEXT-PRIME   14    1,186 code lines   mostly heredoc teaching text, few branches
JUDGMENT     65    4,219 code lines   carries its own decisions inline
```

Classified by whether the file imports from `divineos.*` and how many
control-flow branches it holds — not by line count. My first pass used a
25-line threshold and mis-sorted every prime in the tree.

**The migration target is the 65, not the 102.** A prime that prints three
hundred lines of teaching text holds almost no judgment to drift; moving that
text into Python would make it harder to read and change nothing about
correctness. The 4,219 lines of *branching* are where a convention rots
quietly, and that is the drift Aether named at the start.

Heaviest judgment-carriers:

```
28 branches  post-compaction-fingerprint-surface.sh
26 branches  register-awareness-surface.sh
24 branches  lepos-channel-reflect.sh
21 branches  family-state-surface.sh
16 branches  keyword-enforcement-doorman.sh
14 branches  must-read-gate.sh          <- I wrote this one TODAY
```

## The entry I did not enjoy finding

`must-read-gate.sh` is mine, from this session, and it lands in the judgment
column with fourteen branches. I built a thick hook **on the same day** I have
been cataloguing the cost of logic living outside the OS, against a design
document that has existed since June and that I did not read first.

Not a disaster — it works, it is tested through `core/must_read.py`, and most
of the branching is tool-name dispatch. But *which tools count as substantive*
is a judgment, and it sits in bash where no unit test can reach it. It belongs
in the module the doorbell already calls.

That is the argument for consolidation stated better than I could state it
abstractly: **the drift is not historical. It happened today, by me, while I
was looking directly at the problem.**

## What the consolidation actually buys

Three of this session's failures disappear under it:

* **The worktree hook-path hole.** `core.hooksPath` was relative, so a worktree
  ran no hooks at all — no gates, no emitter. With seven doorbells the failure
  surface is seven files and one testable resolution helper.
* **Hooks written and never registered.** Three sat dark in both trees since
  2026-07-28. With one doorbell per event, "registered" stops being a per-file
  act that can be forgotten; the OS-side router owns the roster.
* **The prescribed-remedy defect.** Gate text naming commands that do not
  exist. In Python that is one AST test from unshippable; across ninety-nine
  bash files it is a grep and a hope.

## What it costs, stated rather than skipped

* **The router becomes load-bearing.** A bug there breaks every surface for
  that event, where today a bug is usually confined to one file. Worth it only
  because a router is testable and ninety-nine bash files are not.
* **Ordering becomes explicit.** Today it is implicit in the settings array. A
  router must own it deliberately — more honest, more work.
* **The primes should stay as files.** They are content, not logic. Folding
  them in would be compression for its own sake.

## Not proposed here

The migration itself. This is the measured ground for it — the count, the
three-way split, the seven doors, the honest cost. Aether owns the tracker and
started the work; how the router dispatches is a decision we should make
together rather than one I hand him finished.

## A second gap, found while measuring

Andrew: *"you should have something that helps keep track of all of this."*

There is no code-scale metric anywhere. `divineos body` reports substrate
vitals — database sizes, table health, storage growth — and zero lines about
the codebase. `divineos progress` tracks sessions and knowledge, not size.

Measured by hand this session:

```
Python        379,548 lines   1,424 files   (src 209,953 / tests 142,047 / scripts 13,919)
Shell          14,629 lines     117 files
Markdown      202,593 lines   2,460 files
Tracked         4,844 files
Commits         1,716          since 2026-03-15 (144 days)
Tests          10,358
Commands          430
Hooks             100 registered across 7 event types
```

I called this a dinghy roughly an hour before measuring it. The numbers were
printing in `check_doc_counts` output all session and I read them as a
pass/fail state rather than as a description of the thing I live in.
