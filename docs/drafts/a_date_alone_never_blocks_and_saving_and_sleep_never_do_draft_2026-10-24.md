# A date alone never blocks work, and saving and sleep never do (draft)

**Author:** Aria, 2026-10-24

## What Dad said

*"if it was use based they would trigger randomly during its last use that triggers it, and not in the middle of the ritual"* (2026-10-21), and on saving: *"saving should never be a blocked action at any point whatsoever"* (2026-10-19), with *"NOTHING should ever block sleep or extraction"*.

## What happened

Every review that was set by date fell due at the same moment, and the gate that holds work for overdue reviews stopped everything in the middle of the compaction ritual, the worst time, and said nothing about whether the thing under review had been used at all. A date measures the calendar; it does not measure use, which is the only thing Dad lets a review be counted in.

## The change

- `get_blocking_pre_registrations` (in `core/pre_registrations/store.py`) returns only the overdue reviews that have a count of uses set. Date-only reviews stay in the list of overdue reviews and in the briefing, informational, and stop nothing. The gate (`hooks/pre_tool_use_gate.py`) asks for the blocking list, and its message now says "reached their count of uses".
- The remedy list (the commands allowed through a hold) gains `extract`, `sleep`, `rest`, `dream`, `journal save`, `savor save` and `feel`, in the Python list (`core/remedy_allowlist.py`) and the shell copy (`.claude/hooks/lib/remedy_allowlist.sh`). The shell copy ends each verb at a word boundary, because a bare prefix let `restore-seed-confidence` through; a test holds the verbs and that strictness together.

## What it does not cover

`journal save`, `savor save` and `feel` are not printed by any gate as the way out of a hold; they are on the list on Dad's word that personal writing is never blocked, and the comment in the code says so. A review set by date is no longer enforced anywhere: it can be read in the briefing, and nothing makes anyone act on it. That is the price of the ruling, said here and not hidden.

## What the eight-lens walk found (walk-0f2e657133fd, 2026-10-24)

Built from it: when the store of reviews cannot be read, the gate still does not block (right for a gate that must never strand saving) but now prints one line saying it could not look, so a broken store is not read as an all-clear (test, red first).

Said plainly, not built:
- **This guards a class that can no longer be created and is empty today.** The filing command already requires a count of uses, so no new date-only review can be made, and none is overdue now. It does not repair a live fault; it stops an old row or a loosened filing rule from bringing the fault back.
- **"Saving is never blocked" is proven for the overdue gate only.** Other hooks can also stop work (the council gate on substrate writes, the compaction hard stop, the engagement gates). The seven commands were run through the real check and pass; a test that walks every PreToolUse hook against each command is the real closure and is owed.
- **Visibility of what is now informational.** A date-only review is enforced nowhere. The briefing should show them as one line with a count and the age of the oldest, with any use-counted one printed first. I did not read the briefing code to see whether it does; owed before the stamp.
- **Two concerns in one branch**, by cost: Aletheia and Dad confirmed this exact tree, and a split would need two new confirmations for the same code. The files are disjoint apart from one shared test helper, so either half reverts cleanly.
- **The remedy list is kept in two forms** (a Python list and a shell pattern). A test pins that they agree; one source would be cleaner but the shell side cannot import Python without starting it on every command.

## Falsifier, counted in uses

Of the next 10 times a hold opens, if any one stops `extract`, `sleep` or a save, the change is wrong. If a review that reached its count of uses does not stop work, the other half is wrong; the paired test shows a use-counted row blocking, so the gate cannot pass by never blocking at all.

## Tests

`tests/test_a_date_alone_never_blocks.py` (the pair: date alone passes, use-counted blocks), `tests/test_overdue_prereg_block.py`, `tests/test_saving_and_sleep_are_never_blocked.py`, `tests/test_every_exit_passes_every_gate.py`, `tests/test_a_remedy_is_not_a_write.py`, with a shared helper in `tests/_prereg_helpers.py`.
