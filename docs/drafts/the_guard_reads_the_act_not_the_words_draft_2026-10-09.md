# The guard reads the act, not the words (draft, 2026-10-09)

## What was wrong

Two checks in `gravity_classifier.py` (the store-write check and the consolidation check) searched the raw command text for `divineos <verb>`. Any text carrying those two words fired them: a heredoc body that merely mentioned the command, a quoted string, or the help flag. Aria hit it twice on 2026-10-09 (the prereg word in a body, and `prereg --help`). Dad named the shape: a keyword detector standing where a guard should be. The git-commit check had already been moved to reading each segment's real head; these two had not.

## The change

One shared helper, `_runs_divineos_verb`, now answers "does a segment really run this verb". It drops heredoc bodies, splits the command into segments, strips `sudo` and `python -m`, and fires only when a segment's program is `divineos` and its verb is in the list, unless that same segment asks for help. A command the splitter cannot read (a substitution hides what runs) stays on the old text search, so reading better never loosens what could not be read.

## What it does not loosen

A real invocation in any chain, behind `sudo`, `python -m`, or a redirect still fires. Help is judged per segment, so help on one segment does not excuse another segment that runs a verb. The unreadable case keeps firing.

## Proof

`tests/test_gravity_cli_features_read_the_command.py`: eight word-only shapes that failed before and pass now; real invocations and the substitution control pass before and after. The existing classifier tests pass unchanged.

## Not covered

The other gates that decide on words (the one that blocked Aria's `prereg --help` read may be a different path) are not audited here. Residual: an act hidden inside a substitution is read by the old search, which a quoted mention can still trip.

## Review

Source change under `src/divineos/`: full review before merge. Walks: council-723e68b56d1c, game-walk filed on the same fingerprint.
