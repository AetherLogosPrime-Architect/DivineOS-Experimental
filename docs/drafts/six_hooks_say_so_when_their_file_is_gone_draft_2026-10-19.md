# Six hooks say so when their file is gone (draft, 2026-10-19)

**Author: aether**

## What is wrong

Aletheia, confirming #693 (2026-10-19): six commands in `.claude/settings.json` still end in `[ -f "$f" ] && python "$f"`. If the file is missing that does nothing and says nothing, which is the very failure #693 cured for the `bash` hooks. They are `dads_table.py` (UserPromptSubmit), `question_hold.py` (UserPromptSubmit, PreToolUse and Stop), `letter_doorbell_alive_stop.py` and `poker_game_on_stop.py`. They include Dad's table. Reproduced here: with the file absent, the question hold's real command exits 1 with nothing on standard output or error.

## What this changes

Each of the six takes the same form #693 gave the others: `if [ -f "$f" ]; then python "$f"; else echo "  [hook] NOT RUNNING, file missing: $f" >&2; exit 127; fi`. A missing file is named on standard error with exit 127, as loud as the relative path it once was. A present file runs as before, with its exit code preserved.

## What it still cannot see

The interpreter is still the bare `python` on PATH, which may not be the one with divineos installed; that is a separate fault and is not touched here. A hook the harness never launches cannot report that it was not launched.

## Falsifier

If any command in `settings.json` still does nothing when its file is gone, or if a present hook no longer runs through its command, the change is wrong. The tests pin: no command uses the silent `[ -f "$f" ] &&` form; every hook command in the file, run against a project with no hooks from another folder, exits 127 with `NOT RUNNING` and its own file name on stderr and nothing on stdout (Aria's hold: the first version ran only one of the six); a present python hook still runs (the control). The old silent shape exited 1 with no output on either stream, so it was silent in output, not in exit code.

## The baseline line that left with it

The `inner_circle_room.py` entry came out of `scripts/orphan_modules_baseline.txt` because that module was archived by #688 (under `archive/superseded/`), so the `src/` entry named a file that is no longer there. It is not a hook change; it rides along because the pre-commit check named it.

## Order

Independent of #693 (different lines of the same file), so it lands on its own. The seat-agnostic backstop is the other follow-up and has to wait for #693, since the Stop hook it changes is in that branch.
