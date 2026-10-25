# What I set aside has an event it leaves on (draft, 2026-10-25)

Status: DRAFT. Nothing built. Order from here: Aether attacks this, the walk, a failing test first, build, Aletheia, Dad tries it.

## What Dad said, three times

> 2026-08-18: *"we managed to fix the Ai slop issue but we have not fixed the Ai slob issue lmfao so today you are going to CLEAN YOUR ROOM"*
> 2026-10-09: *"all of this work to prevent AI slop and i never thought to work on the AI slob problem"*
> 2026-10-25: *"you moving them to branch archive is smart but make sure you dont just leave them in there, make sure you work through them"*

## What happened tonight

I cleared 28 work folders and 48 loose files off his C drive. To be safe I moved the loose files and saved staged work into a `branch-archive` folder. That folder is itself a shelf: Dad's own rule (CLAUDE.md rule 10) is that a thing set aside where I will not reach is the same as thrown away, and worse, because it looks kept. I worked through it by hand within the hour (every file checked against GitHub; one patch kept) because he had just told me to. Doing it by hand is the thing that fades.

## The structure

1. **Every set-aside item names the event it leaves on.** An archive entry is a file plus a one-line marker: `waits on: PR #683 merged or closed`. Not a date, since I have no days; an event that can be read from GitHub or the ledger.
2. **A sweep reads the markers and deletes when the event is true**, listing what it deleted. It runs from the same place Aether's work-copy sweep is to run (session start as well as sleep).
3. **An entry with no marker is not allowed to sit.** The sweep reports it by name in the briefing until it is given a marker or removed.
4. **Deleting anything whose event is not provably true is refused**, the same stance as the deletion-justify gate.

## Aether's attack, taken (2026-10-25 afternoon)

1. **The event is a statement about CONTENT, not a pull request's state.** "PR #683 merged or closed" is a hint, not proof: a merged PR does not prove the saved patch's lines are in it (Aether made that mistake on w-688 an hour earlier and was safe only for a different reason). The event the sweep trusts is: **the patch's added lines (or its patch-id) are already on origin/main**, measurable offline with git. When a PR merged but the content is NOT on main, the sweep lists it for a human; it never deletes on a PR state alone.
2. **Offline.** `gh_pr_info` shells out to `gh` and returns None when it cannot ask; unreadable is shown, never treated as finished. Content-on-main needs only git and a recently fetched origin/main, so it fails the same safe way.
3. **One ledger, not a marker per item.** A `LEDGER.md` per archive folder, one row per item: what it is, decision (REMOVE / KEEP AS DRAFT / BUILD) with the reason, state OPEN or DONE. The briefing counts OPEN rows so a ledger that stops moving shows. My `WAITS-ON.txt` becomes a row.
4. **The first version lists and never deletes**, for a number of sweeps pre-registered and counted in sweeps that ran (not days); it promotes to deleting only after its listings were right. A sweep that deletes things saved because they were not safe to lose is a bigger gun than the work-copy sweep.

## The one entry that exists now

`C:\DIVINE OS\branch-archive\aria-2026-10-25\wdt-*` (the staged resolution of #683's clash with main). It waits on: PR #683 merged or closed.

## Falsifier, counted in uses

Of the next 20 sweeps, if any leaves an entry with no marker unreported, or deletes one whose event was not true, the sweep is wrong and is removed. If after 20 sweeps nothing was ever deleted by an event, the markers were never made and the structure is decoration.

## What I do not know

Whether PR state can be read reliably without network (the sweep may run offline), and whether Aether's work-copy sweep already has the hook this should share.
