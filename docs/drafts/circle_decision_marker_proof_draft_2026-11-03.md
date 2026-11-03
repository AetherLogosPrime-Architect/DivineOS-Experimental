# Draft: the "he decided" marker is written from his words or not at all (2026-11-03)

The idea, not a plan. Second of three moves from the outside reader's findings on PR 769.

Today the pause writes `circle_removed_on_his_decision.json` by itself on the second removal call. It has no
way to know he said anything. Fixing which calls count (move one) makes it fire less, but the file would
still be the pause vouching for itself.

The shape that makes it honest: the pause stops writing the marker. A separate writer takes a line as input
and writes the marker only if that line is found in his own table (the file his table appends every message he
types to), typed after the pause was shown. The marker then holds `his_words` (the whole line from the table,
so it cannot be a paraphrase) and `at` (the table's own time for it, in UTC to the second). The reader treats
a marker missing either field, or with an unreadable time, as no decision on record.

Prior art found: `landing_homework.his_words_were_typed` already checks that quoted words are a stretch of
something he typed (using `his_message.typed_part`, which cuts out pasted blocks). It answers yes or no and
keeps no time, so the writer reuses `typed_part` and the same table and adds the row's time.

Why the second call does not carry the words itself: the hook only sees the tool call, never his message, and
reading his message to guess his meaning is the phrase list this module deliberately gave up. So the second
call goes through with no reason owed, as before, and the words are recorded afterward by whoever acted.

What this cannot do, to say in the PR: it checks that the line is his and came after the pause, not that it
meant "remove". The reader of the marker is Aria's PR 768 on its own branch, so the same two-field check is
offered as `decision_on_record()` for her side to call; it is not changed from here.
