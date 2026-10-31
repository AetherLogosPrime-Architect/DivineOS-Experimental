# The volley window starts when he goes to bed, and a goodnight counts at any hour (rough draft)

**Date:** 2026-10-30. **Author:** Aria. **Status:** idea only; Aether reads it before anything is built.

## What he said (verbatim)

2026-10-30: *"from midnight to 6am that is the volley window, unless im up past midnight then its from when i go to bed until 6am"*, after the night before, when he said goodnight and the away mode never started. On 2026-10-12 he had said the opposite for the clock window ("even if im up chatting because it means i need to get my butt to bed"); the newer sentence wins.

## What exists already (looked first)

`night_hours_are_volley_mode_draft_2026-10-12.md` (the clock window), `his_questions_overnight_go_to_the_morning_draft_2026-10-16.md` (a question asked while he is away is carried to a morning list), `a_6am_note_wakes_a_seat_to_write_his_board_draft_2026-10-12.md` (the 6 a.m. wake), and `the_doorbell_rings_forever_without_being_set_again_draft_2026-10-29.md` (the bell, which I have not yet re-read). This note amends the first; it does not replace the others.

## What the code does now (core/question_hold.py)

Three kinds of away, tried in order: his words (`step_away`, `AWAY_CUES` is a fixed list with no "goodnight"), a night clock (`_scheduled_away`: 00:00 to 06:00 local, whatever he is doing), and two hours of silence (`AWAY_AFTER_SILENCE_SECONDS`). A goodnight before midnight matches none of them, so a question asked in that gap opens a hold.

## The idea

1. **His goodnight is his words, at any hour.** The meaning-reader (the one the memory link already uses) decides "he is going away"; the check that the words are really his stays; `AWAY_CUES` stays as the floor.
2. **The clock window follows him.** After midnight it counts as away only if he has gone quiet for a while (the `LIVE_CHAT_SECONDS` idea already in the file) or has said goodnight. While he is typing at 00:40 it does not, so a question to him is held and answered as live chat. It ends at 06:00 or at his next word, whichever comes first.
3. **A goodnight in the afternoon is a nap, not a night.** Its away ends at his next word or at the next 06:00, not carried into a second morning.
4. **The 6:00 to 6:30 half hour is not in the hold.** The timer wake reads the clock and does the wrap-up (done: timer 852716ab). The hold only needs to end at 06:00 or at his word.

## What this does not do

It does not decide in the hold whether a goodnight "means" away; it asks the reader and records the quote. A reader that is wrong either way (a goodnight read as chat, or chat read as a goodnight) is the risk, and it is the one to test.

## Falsifier

If he types "goodnight" at 11 p.m. and a question asked at 11:20 still opens a hold, or if he is chatting at 00:40 and a question is carried to the morning list unseen, the change is wrong.

## Open question for Aether

Where does the meaning-reader live and what does it return for a goodnight? I have read the tests (tests/test_heard_by_meaning.py) but not the function the hold would call.
