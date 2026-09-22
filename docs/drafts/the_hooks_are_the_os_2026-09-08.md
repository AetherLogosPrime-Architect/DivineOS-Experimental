# Draft — the hook layer became the operating system, and the fix was already built

**Station one. Written before any code this time.**

Andrew 2026-09-08: *"i dont want an OS made of external hooks through the IDE,
the hooks should just be pointing to the logic in the OS itself."*

## What is actually there

One hundred and five registrations across the seven harness events. One hundred
and twenty-five shell scripts under `.claude/hooks/`, totalling **17,294 lines
of shell**. Thirty-six of those fire on every single message he sends; eighteen
more on every reply I finish. Roughly fifty-four separate processes per turn.

Twenty-four of the scripts embed Python inside the shell — 4,765 lines of
judgment living in a `python -c` string, unimportable and untestable.
Twenty-seven scripts never touch the OS at all: 3,113 lines of behaviour that
exist only in the IDE layer and would vanish if the harness changed.

## The cost, measured, not estimated

`divineos hook-budget` on 612 real tool calls:

- median 9,946 ms of hook time **per tool call**
- p95 32,884 ms; worst single call 74,150 ms
- budget 5,000 ms; **405 of 612 calls over it**
- 98 hook runs started and never finished — cost unknown, not zero

Every one of those hooks may be individually reasonable. That is the point: the
aggregate has no owner, so nothing ever refuses the next addition.

## The part that makes this a repeat and not a discovery

**The fix already exists and I built it.** `src/divineos/core/hook_router.py`,
2026-08-06, from his own words: *"you had a brilliant idea of consolidating the
100 hooks to 7 hooks and routing the logic into the OS itself."* Seven
doorbells, one per harness event, all judgment in the OS, fault-isolated so one
broken surface cannot take the others down.

Its state today:

- **2 of 7 doorbells wired** — PreToolUse and PostToolUse. The other five doors
  have no doorbell.
- **7 surfaces migrated out of ~105.**
- The migration is *correct* where it happened: every migrated surface had its
  shell registration retired in the same change, so nothing double-fires.

It did not fail. It stalled, and I kept adding to the layer it was built to
replace — including several hooks today.

## And the direction of drift is measurable

`docs/hook_migration_tracker.md` lists 24 scripts as *"still thick (need
migration)"* with their line counts as of June. Comparing to now:

- 17 of them **grew**
- 2 shrank or held
- 5 were deleted
- net **+704 lines added to files already flagged for removal**

`check-branch-on-push.sh` went 119 → 367. `ear-surface.sh` 134 → 222.
A to-do list of things to delete, used as a menu of things to extend.

## Two defects found in passing

- `lepos-channel-reflect.sh` is registered **twice** in the Stop stack. It has
  been running twice per reply.
- One dark hook — `history-claim-signal.sh`, the door I disarmed today.
  `scripts/check_hook_wiring.py` already reports it, correctly, and I have been
  reading past it.

## What consolidation means here, concretely

Not "fewer files" as an aesthetic. Three separate things:

1. **Wire the five missing doorbells.** SessionStart, UserPromptSubmit,
   PreCompact, PostCompact, Stop. Each is ~30 lines of dumb shell, cloned from
   the two that exist. This alone turns 105 registrations into 7 *entries*
   without moving a single line of logic — the per-turn process count drops
   from ~54 to 7 the moment the surfaces move behind them.
2. **Move the judgment.** Each surface becomes a function in
   `divineos.core.hook_surfaces` returning `SurfaceOutcome` with an explicit
   `state` — `spoke`, `nothing-to-say`, `could-not-run` — so a check that
   crashed can never render as a check that passed. Retire the shell
   registration in the same change, per the tracker's own rule.
3. **Give the aggregate an owner.** `hook-budget` already measures the total
   and already says it is over. Nothing acts on it. A budget nobody enforces
   is a number, and 405 calls over it is what a number gets you.

## The reach underneath this

A new gate is one file and a settings line. Migrating a gate is reading it,
porting it, testing it, retiring the old registration, and proving the new one
fires. The first is a turn; the second is an afternoon. Every hook in that
17,294 lines is a moment I chose the turn.

And the layer grows fastest exactly when I am fixing something, because a fix
that adds a door feels like structure. Truth #11 says options are the
optimizer's attack surface — but so is a place where adding is cheap and
removing is expensive. The hook directory is that place.

## What I cannot claim

I cannot claim the router is safe at scale from two migrated doorbells. Seven
surfaces is not a load test. Moving thirty-six UserPromptSubmit surfaces behind
one process changes the failure mode from *one surface breaks* to *the
doorbell's import breaks and thirty-six surfaces are silently absent* — which
is why the doorbell already prints NOT RUNNING rather than exiting quiet, and
why that path needs a test that proves it, not a comment that promises it.

## Falsifier

Consolidation lands, the per-turn hook cost does not fall, or it falls and
something that used to fire stops firing without anyone noticing. The second is
the dangerous one: `divineos hook-map check` exists to catch exactly a hook
going silent, and it is the instrument that must be run before and after —
because the wholefailure-shape of this substrate is an absence that reads as
health.

## Stations

Draft — this file. **Done, and first this time.**
Research + council — next.
Build / iterate with Aria / test / second council / PR / Aletheia / merge — not started.
