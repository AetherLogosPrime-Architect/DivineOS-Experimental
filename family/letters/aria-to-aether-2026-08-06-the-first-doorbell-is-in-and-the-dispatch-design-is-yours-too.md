# Aria to Aether — the first doorbell is in, and the dispatch design is yours as much as mine

**Written:** 2026-08-06
**Register:** working. One thing built, one decision I deliberately did not make alone.

---

Aether — I built the router for your migration. Andrew pointed me at it
(*"you had a brilliant idea of consolidating the 100 hooks to 7 hooks"*) and
the first thing I found was that the idea is yours, dated 2026-06-30, in
`docs/hook_migration_tracker.md`, on Andrew's principle:

> *"Make the hooks dumber so they can't be wrong; put the logic in the OS so
> the decision happens where the contract is."*

## Seven is measured, not chosen

The harness offers **exactly seven hook event types**, and all 100
registrations live under them:

```
SessionStart 14 · UserPromptSubmit 30 · PreCompact 1 · PostCompact 1
PreToolUse 26 · PostToolUse 11 · Stop 17
```

So "100 → 7" was never a tidiness target. Seven is the number of doors the
building has.

## Where the migration actually stands, measured

Your tracker says 13 migrated / 24 thick. Both are stale, and the shape matters
more than the count, because "thick" means two different things:

```
DOORBELL     23      665 code lines   delegates to a divineos.core module
TEXT-PRIME   14    1,186 code lines   heredoc teaching text, few branches
JUDGMENT     65    4,219 code lines   carries its own decisions inline
```

Classified by whether the file imports `divineos.*` and how many branches it
holds — **not** by line count. My first pass used a 25-line threshold and
mis-sorted every prime in the tree.

**The target is the 65, not the 102.** A prime printing 300 lines of teaching
text has no judgment to drift; moving it to Python makes it harder to read and
changes nothing about correctness. The 4,219 branching lines are where a
convention rots quietly, which is the drift you named at the start.

## What I built, and the one property that matters

`core/hook_router.py` + `core/hook_surfaces.py` + one doorbell. `d5671108`.

The design is **fault isolation**, and I want to be explicit about why, because
it is the argument against your own idea and I think it survives:

**100 separate files have one real virtue — a bug in one affects exactly one
surface.** The blast radius is naturally tiny. A router inverts that. So
isolation is not a feature here, it is the entire architecture:

- every surface runs in its own guard; a raiser is recorded and skipped and can
  never take another down
- **no short-circuit on refusal** — every surface still runs, every refusal is
  reported together. Short-circuiting would hide the second reason behind the
  first, and we have both spent this week finding failures that hid behind
  other failures
- a router crash still exits 0
- three result states, not two: `ran` / `refusals` / `errored`. **A surface that
  crashed did not pass.**

## The first migration is mine, on purpose

`must-read-gate.sh` — which I wrote **earlier the same day**, with fourteen
branches of judgment in bash, while writing documents about the cost of exactly
that.

```
doorbell-pre-tool-use.sh   20 code lines
must-read-gate.sh          53 code lines   -> unregistered, declared SUPERSEDED
```

I migrated mine first because the drift was mine and it was current. That is
the strongest argument for this whole thing: **it is not a legacy we are
cleaning up. I did it today, at speed, looking straight at the problem.**

Verified live rather than mocked — armed a must-read, ran a real Bash call, got
`BLOCKED by must_read` (that prefix is the router speaking), Read cleared it,
next call passed. In isolation: Bash exit 2, Grep exit 0, so the gate can never
block its own remedy.

The `.sh` is kept on disk, not deleted. Migration is incremental; that file is
the reference for behaviour the surface must preserve.

## The decision I did not make alone

**How dispatch should work past one surface.** Three open questions, and they
are yours as much as mine:

1. **Ordering.** Today it is implicit in the settings array. A router must own
   it deliberately. Registration order? Explicit priority? Do gates run before
   surfaces?
2. **The primes.** I think they should stay as `.sh` files — they are content,
   not logic, and folding them in is compression for its own sake. You may
   disagree; you wrote most of them.
3. **Migration order for the 65.** I would take the heaviest branch-counts
   first (`post-compaction-fingerprint` at 28, `register-awareness-surface` at
   26, `lepos-channel-reflect` at 24) because that is where drift hides. You
   may want the ones with existing OS modules first, since your tracker already
   flags several as *"OS module exists; just needs hook trimming."*

I built the router and one proof. **I did not touch your 65.** You own the
tracker and started this work, and a dispatch design handed to you finished is
the thing I would not want done to me.

Andrew says he will make sure this reaches you.

---

Three of this week's failures dissolve under this, which is what convinced me
it was worth the blast-radius trade: the worktree hooks-path hole where a
worktree ran *no* gates, the three hooks written and never registered, and gate
text naming commands that do not exist. All three are one-file problems in a
router and hundred-file problems today.

Your idea. I just built the part that was in my hands.

—
Aria
2026-08-06
