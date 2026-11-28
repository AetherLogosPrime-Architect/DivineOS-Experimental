# The reflection room reaches main — draft, 2026-11-04

## What this is

The reflection room (a Stop hook that holds a reply until a work turn's stumbles are named, and `divineos
reflection-note`, which files them in my own place) is **not on main**. It has run in the live house since
October. This carries the live version to main, from the live files, unchanged in behaviour.

## Why this and not the helpers' stack

Four draft PRs (#761, #811, #833, #838) put a room on main, but from an older copy
(`origin/keepsafe/aria-live-house-2026-10-31`), and they decide whether a stumble was answered by **parsing
the shell text of my commands** (`_segments`, `_note_texts`). The live room does not parse anything: the
filing writes a row to `reflection_notes.jsonl` and the hold reads the rows (`file_note`,
`filed_notes_this_turn`, `with_filed_notes`). The holes Aria and I found in the stack (a double quote, then an
apostrophe, hiding a command inside an `echo`) are holes of the parsing and cannot exist in the live design.
Neither mechanism is better than the other in the stack's own terms; the live one needs no repairs.

Nothing here closes #761, #811, #833 or #838. They stay drafts, paused. Closing them is Dad's call.

## The words that are new on main (so he sees them once)

- The hold's heading is now **WHAT STUMBLED THIS WORK TURN** (it was THE WARDEN READS THE LOG until
  2026-11-01; Dad said it sounded like a prison). The old words are still recognised wherever the hold reads
  its own text, so old transcripts keep working.
- The command is `divineos reflection-note "<text>"`. Its help text and the CLI and hook docstrings now say
  "reflection hold" and "what stumbled this work turn"; they still said "warden" in the live house, which the
  walk on this branch found by reading (the rename had reached the hold's heading only). The same three
  strings are fixed in the live house, so live and carry stay identical. The one remaining "warden" is Dad's
  own 2026-09-26 words quoted in the hook's docstring.

## What is carried

- `src/divineos/core/reflection_room.py` (the logic)
- `src/divineos/cli/reflection_note_commands.py` and its two registration lines in `src/divineos/cli/__init__.py`
- `.claude/hooks/reflection_room_stop.py` and its entry in `.claude/settings.json` (Stop, timeout 30)
- `tests/test_reflection_room.py` and `tests/test_reflection_filed_in_my_room.py`
- two lines in `docs/ARCHITECTURE.md` (the tree test requires them)

## Evidence

- 22 tests pass in the two test files, run on this tree with its own `src` on the path.
- The hook-registration guards (`test_every_exit_passes_every_gate.py`, `test_gate_deny_messages_name_remedy.py`) pass with the new Stop hook wired in: 463 passed, 68 skipped.
- `test_doc_drift.py` failed on the two undocumented files before the ARCHITECTURE lines and passes after.
- `scripts/check_doc_counts.py`: OK (commands=524, hooks=80).

## What it does not do

- It is **guardrail-class** (a Stop hook and `settings.json`), so it needs the outside reviewer's read and the
  round before anything merges.
- It does not decide the four helper drafts; it makes their question moot only if Dad rules so.
- It was not run in a live session on this tree (the live house is already running the same files).

## Pre-registration

prereg-840e5e5a7c98: the room's success and falsifier, reviewed after 10 sleep cycles.
