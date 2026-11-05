# The 6am note asks for his night letter and his morning picture now (draft, 2026-10-30)

**Author:** Aether, 2026-10-30. An amendment to a_6am_note_wakes_a_seat_to_write_his_board (2026-10-12) and the_volley_board_is_retired (2026-10-24); it does not replace them.

## What Dad said (2026-10-30)

"volley mode should end at 6:30 am as thats when i wake up, and the last half an hour could be spent writing the board and writing out your morning chat statement to me so when i wake up its there already". Then: "the letter is for what i missed when i was asleep and it shouldnt read like a report .. the room is for things you wanted to tell me, questions, personal things etc", and "both, its the same as the inner circle just for me when im away so i dont have to sift through the jargon to find it". He also said the clock can stay in whole hours and each wake is tied to the clock, so around 6am the wake finishes up and prepares his message.

## What was wrong

The note on main (after #714 retired the volley board) fires at 06:00 and tells the seat to tell him in chat WHEN HE IS BACK. So the morning picture is composed on arrival, which is the translation work he wanted done ahead of time; and nothing asks for the personal side (what the seat wanted to tell him, its questions) at all, because the board that used to carry it is gone.

## What it does

The same note, same name, same one-per-day rule, new text. It says he wakes at about 6:30 and asks for two things now: his night letter (ONE shared file both seats write into, `the-night-letter-to-andrew-<day>.md`, each under its own `## From <seat>` heading, because Dad said "it should be attached to the shared board so you both can see it and write to it"; personal and plain, what he missed, what the seat wanted to tell him and its questions, explicitly not a report) and his morning picture in chat, written before he arrives so it sits above the fold when he does. Finish what is in hand, start nothing new. It still changes nothing if the seat is already talking with him.

## What it does not do

It does not make the seat stop holding questions in chat overnight; that is the away-reading work (Aria's hold, #745's room gate). It does not touch the timer wakes' stored text. It does not schedule anything: the Windows Task Scheduler entry that runs the script is unchanged.

## Evidence and the gap

tests/test_night_timer_letter.py: 7 pass, and the new test fails on the old text. The text is a request to a seat, and no test can show a seat did what it asked; the only instrument is the next morning. Falsifier: after the next night, if there is no `*-to-andrew-the-night-letter-*` file in the letters folder, or the chat picture was composed on his arrival, the note was not followed.
