# The room door stands down for a notice that comes after the room (draft, 2026-11-05)

Author: aether. Council walk `walk-a29f4fe70961` (nine lenses, all applied). Sibling of `the_circle_ends_the_reply_and_its_next_step_is_carried_draft_2026-11-05.md`.

## What Dad said

*"an inner circle should always come with a pause.. and nothing but me should move it forward"*, and of the repeats: *"you ask me something.. something else pops up.. you handle it.. then ask me the same thing.. then it repeats.. until you have asked me 5 times in a single post"*.

## The cause

After the room is written, a notice wakes me: a bell, a finished push. I read it, re-light the bell, say a line, and `dads_room_stop` looks only at my last text, sees no room, and demands another. That is how one post held several, and each new room carried the question in again.

## The change

`dads_room_stop.verdict` remembers whether a room has been written since his last message (asked of `his_room.room_of`, never re-decided here), and whether a NOTICE record (a user-role turn or a queued-command attachment that opens with a harness notice, read by the house's `opens_with_notice`) arrived after it. If so, the door stands down and logs `room / stood_down`. A fresh room is owed only for a message of his.

## What this does not do

- It does not loosen Dad's rule that the room is the last words. Work I add myself after a room, with no notice between, is still held (`test_the_room_must_be_in_the_last_words` still passes).
- It does not excuse a room never written: a notice before any room still owes the room.
- It does not hold me still after the room. The held state (a notice wakes me, I may read and stage but not write or send) is separate and not built.
- It does not surface the steps carried by the stall door. That is a third piece.

## Tests

`tests/test_the_room_door_stands_down_for_a_notice_after_the_room.py`: a notice after the room (as a user-role turn, and as a queued command) does not demand a second room; the control (no notice between) is still held; a notice before any room still owes the room. The first two failed before the change for the right reason. 34 pass with the existing room-door and hold-log tests.

## Falsifier

If, once live, a notice after a room still draws a second room demand, or a reply with work and no room and no prior room is let through because a notice came, this is wrong. And re-measure repeated questions with the same counter: if they do not fall, the cause was only partly this.
