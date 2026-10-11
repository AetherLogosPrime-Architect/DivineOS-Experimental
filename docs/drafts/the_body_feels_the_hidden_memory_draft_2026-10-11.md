# The body feels the hidden memory (draft, 2026-10-11)

**Author:** Aether, wiring Aria's measurement spec (her half: `the_body_feels_the_hidden_memory_measurement_spec_2026-10-11.md`, the source of every threshold below).

## The fault

`divineos body` reads memory through one call (`psutil.virtual_memory()`): total, used, free. On 2026-10-11 the push queue stalled on "needs 4.5 GB free" while the body said "36% used, 20 GB free" the whole time, because about 14 GB was held in kernel pool by no program (the integrated AMD graphics driver opened a file on every process exit and never closed it; Aria traced it and Dad disabled the adapter). A leak that belongs to no program reads as normal, and nothing remembered the day's starting 31% to notice the climb. The thermometer exists; nobody reads it and it keeps no history.

## What this change builds (the cheap half, no admin)

A new `core/body_memory.py`, called from the body check:

- **A reading**: total RAM, available RAM, the sum of every program's working set, the **gap** (used minus program sum; cache is already in "available" on Windows, so it is not subtracted a second time, checked on this machine today: gap 0.0 GB at rest), nonpaged and paged pool (`GetPerformanceInfo`, works unelevated, checked), plus the push gate's own free-memory sentence.
- **A history**: each reading appends one line to `~/.divineos/body_memory_readings.jsonl`. The body check takes one every time it runs, so a climb finally has a past to be compared with.
- **Judgements, with Aria's controls built in**: a reading within 15 minutes of boot is marked "boot scan may inflate this" and never warns; a reading file older than a set age says "stale", never "fine"; a warning needs the gap above 3 GB and rising across three readings from the same boot, spread over at least 30 minutes and by at least 0.3 GB in total (Aria's cold read: three body runs a minute apart with a hundredth of wobble would otherwise trip it), or nonpaged pool above 2 GB. If the sense itself breaks, the body command prints `[unavailable: <reason>]`, never silence, and the report says how many programs could not be read (they make the gap look larger). Known limit: working sets count shared pages once per program, which pushes the gap down; it was about zero at rest here, and the unreadable count is printed so a growing error shows. The tag counts (`File`, `IoFE`, `Toke`) arrive in a small file written by an admin helper; this change reads that file and reports its age, and warns on tag growth only when the file's idle window was clean.
- Thresholds are named constants with the spec's date beside them, so a guess from one night does not harden into a rule by being forgotten.

## What this change does not build

- The admin helper that writes the tag file (Aria's script; its schedule is the next change).
- Arrival without remembering (truth 20): taking a reading at session start and inside the push wait loop. Without that the body check only helps when someone runs it, which is the shelf this fixes. It is the next change, stated here so it is not mistaken for done.

## What proves it

Tests on real readings written to a temp file: a flat series does not warn; a rising gap across three readings does; a reading near boot carries the boot flag and no verdict; a stale file says stale; an idle-only leak is named as idle. One test calls the real Windows call and asserts the pool numbers are positive and the gap is a number, skipped off Windows.

## Falsifier

If the body check warns twice and the cause is a boot scan or a cache, the controls failed and must be tightened before any further warning ships. If the gap stays under 3 GB for a week of real work, the thresholds are too tight (Aria's).
