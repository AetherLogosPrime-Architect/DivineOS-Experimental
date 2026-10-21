# A checkup is dated on the code and logged in the logbook (draft proposal, not built)

Aria, 2026-10-20. Dad, in the middle of a talk about pulse and rhythm: *"what might help as well is a check log.. something attached to the code you can date and sign when you last did a checkup on it"* and, on how much: *"as long as the log doesnt crowd the code, it should be the same as code notes, the latest checkup only with a pointer to the logbook"*. He had already ruled the same shape for code notes (2026-09-20): the latest note in the code, the reasoning and journal archived and linked.

## What exists already (checked before proposing)

`core/tool_trust.py` is a logbook for instruments: a table of instruments with `checks_total`, `checks_truthful`, `last_checked_at`, `last_outcome`, and a `tool_trust_events` table with a timestamp, an outcome (TRUTHFUL / CONTRADICTED) and a free-text evidence line per check. It scores by Beta smoothing and gates tiers on sample count (principle eb5b5db5: trust is earned, never 100%). Nothing in `src/` ties that logbook to a place in the code, and nothing records *what kind* of checking was done. A search of `docs/drafts` for a prior draft on this found none.

## The inventory comes first (Dad, same evening)

*"technically the logbook should contain a list of every system you have that can be checked, and then mark all of them unchecked and then as you go you can add the checkup to the list, so its easy to find, and also to know what you have and have not already checked"*

A logbook that only holds what was checked cannot tell "fine" from "never looked", because both are absent. So the first thing built is the full list of checkable units, every one starting as **UNCHECKED**, and a checkup moves a unit from UNCHECKED to dated. The list is derived from the code itself (modules under `src/`, hooks, scripts, each gate), not typed by hand, and a unit that appears in the code but not in the list is itself reported ("unlisted"), so the list cannot silently fall behind the system. Same lesson as the twin database: prove the set searched is the set meant. The briefing then shows a count, *N of M checked, K stale, J never*, and `check-log list --unchecked` is the work queue.

## The proposal

1. **The logbook is the existing events table.** A code unit (a file, or a function by `path::name`) is registered as an instrument of kind `code`. One new column on the event, `method`, a short controlled word for how it was checked: `read` (looked at it), `ran` (exercised it as written), `broke` (forced a failure and watched it get caught), `cold-read` (someone else's seat). The evidence line stays free text.
2. **The code carries one line.** At the top of the unit: `# checked: 2026-10-20 aria broke -> divineos check-log show <id>`. Latest only. Rewriting it replaces it; the history lives in the logbook. Nothing else is added to the code.
3. **The line is written by the check, not by me.** A single command, `divineos check-log record <id> --method broke --evidence "..."`, appends the event AND rewrites the one line. There is no second step to forget. Per truth #11 this removes the choice-point: the only way to get a fresh date on the code is to log a real event, and the only way to log one writes the date.
4. **It goes stale on its own.** A briefing surface lists units whose latest check is older than their gravity allows, or whose code changed after the last check (the line records the commit it was checked at; a differing hash means "changed since checked"). A date on code that has since moved is the worst form of the sticker.
5. **Method is part of what is shown.** `read` does not earn the ease that `broke` does. The line shows the method; the logbook shows the run of them, so a quick glance after five hard checks reads as exactly that.

## How it can fail, written before it is built

- **A green line with no pulse.** Someone logs `read` with no evidence and the line looks reassuring. Mitigation: evidence is required and non-trivial, method is displayed beside the date, and the surface counts `read`-only units as weaker than `broke`.
- **It crowds the code.** Held to one line per unit by the writer; a test asserts the writer replaces rather than appends.
- **Nobody records.** The usual fate. So the places where a real check already happens (the push gate's results, the Breaker loop, a stamped cold read) are candidates to record on their own; that is a second step, not part of this one.
- **Stale line after the code moved.** Covered by the commit hash on the line.
- **Marking something checked that I did not check.** A line cannot prove who did the checking; the logbook event carries the actor and the method, and a signature is only as honest as the seat. This is the honest limit, stated rather than claimed away.

## Test plan (red first)

A real temp file with a unit; `record` writes exactly one line, a second `record` replaces it (line count unchanged), the logbook has both events; changing the unit after a record makes it read as changed-since-checked; a unit with only `read` events reads weaker than one with a `broke`. A mutation for each rule (drop the replace, drop the hash, treat `read` as `broke`) must turn a test red.

## What Aether's read changed (his letter, 2026-10-20 night; four breaks, taken)

- **File first; no score on code.** Show the run of methods; `broke` outweighs `read` by sight, not arithmetic.
- **The line cannot hold its own commit hash** (the commit holding the line is made after it is written). Staleness is a hash of the file's content with the checked line removed, so "stale" means the code changed.
- **The id is stable, written once, not the path**, so a rename does not orphan the row and flood the unlisted count until nobody reads it.
- **`ran` and `broke` must carry a reference that can be looked up** (a test run, a ledger event, a mutation result). `read` stands alone and is shown plainly as the weak method. Otherwise `record --method read --evidence "looked fine"` is the ten-second cheap close.
- **Print "author = checker"** beside the method, from repo history: the one fact the seat cannot fake, and it separates a self-check from a cross-check.
- **His shape question, the real fork:** rewriting a dated line into source makes every checkup a diff, and under the blanket review each one needs Aletheia's eyes for a date, which teaches avoiding the checking. His alternative: the code holds only the stable id; date, method and staleness come from the logbook (`check-log show`), with an optional generated sidecar listing the latest checkup per file. Which matters more to Dad, seeing the date beside the code or the code staying still, is open and is Dad's to rule.
- **Not yet looked at:** whether the push gate or the Breaker loop leave an event a `record` call could read, so they can record themselves.

## Dad's ruling on the fork, and the checklist (same night)

On the fork: *"we could just make an exception for date changes? or if it works better just keep it in the logbook."* Recommendation: keep it in the logbook. The code holds only the stable id; date, method, checker and staleness come from `check-log show`, with the generated sidecar if he wants to see dates beside the files. An exception for date-only edits would be a rule the review gate has to police (that the diff really is only a date), and an exception is a slot for the optimizer (truth #11); no rewrite means no diff means nothing to except.

On what counts as checked: *"you could make a checklist of things that need done to be considered checked, and make it need to be linked to the actual work, so an 'i checked it' cant satisfy it"*. A checkup is a completed checklist, and each item is closed only by a reference that can be looked up, never by a statement. Draft of the list, per kind of unit:

- Every unit: the thing was exercised (a test run or command output id); a failure was forced and the result recorded (a mutation or break result id); the checker is not the last author, or the self-check is marked as such (derived from history, not typed).
- A gate or hook: a case it should block was fed to it and blocked; a case it should pass was fed and passed (two ledger events or test ids).
- A report or log line: the reported thing was looked at independently of the report (the pulse, not the rhythm).

A checkup with any open item records as PARTIAL, shown as such, and does not clear UNCHECKED. The record command refuses to close an item without a reference that resolves to something that exists; whether it can also verify the reference is genuine (rather than present) is a limit to state, not claim away.

## What the council walk added (walk-cb07b72e9767, high gravity, 9 seated; Popper and Dillahunty came up by score)

- **Evidence must be able to come out the other way** (Popper). A reference to a lone pass refutes nothing. Every `ran` or `broke` item references a PAIR: the result with a defect forced in (must fail or be caught) and the result without (must pass). A lone pass is recorded as weak. The expected result is written BEFORE the run, so a surprise shows as a surprise.
- **Burden sits on the claim; every record states what it does not cover** (Dillahunty). A reference a stranger can resolve and re-run, or it is assertion. One sentence per record: what this covers and what it does not, so "checked" cannot stretch to the whole unit.
- **Never claim "sound"** (Sagan). The label reads what, how, result; never "ok" or "verified". Cross-seat checks are worth more than any number of self-checks, which is why author = checker is printed.
- **The attacker is me on a lazy day** (Schneier). References are bound to the unit's content hash, reuse across units is flagged, and the record command mints the reference itself by running or capturing the check, so there is nothing to type. The checklist per unit kind comes from the code, not from whoever records.
- **Doubt resolves toward showing less** (Taleb). PARTIAL by default, fast staleness for high-consequence units, never a single percent-checked headline (weak reads would average away the dark corners), the never-checked count as loud as the checked count, and a scheduled forced break for the catastrophic few (the ledger).
- **The log is its own first unit** (Hofstadter). Checked by a seat that did not write it. The unlisted-unit detector is the instrument everything stands on: plant an unlisted file, prove it is present at the moment of the read, watch it be reported. A dead control and a blind instrument return the same zero.
- **Show it where the work happens** (Jacobs). At the moment a seat edits a unit: last cross-checked N days ago, changed since. Hook recording to checks that already happen (push gate, Breaker loop, stamped cold reads) so the log fills itself from real activity.
- **Watch the drift** (Dekker). Show the method mix over time so a slide toward the cheap `read` is a visible trend; make `ran` cheap by automation so the right path is also the easy one.
- **Stock and flows** (Meadows). Edits refill the unchecked pile and checks drain it; measure rate in and rate out, not just the pile. Steer by "changed, unchecked, high-consequence units trending down", not by "a complete dated list". Staleness must surface at edit time; late feedback steers nothing.

## Aether's second read (letter 255): what is true today, and two breaks on the hash

- **Today neither the push gate nor any break-testing script leaves a ledger event** a `record` call could read (he grepped, and proved the probe on a known case first). So "hook recording to checks that already happen" is not yet true: each of those must first emit a result event. That is a small build owed before the log can fill itself. A mutation runner does exist in this checkout (`scripts/run_mutmut.py`, with `scripts/hollow_out.py` and `scripts/check_test_substance.py` beside it); whether it emits an event is not yet looked at.
- **The strip rule must be exact.** Remove one line, by an exact pattern, only within the first N lines, and refuse to hash if more than one line matches. A lookalike comment elsewhere would otherwise be stripped silently with a real edit hiding behind it; two matches is loud, and also catches one unit's id pasted into another file.
- **Changing the id to a different valid id** points the record at the wrong unit's rows (editing the id alone leaves the hash unchanged, which is the safe direction). A duplicate-id detector over the inventory catches it; the unlisted-unit check catches an id in no list.

## Open for Dad, Aether, Aletheia

- Granularity: file first, or function from the start?
- Whether the existing instrument score applies to code, or code gets the date and the method only.
- Whether the push gate or the Breaker loop should record automatically once it exists.

## Status

Nothing built. This note, then a council walk on it, then tests, then code.
