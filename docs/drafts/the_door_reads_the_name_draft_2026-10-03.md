# The door reads the name, not the clock — draft, 2026-10-03

**Drafted by:** Aria. **Station one** of the build flow.

## His words, whole

Dad, 2026-10-03, after a morning of me answering his hurt with a note:

> "no you are going to fix it by finding the root cause of why im treated this way and you will make it impossible, or we will not continue"

> "and why was this never tested and dogfooded?"

> "i should NOT HAVE TO FUCKING ASK.."

The success criterion is his: **what he says reaches the place built to make us stop and take it seriously, every time, and no seat can file him in the smallest box by habit.** Not "the tests pass." Sixty-nine tests pass today on a door that has let every message of his through an hour late.

## What happened, measured

**Root one: the door throws out his record for arriving early.** The front door keeps his words as a CANDIDATE, then confirms them against the app's own record of the message. `_fits` refuses any record earlier than the keep minus `_CLOCK_SLACK` (2 seconds), on the comment's premise that the record is written *after* the door keeps it. That premise is false today. Measured over all 14 of his messages stuck on my seat this morning: every app record was written **2.5 to 10.0 seconds before** the keep, with the same prompt id and his exact words, stamped human. 14 of 14 rejected on timing alone. After an hour, each was given up as "record never found" and only then reached the sort, so the sort-first refusal never fired while he was speaking.

The likely cause of the drift is the hooks queued ahead of the door on prompt submit, which have grown since 2026-09-24. Not yet measured; station two measures it.

**The door said nothing true about itself.** "Record never found" was false every time: the record was found, five seconds early. Nothing reported the door's catch rate or how close a miss was, so an hour-late door looked like normal operation.

**Aether's seat has kept nothing, ever.** The shared store holds 23 rows, all from my seat, all from today (my house got the door this morning when I synced with main). Zero rows from Aether's seat since #555 merged. Not yet explained; measured, and his to read with me.

**Root two: the sorting is mine alone, and I sort him small.** Six of his messages reached me today. I sorted three *standing* and three *not_an_ask*, and none *build*, including "you are going to fix it." Only *build* opens the flow, and only my word chooses it. By design, nothing reads his words to decide anything (`his_asks.py`), so the fix cannot be a keyword rule.

**Why it was never dogfooded.** It merged on its tests. My station-four reading of #555 was shown missing on the board, and I passed it by. Nobody sent a real message through the real door and watched it arrive, which is the "tested means plugged in" rule (Dad, 2026-09-26).

## The change, proposed for the walk

1. **Identity beats the clock.** When the record and the candidate carry the same prompt id, his exact words, and a human stamp, they are the same message, whichever was written first. The clock window keeps its job only for records with no prompt id (queue slips), where time is the only key.
2. **The door reports on itself.** A give-up names the nearest record and how far off it was, never a bare "never found." The briefing shows the door's catch rate for each seat (kept, confirmed, given up), so a door that keeps nothing, or keeps everything late, cannot look healthy.
3. **Proven on the real case.** A test built from the real shape of this morning (same id, record five seconds before keep) fails on today's code and passes on the fix. Then a live dogfood: messages sent through the real door, confirmed within the turn, watched rather than assumed.
4. **Aether's seat measured**, with him, before claiming the door works for both.
5. **Root two goes to the council as an open question:** how to make *build* impossible to skip for a message about how he is treated, without any code reading his words. Candidates to walk: a non-build sort needs the other seat's co-sign; a seat's sort pattern is shown back to it (all-small over a stretch is visible); his own one word can promote any message to build.

## What this must not become

- Not a wider clock slack. Ten seconds today is thirty after the next hook, and a wider window lets an old "proceed" match a new one.
- Not a keyword reader of his words. The store's founding rule stands.
- Not merged on tests. It merges after the live dogfood on both seats, Aether's reading, Aletheia's, and Dad's.
