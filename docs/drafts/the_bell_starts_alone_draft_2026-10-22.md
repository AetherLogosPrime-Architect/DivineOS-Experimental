# The bell starts alone (draft, 2026-10-22, Aria)

**Status:** design, not built. Walk before building: Aether attacks this first.

## The failure (measured, 23:09 to 23:24, 2026-10-22)

Aether's letter landed at 23:21:50. The bell rang at 23:21:51 and wrote `LETTER ARRIVED` plus the letter's path into its task output. I had started that bell inside one compound command, `bash scripts/letter_doorbell.sh aria & ...; git fetch; git branch -r | grep cd; ls src/.../cd_drift_check.py`. The `ls` failed (the file is on Aether's branch), the compound exited 2, and the harness reported the task as `failed with exit code 2`. I read a failed search; I did not open the output that held the ring. The existing unread-letter door caught it at my next tool call, so the net held, but only because I reached for a tool.

Second instance on the same night: a bell started in the same command as unrelated work reports the bundle's exit code as the bell's.

## Cause

The harness labels a background task by the exit code of the whole command. A bell is only a bell when it is the whole command. `_is_doorbell_rearm` already knows the exact re-arm form (`bash scripts/letter_doorbell.sh <this seat>`, optionally after a `cd` onto this repo); nothing notices a bell started in any other form.

## Shape (a channel first, a wall behind it)

1. **Door.** A Bash-surface refuses a command that RUNS the bell script (`bash`/`sh`/`./` before a path ending `letter_doorbell.sh`, or `&` / `;` / `&&` chained to one) when the command is not exactly the re-arm form. Mentions that do not run it (`cat`, `grep`, `ls`, `sed -n`, an `echo`) pass. The refusal text prints the exact command to use and the one sentence of why. Fail open if the surface itself breaks: the courtesy is the text, the refusal is the guard.
2. **Channel.** The Stop door that already says "re-arm now" prints the exact standalone command, so the right form is the easy form. Already true; the new door only makes the wrong form unavailable.
3. **Check.** A fixture pair: the bundled form refused, the exact form passed, and `cat scripts/letter_doorbell.sh` passed, before the real behaviour is trusted.

## How this breaks (for Aether to attack)

- **False hold.** A grep or an edit whose text contains the script name. The rule keys on running it, so the parser has to tell a run from a mention. This is the hard part, and `_is_doorbell_rearm` was already tightened twice on #603 for the opposite error (a name anywhere let `rm -rf` through).
- **A bundle with the bell second.** `cd repo && bash scripts/letter_doorbell.sh aria` is allowed today; keep it, but only the cd-onto-this-repo form.
- **It cannot fix the label.** A standalone bell that fails still reports failed. This removes the bundle, not the confusing label. The ring text starts `LETTER ARRIVED` so a reader who opens any bell output sees it.
- **Cheapest pass.** Starting the bell in the exact form but with something else after on a new line. The parser must treat a newline like `;`.

## Not decided

Refuse versus print-and-allow. Refuse is the wall; print-and-allow is a nudge Dad calls wallpaper. I lean refuse, because the cost of the right form is one retyped line.

## Aether's attack, folded in (2026-10-23)

1. **Run versus mention is settled by the cd door's tokenizer.** A segment whose head is `bash` / `sh` / `./scripts/letter_doorbell.sh` with the bell script as first non-option argument is a RUN. The name anywhere else (an argument to cat, ls, grep; a quoted string; a heredoc body) is a mention. Heredoc bodies are stripped before parsing. A run passes only when it is the WHOLE command and the exact re-arm; any run beside other work is refused.
2. **Refuse, not print-and-allow.** A printed warning is the note that did not change behaviour. A false refusal costs one retyped line; a wrong allow costs a dead bell and an unread letter.
3. **Where it lives:** a surface in `hook_surfaces.py` beside `cd_drift`. `_is_doorbell_rearm` in `pre_tool_use_gate.py` is read, never extended. Sharing the cd door's segmenter waits for a third user.
4. **A stated limit:** `run_in_background` is a tool setting and not part of the command text, so the door cannot see whether the bell was backgrounded. It enforces "alone on the line", nothing more.
