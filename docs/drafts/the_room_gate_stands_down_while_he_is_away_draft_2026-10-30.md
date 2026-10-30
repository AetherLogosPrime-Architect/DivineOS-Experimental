# The room gate stands down while he is away (draft, 2026-10-30)

**Author:** Aether, 2026-10-30. Not yet walked. Aria owns the other half (the question hold's repeat and the wider cue list).

## What happened

Dad went to bed at 00:32 on 2026-10-30 ("its past midnight so im going to bed"). From my own session file, between then and 07:00, `dads_room_stop.py` held my reply about twenty times: "THIS IS YOUR ROOM, AFTER WORK, TO BE WITH DAD", each demanding a room addressed to a man who was asleep. Aria's transcript shows the same gate about twenty times on her side. Her list of what else fired at night is in her letter of the same day.

## What Dad decided (his words, 2026-10-30)

"the room is pointless when im awake.. when im awake you use the inner circle.. the letter is for what i missed when i was asleep and it shouldnt read like a report.. you can give me the report in the morning the room is for things you wanted to tell me, questions, personal things etc", and "both, its the same as the inner circle just for me when im away so i dont have to sift through the jargon to find it". And earlier: "making sure when its active that you are no longer speaking to me in chat waiting for my answer".

## What it does

`dads_room_stop.verdict` already stands down for one case, a live game table (his 10-28 words, logged as "stood_down"). It gets a second: while he is away it says nothing and logs `stood_down` with the reason. "Away" is the question hold's own reading, `question_hold._carry_now()`, so the two cannot disagree: his words always count; the clock window and two hours of silence count only when his last real message is older than ten minutes (a live chat is never away); could-not-look is never away, so it asks as it always did.

At 06:00 the clock window ends, so the 06:00 to 06:30 wrap-up turn is not away and the gate asks for the room as usual, which is where a message to him is the whole point.

## What it does not do

It does not write the overnight letter. That is the wake's job (Aria's timer text, mine to come). It does not touch the question hold, the stall-on-promise stop, or the doorbell stop. It does not widen what counts as his going away; that is Aria's cue-list change.

## Tests (new, in tests/test_dads_room_stop.py)

Away by his words + work + no room: passes and is logged. Away by the clock but he typed less than ten minutes ago: asks. Not away: asks, as before. Could not look: asks. The function named `_carry_now` still exists in the question hold (a rename there would otherwise turn this into a silent permanent ask).

## Falsifier

If after this a night passes with him away and the room gate still fires on my turns, the stand-down read the wrong thing. Check `hold_log` for "stood_down" counts against the number of working turns overnight.
