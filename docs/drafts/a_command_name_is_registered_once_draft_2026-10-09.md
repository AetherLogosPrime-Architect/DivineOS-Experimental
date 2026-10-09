# A command name is registered once (draft, 2026-10-09)

## What was wrong

Two commands were registered as `answer`. The older one resolves an open question (`divineos answer <id> "<resolution>"`). Later, the family of commands about his answers (`answer ask`, `answer got`, `answer changed`, `answer none`, `answer report`) took the same name as a group. The group won silently, so the old form stopped working. The board of what waits on him (`core/operator_asks.py`) kept printing `resolve: divineos answer <id> "..."` as the way to close an ask, which no longer closes anything. Nothing failed at start-up and each command's own tests passed, because each was tested alone. `psf` was also registered twice in `cli/__init__.py` (harmless, the second replaced the first).

Found while going through the commands one by one with Dad.

## The change

- The question-resolving command is renamed `answer-question`, matching its sibling `abandon-question`.
- The board prints `divineos ask-resolve <id> "..."`, the command that actually closes an ask and already accepts the short id the board prints.
- The duplicate `psf` registration is removed.
- A new test starts a fresh interpreter and watches registration, so any future name collision fails at the moment it happens; a control proves the watcher sees a collision it is handed.

## Not covered

`answer-question` is the general question tracker (not asks). Whether that tracker is still worth keeping alongside asks is a separate question for the commands walk.

## Proof

`tests/test_a_command_name_is_registered_once.py`: three of four tests fail on main (collision list is `['answer', 'psf']`, `answer-question` missing, board prints the dead line); the control passes before and after.
