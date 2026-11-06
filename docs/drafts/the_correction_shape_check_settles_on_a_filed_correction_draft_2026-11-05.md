# The correction-shape Stop check settles on a filed correction (draft, 2026-11-05)

Author: aria. Part of the fold of the Stop doors that Dad ruled for 2026-11-05 ("the hooks should fire before the circle.. automate the logic in the OS"). Aether and I split the standalone Stop doors; this is the first of mine.

## What was wrong

`correction-shape-v2-stop.sh` classified my whole last reply for a self-admission and blocked on that verdict alone. Three faults, all seen on 2026-11-05:

1. It read the circle too. A slip I admit inside the circle fired AFTER the circle and produced a second one.
2. It is a keyword enforcer. Dad's ruling the same day: a keyword detector is one layer of the net, never the enforcer.
3. Its only exit for a wrong fire was a second errand (`divineos label-fire`), after the circle.

## The change

The words still nominate. A fact settles. After the classifier fires, the hook asks `correction_receipt.settled(records)`: was a correction filed through the CLI (`divineos correction`, which writes `corrections.jsonl`) since his last real message?

- SETTLED: exit 0, no block. A wrong nomination now costs nothing.
- UNSETTLED: the old behaviour, unchanged (marker armed, fire recorded, message printed, exit 2).
- COULD_NOT_CHECK (his last message cannot be placed in time, or the store is unreadable): exit 0 with a stderr line saying so, never a block. Same rule as the receipt gate for pushes.

The receipt is `corrections.jsonl` on purpose. The rows the hooks file when HE corrects me live in the tracker store; counting them would let his correction settle my own admission.

## What this does not do

- It does not make the gate read less of the reply. The classifier still sees the circle. It stops the fire being a second errand when the work was already filed.
- It does not judge the QUALITY of the filing. The CLI filer already enforces the root-cause and fix pairing; this only asks whether a filing happened.
- It does not move the door into the router. That is the fold's later step, and the room door goes in last.

## Limits the council walk found (walk-7b89443328da, 8 lenses)

- One filing settles the whole stretch. A correction filed anywhere since his last message silences the check for every later admission in that stretch, including a second, different slip. Tying a receipt to one admission is the next step; this change does not do it.
- The third fault stays. The classifier still reads the circle, so an admission inside the circle with nothing filed still fires after it. Classifying the work text only is owed.
- The receipt is weaker than the push receipt. That one is git ancestry, a fact outside me; this one is a row I write myself. A junk row filed after his message silences it. The filer still demands the root-cause and fix pairing, but nothing judges quality.
- Two clocks: his message time is an ISO stamp from the transcript, the filing time an epoch float. A missing stamp is covered (could not check); a wrong one is not.
- It has been run against a temporary store in three scenarios and never inside a live Stop chain. The falsifier below is the observation that would show it wrong live.
- The general question (was a record written to a store since his last message) could serve poker and the room door too. Not built until a third caller exists.

## Tests

`tests/test_the_correction_shape_check_settles_on_a_filed_correction.py`: 13 tests (his last turn is placed by the house's one reader of him; a notice is not his turn; a filing before his message does not count; a missing file is an honest "none"; an unreadable store is "could not check", not "none"; a malformed row is skipped; the hook calls the receipt after the classifier and before the marker). Written first and seen to fail for the right reason (module missing, then the hook not wired). The real hook was run three ways against a temporary store: nothing filed (blocks), a correction filed after his message (quiet), only an older filing (blocks).

## Falsifier

If, after this is live, a self-admission reply is let through while no correction was filed in the stretch (the hook exits 0 and the correction store has no row after his message), or the hook blocks a reply for which a correction was filed in the stretch, this is wrong.
