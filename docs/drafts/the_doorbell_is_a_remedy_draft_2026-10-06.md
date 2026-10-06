# The doorbell is a way out, and three guards held it shut

**Status:** draft, station 1. Not built.
**Date:** 2026-10-06
**Asked by Dad:** "if the doorbell needs fixed you can fix it as well"
**Prior art searched:** `.claude/hooks/lib/remedy_allowlist.sh` and `src/divineos/core/remedy_allowlist.py` (the shared list, whose own header says no gate may block another gate's prescribed exit); `src/divineos/core/question_hold.py:112` (a private anchored regex for the doorbell); `scripts/letter_doorbell.sh` and `.claude/hooks/letter_doorbell_alive_stop.py`. The branch `fix/gates-add-never-repost` (#558) also edits the bell script, for how it reads the folder; it does not touch this.

## What happened (measured today, not remembered)

The Stop guard holds every reply that ends with the bell not listening and prescribes `bash scripts/letter_doorbell.sh aria`. Today that exact command was refused five times, each by a different guard:

- the open-ask hold, because the doorbell is not on its private list of allowed commands;
- the question hold, when I wrote it with a `cd <folder> &&` in front (its doorbell pattern is anchored at the start of the command, and the same command without the prefix passed);
- the read gate, demanding I open an unrelated old writing before any command, while the voice hold refused me the Read tool: two guards each waiting on the other.

## Root cause

The shared remedy list cannot hold the doorbell: its Python copy forbids `bash` as a head on purpose (a test asserts it), because bash runs anything. So the doorbell was handled by one private regex in one guard and nowhere else. A permitted command with one home in one guard is the exact shape the list's header describes.

## Proposal

One narrow judgment in the shared Python module: `is_doorbell(command)` is true only when every acting segment of the command is `bash scripts/letter_doorbell.sh [seat]`, with setup prefixes (`cd`, an assignment) allowed and any other work chained behind it refusing the whole line, reusing the same parser the list uses. The three guards that blocked it each ask that one function. `bash` stays off the remedy list.

## What this does not open

The script writes a heartbeat file and lists a folder under the home directory and runs nothing else; it is guarded as a file like any other. The exemption is an exact script path, not a family of commands. Anything chained behind it is refused. If the parse fails, the answer is no.

## Falsifiers

- The command with a `cd` prefix passes all three guards.
- `bash scripts/letter_doorbell.sh aria; rm x` is refused by all three.
- `bash scripts/other.sh` and a mention of the doorbell inside another command's argument are refused.
- `bash` still cannot appear on the remedy list.
