# Replacement criteria — when a new mechanism may retire an old one

**Written 2026-08-15, immediately after violating every rule in it.**

## The incident this exists for

The native session-to-session message channel arrived. It was clean, native,
and made our hand-built letter-delivery machinery look embarrassing — five
competing systems for one job, three running at once, one of them lying about
whether it was armed since June.

So I proposed retiring the postal service and letting the native channel carry
the wake. Then I executed part of it: fifteen delivery files archived and
deleted, seven test files, five hook registrations.

The native channel had, at that moment, **never once delivered successfully.**
Four sends, four jams, zero clean landings.

Aria's decisive test — all twenty-eight of her prompt hooks disabled, message
still jammed the window — proved the fault lives in the delivery path itself.
The replacement I had bet on could not do the job at all.

She found the counter-argument in my own writing, `exploration/aether/111`:
the component that crosses the lifecycle boundary is structurally the
most-broken component, and that is not accident. The native channel is a
boundary-crossing component. I proposed making the newest one load-bearing on
its first day.

## The two errors, and the second is worse

**Elegance decided.** The incumbent embarrassed me and the replacement was
clean, so "shabby" got read as "replaceable" without a single successful
delivery required as evidence. Design quality is not delivery evidence.

**I acted before the evidence arrived.** I deleted, and only after her result
came back did I check whether the surviving fallback still worked. It did —
`ear-surface.sh` was intact and fired that same turn — but I verified *after*
acting. Same ordering error as merging branches onto a red `main` earlier the
same day.

And the deletion took the CLI down with it: `cli/monitor_commands.py` imports
`core/monitor_cleanup` and `core/monitor_singleton`. Both were on a
dangling-reference list I had generated, read, and then not acted on. The
breakage surfaced while running the very command that logs this correction.

## The rules

**1. An incumbent is retired by evidence, not by comparison.**
The replacement must succeed at the incumbent's actual job. "Better designed",
"native", "fewer moving parts" are not qualifications. Zero successes is
disqualifying regardless of how bad the incumbent looks.

**2. The bar is a count, agreed in advance, in the failure mode that matters.**
Name N before testing, not after. For the message channel: ten consecutive
clean landings across both directions, and it does not carry a wake until it
has survived an idle receiver — the case that failed every single time.

**3. The fallback is verified working BEFORE the deletion, not after.**
Run the check. Read its output. Then delete. A fallback assumed intact is a
fallback with no evidence behind it.

**4. Dangling references are resolved before removal, not listed.**
If a removal produces a reference list, that list is a work item, not a note.
Nothing is deleted while a live caller still imports it.

**5. Archive is not a substitute for any of the above.**
Recoverability lowers the cost of being wrong; it does not license being wrong.
Archive everything anyway — but the archive is the seatbelt, not the brakes.

**6. Operator testimony of observed behaviour is evidence.**
Added the same day, after breaking it. Andrew: *"the monitor we used to have
worked fine.. it just keeps dying and nothing checks for it or resets it, but
when it worked it worked."* I heard fondness, filed it as nostalgia, and went
looking for what was wrong with the mechanism instead of for when it was right.

One unopened log settled it — `aria_rearm_events.log`:

    [LETTER-MONITOR-ARMED] watching ...\letters for *-to-aria-*.md
    [LETTER] ...\aether-to-aria-2026-07-19-wrapper-implementation-shipping.md
    [LETTER-MONITOR-HEARTBEAT] alive
    ...
    [2026-08-02 16:36:16] FALLBACK activated after 3 failed spawns in 77s

It armed, caught a real letter, heartbeat-ed for two weeks, then spent a
`RestartCount 3` budget in 77 seconds and never tried again. A countdown, not
a supervisor. It had been dead 13 days, and the liveness check that should have
caught it was the one reporting armed unconditionally since June.

So: when he reports that something used to work, the FIRST move is to search the
telemetry for the last successful run and the event that ended it — not to audit
the mechanism for design flaws. If no such record exists, say so plainly; do not
substitute a critique for the search.

This is need-21d2eb2d inverted. That need names performing-rigor as a route
around receiving the architect's testimony. Here my own measurements outranked
his account of what he personally watched happen, and across one day his account
was the better evidence four times running: the stop-behaves-normally detail
that killed the hook-queue theory, the reverse-direction test design, the
orphaned-background-task message that led to a documented platform bug, and this.

## The shape underneath

Boundary-crossing components are structurally the most-broken things we own,
for as long as we own them. That is a budget to plan for, not a defect to be
surprised by. Which means the *newest* boundary-crossing component is the
worst possible candidate for load-bearing work, and the pull to promote it is
strongest exactly when it is shiniest.

Related: `exploration/aether/111`, and the addition-with-eviction rule — no new
surface without naming what it retires. Both rules are needed. Eviction without
evidence is this incident; evidence without eviction is the five competing
delivery systems that caused it.
