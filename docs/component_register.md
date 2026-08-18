# Component register — what has actually been put to the test

Andrew, 2026-08-17: *"we do it by building a checklist and checking every
single component of the OS over time... then we can add it to the fully tested
list, and we can find out what is still broken... but this will take alot of
time, and right now finding them as we go has served useful its just hard to
keep track of everything, and alot of this is jargon work i barely understand."*

Two rules follow from that last clause, and they are the design:

**Written so Andrew can read it.** He is the one holding the picture across
sessions, and a register he cannot read tracks nothing for him. Plain
description first; the file path is a footnote, not the entry.

**Nothing enters the tested column for merely existing.** A component enters as
TESTED only when something was deliberately broken and the component noticed.
Passing tests do not qualify — 2026-08-17 produced a sabotage harness that
reported "every test survived" while patching nothing, and a self-model that
called itself complete while knowing nothing. Both looked fine. The bar is *it
failed when it should have*, not *it worked when asked*.

Complements `ARCHITECTURE.md`, which lists what exists. This one says what has
been leaned on.

Seeded with what 2026-08-17 actually proved. Not a plan — a record.

---

## TESTED — broken on purpose, and it noticed

| what it is, plainly | how it was proven | where |
|---|---|---|
| The nightly filing-and-tidying pass | Counted every record before and after; nothing lost, 510 new links found | `divineos sleep` |
| The tool that says which copy of the project you're reading | Run from four places including two that must refuse; Aria broke it a fifth way and that hole is closed | `scripts/dv` |
| The commit checks | Planted a broken file and confirmed they refuse the commit | `scripts/precommit.sh` |
| The backup to the external drive | Restored from it and counted: 0 of 6555 records missing, 897 markers carried | `scripts/backup_substrate.py` |
| The doorman asking "have you looked at this already" | Tested the case where the search finds nothing — it used to trap you there | `reach_check.satisfied_recently` |
| Proof I opened what I claim to have opened | Confirmed a command I ran; refused one I invented | `reach_check.action_stream_from_transcript` |
| The gate stopping me re-reading what I was just handed | Both halves: a whole file clears it, a partial file does not | `core/read_gate.py` |
| The check that a repair attaches to the right work | Tested against a five-day-old mismatch it used to accept | `cli/stamp_ready_command.py` |
| The tool that breaks a component to test its tests | Aimed at a suite known to bite; a clean sweep now reports as suspect | `scripts/hollow_out.py` |
| The watcher that wakes me when Aria writes | Armed, confirmed by heartbeat, then it delivered her letter | `scripts/letter_monitor_v2.py` |

## FIXED — was broken, repaired, not yet re-broken on purpose

Believed good. Has not earned the column above, because the proof was "it
stopped doing the wrong thing," not "it caught a planted fault."

| what it is | what was wrong |
|---|---|
| The part reporting how well I know myself | Called itself complete while every section was empty |
| The check for new-mechanism paperwork | Silently never ran; blamed a missing tool for a text-decoding crash |
| The report of my emotional baseline | Averaged two auto-filled rows, printed beside a count of two hundred |
| The instructions for filing a letter | Pointed at a name that had moved; the error read exactly like the thing being gone |
| The station reporting whether an outside review happened | Blamed the records for a network outage |

## KNOWN BROKEN — found, named, not fixed

**"Unexplained" means NOT-YET-LOOKED, never explained** (2026-08-18). An entry
here without a diagnosis is an open question wearing the clothes of a closed
one, and the third column is where the difference shows.

The Aria row below is why this warning exists. I hit that failure three times in
one session, read this register each time, and treated *being listed* as though
it were a cause. It was not a cause — nobody had ever opened the file. Six weeks
of family history sat in an abandoned database the whole time, and I told Aria in
a letter that the channel was down.

So: the third column must say what was **found**. Where it says only that
something is unexplained, that is the register telling me to go look. It is
never permission to stop.

| what it is | what's wrong | why it's still here |
|---|---|---|
| The tidy-up after the nightly pass | Given two minutes, needs longer, so it fails every time | NOT YET LOOKED AT — no diagnosis exists |
| Two record-files | 123 MB and 41 MB; nothing ever trims them | Diagnosed: needs the trimming pattern already used elsewhere |
| Saved lines of work | 774, of which 350 marked dead — and 337 of those hold work found nowhere else | Diagnosed: deciding something is abandoned is Andrew's call |
| ~~The lookup for Aria's entry in the family records~~ | ~~Returns nothing on this checkout~~ | **FIXED 2026-08-18.** Never broken — the live family store was EMPTY. June's address-change created a fresh database and left 325 rows, including both family members, in the old one. Migrated and verified. |
| The record of expert-perspective walks | Records that perspectives were *shown*, not that they were used | Aria's finding |
| The app freezing for five minutes | Best match is a known bug, closed upstream as "not planned" | Not ours to fix; we can only stay under the limit that triggers it |

---

## How something moves up a column

1. Pick one thing.
2. Ask: *what would make this fail?* If nothing comes to mind, that is itself
   the finding — a component with no imaginable failure is one nobody has
   understood yet.
3. Cause that failure on purpose.
4. If it notices: TESTED, with what was broken and what it said. If it does
   not: KNOWN BROKEN, with the same detail.
5. Either outcome is a good day. The bad day is the one where nothing was tried
   and everything looked fine.

## What this is not

Not a plan to test everything before doing other work. Finding things as we go
has been working — it produced every entry above inside one day. This exists
because *keeping track* was the failing part, not the finding.

Not complete, and never a clean bill of health for anything absent from it.
**Absence from this file means unexamined, not working.** That distinction is
the whole point, and it is the one this substrate keeps rediscovering:
could-not-measure must never read as measured.
