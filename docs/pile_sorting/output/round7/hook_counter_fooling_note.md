# Reading the hook-counter fix, and scripts that would fool it

*Round seven, errand five. 2026-10-08, cloud helper. Read-only: I read the change on `aria/the-hook-counter-reads-code-not-comments` (commit `2069dc1d`, three files: `src/divineos/core/hook_layer.py`, `tests/test_hook_layer.py`, and a draft) and ran its counter on made-up scripts in scratch folders. Nothing in the repository was changed.*

**A picture.** The counter is a clerk who sorts the hook scripts into two piles: "talks to the main system" and "never does". Round five showed the clerk was wrongly putting ten scripts in the second pile, because the clerk did not know one way of talking (`python -m divineos.x`). Aria's change teaches the clerk that way, and also tells the clerk to ignore any line that starts with `#`, because a comment saying "run divineos briefing" is talk, not a call. I tried to fool the clerk with scripts that cheat in each direction.

## What the change does

- Adds `\s-m\s+divineos\b` to the "calls the OS" pattern, so the ten module-form scripts are no longer detached.
- Throws away whole-line comments (lines whose first non-space character is `#`) before looking. Its own comment says trailing comments stay on purpose, and that the choice "errs toward attached".
- Adds two tests: a `python -m divineos.hooks.some_hook` script is not detached (with a control that a plain `echo` script stays detached), and a script whose only mention of the OS is in comments is detached while one that really calls it is not.

I ran the branch's counter on the branch's own hooks folder: 38 of 146 shell files detached. None of the ten module-form scripts is on the detached list, and the two scripts that round five found attached only through a comment (`continuity-frame-prime.sh`, `log-session-end.sh`) are now on it. The change does what it says.

## Scripts that fool it

Each row was run through the branch's `inventory()` in a scratch folder. Controls first: a real module call reads attached, a script with no call reads detached, a script whose only mention is a whole-line comment reads detached (all three behaved).

| Case | What the script is | Truth | Counter says |
|---|---|---|---|
| F1 | prints a hint: `echo "hint: run divineos briefing first"` | detached | **attached** |
| F2 | a "comment" written as a here-document to the no-op command: `: <<'NOTE'` … `divineos briefing` … `NOTE` | detached | **attached** |
| F4 | a trailing comment: `echo hello  # divineos briefing` | detached | **attached** |
| F8 | not the OS at all: `grep -m 1 divineos notes.txt` | detached | **attached** |
| F3 | dead code: `if false; then divineos briefing; fi` | arguable | **attached** |
| F5 | a real call with the module name in quotes: `"$PYTHON_BIN" -m "divineos.hooks.x"` | attached | **detached** |
| F6 | a real call with no space: `"$PYTHON_BIN" -mdivineos.hooks.x` | attached | **detached** |

The cases that read correctly: a `#`-looking line inside a Python here-document (F9) is correctly dropped, and `/usr/local/bin/divineos briefing` (F10) is correctly attached.

### The short example that fools it toward "attached"

```bash
#!/bin/bash
# this script never touches the main system
echo "to debug, run: divineos briefing"
exit 0
```

The comment line is dropped, and the `echo` line still matches `divineos briefing`, so the file is counted as attached. Two files in the repository are in this state today (below).

### The short example that fools it toward "detached"

```bash
#!/bin/bash
exec "$PYTHON_BIN" -m "divineos.hooks.front_door_hook"
```

A real call, counted as a stranger to the system, because the quotes break `-m divineos`.

## Real scripts that are already fooled

Reading the branch's hooks folder I found two that are counted attached on the strength of a sentence of prose and nothing else:

- `.claude/hooks/check-cleanup-period.sh`, line 111: inside a message, the text `` \`divineos extract\` ``. The script uses plain `python -c` to read a settings value and never imports or runs the OS.
- `.claude/hooks/hedge-suppression-prime.sh`, line 233: inside a message, the text `` `divineos recall` ``. The script finds a Python through the OS's helper but does not call the OS.

I read the matching lines in both files; I did not run either script. Both would flip to detached if the counter ignored message text, so the fix as written still overstates "attached" by at least these two. (It says so itself: it errs toward attached.)

## What I think this means, and what I do not

- The fix removes the large error (ten scripts) and leaves small ones that go in both directions. Of the seven fooling cases, five push toward attached (the direction the author chose on purpose) and two (quoted module name, no space after `-m`) push toward detached, which is the direction the author did not intend. The quoted form is an easy thing for a future script to write.
- A real fix for the message-text cases needs something that understands quotes, which the author already says is "a parser's job". I recommend nothing; this note only lists the cases.
- I did not test a `-m divineos` that sits at the very start of a line with nothing before it; the pattern asks for a whitespace character first.

## What I could not do

- I did not run the 38 detached scripts one by one to check each is truly detached. I counted what the counter says.
- I did not run the two tests the change adds against my made-up scripts; I read them.
- I did not test Windows line endings or PowerShell hooks (the counter only reads `*.sh`).
- The two real files are a reading of two lines each, not a run.
