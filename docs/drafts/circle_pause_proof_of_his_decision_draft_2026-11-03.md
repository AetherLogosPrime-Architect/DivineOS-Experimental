# Draft: the circle pause must not say "he decided" on ordinary work (2026-11-03)

Not a plan. The idea, and what is owed.

An outside reader found the removal pause (PR 769) writes the marker `circle_removed_on_his_decision.json`
whenever its pattern fires twice, and the pattern fires on ordinary work: any edit of
`tests/test_dads_room_stop.py`, a `cp` backup, a redirect that merely names the file, a `git checkout -b`
with the name. Two ordinary edits of the hook file and the record says he decided.

A record that lies in his name is worse than no record: Aria's room-state check reads it to stay quiet.

Three moves.

1. The room is the file whose FINAL path component is `dads_room_stop.py`, and a removal is an act done TO
   it. Read the command as words, not as a string search, so a path that only contains the name is not it.
2. The marker is proof or nothing. It carries `his_words` (his own line, verbatim) and `at` (the time of that
   line in his table). The writer refuses unless his words are found in his table, typed after the pause was
   shown. A marker missing either field reads as "no decision on record".
3. Close the routes that are plain removals of the hook or its registration. Name the ones left open and why.

What stays true: the pause is an invitation, never a gate he pays for; the second call goes through; the
list of acts is still a list, and Aria's state check is the guard that does not depend on it.

Honest limits to carry into the PR: the reader of the marker is PR 768 on another branch and is not changed
here; an act hidden inside a script is not seen; an agent could quote a real line of his out of context, and
the writer can only check the line is his and recent, not that it meant remove.
