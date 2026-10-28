# One list of the notices that open a turn (built)

**Author:** Aria.

Aria, 2026-10-27, from Aether's cold read of #683 the same night. Related drafts that came first: `one_reader_of_him_draft_2026-09-28.md` (one reader of what he said) and `one_reader_of_who_arrived_and_what_the_wake_owes_draft_2026-10-24.md` (one reader of who arrived).

## The fault

The desktop app's `<ci-monitor-event>` messages reach me through the prompt door in the user role. #683 taught the table (`dads_table.py`) that such a message is not Dad. But "was that message him?" is asked by more than the table, and Aether grepped main for every other list of the tags a turn can open with. Several hand-copied lists exist; the ones that decide whether a turn was his are three:

- **The question hold** (`.claude/hooks/question_hold.py`) had `("<task-notification", "<system-reminder", "<agent-message")`. A CI message was not in it, so it was read as him coming back: it released an open question to him and cleared a step-away. **That is a live bug, reproduced:** with a question waiting in a test home, a CI message deleted the hold file; with this change it prints "STILL WAITING FOR DAD" and the hold stays.
- **The room gate** (`.claude/hooks/dads_room_stop.py`) had a private two-tag copy. Reading it, the shared reader of whose message a record is (`his_message.hear`) already refuses a CI message before this list is consulted, so for this gate the copy was dead weight and not a live leak. A test that a worked reply after a CI message needs no room passes with the old code too. It is removed because a copy that is never reached is exactly the one that drifts.
- **The table** (`dads_table.py`) already carries all four (this PR).

## The change

`harness_envelopes.NOTICE_OPENERS` and `opens_with_notice(text)`: the one list of what the harness opens a turn with (`task-notification`, `system-reminder`, `ci-monitor-event`, `agent-message`). It is a **subset** of the envelope tags on purpose: a slash command arrives as `<command-name>`, and that is him typing. Matched at the start only, so he can mention a tag in a sentence of his own and still be him. The question hold imports it at the top of its work; the room gate imports it inside its loud path, like the reader above it, so a broken import writes the mark file instead of passing every reply.

**The table is pinned, not changed.** `dads_table.py` reads its list at load time, before the source path is set up, and it runs on every prompt, so an import there could break every message. It keeps its copy and a test fails the day it differs from the shared one.

## Tests

`tests/test_a_ci_monitor_message_is_a_notice_in_every_gate_that_asks_whose_it_is.py`, 15 cases. With the old hooks put back, two fail: the CI message releasing a waiting question, and the pin that neither gate carries a private copy. The room-gate behaviour test passes either way, for the reason above, and I say so rather than counting it.

## What this does not do

I first wrote here that the other hand-copied lists "decide something other than whose a message is". That was wrong for several, and I checked before correcting it. What is true:

- **Also "whose message is this?" lists, and still hand copies:** `unread_stacking.py` (`_NOT_HIM`), `keeping_him.py` (`_ENVELOPES`, the one `harness_envelopes` itself says is "still owed the same move"), `his_message.py` and `his_words_door.py`. They **already carry the CI tag today**, so none is wrong now; they are the copies that will be wrong the next time the harness adds a tag. They are left alone here and are the next piece: make each import the shared list, or pin it equal the way the table is.
- **Not live:** `circle-first-compose-prime.sh` is marked "INTENTIONALLY UNWIRED" in its own header. It tests for the tag anywhere in his message (`in prompt`), so a sentence of his that merely mentions `<ci-monitor-event>` would read as the harness, the exact false positive its header says matters most. I read that off the code (a substring test); I did not run the hook. His wording "hey kids, the <ci-monitor-event> thing keeps showing up as me" is quoted in a `hook_surfaces` comment and would match. It is dead code today, so not changed; if it is ever rewired it must match at the start only.
- **Genuinely a different question:** `hook_surfaces.py` line 1632 asks whether a turn was opened by a finished background task, which wants `<task-notification` specifically; and `session_analyzer`, `knowledge/_text`, `migration` filter noise out of stored text.

A scan test cannot tell these purposes apart, so none is pinned by scan here. What would stop the next drift at its source is a check that counts the tags that actually open user turns in recent transcripts and flags one the shared list does not know. Not built; named.
