# The correction marker records WHO set it, so nothing has to read its words to find out

**Author:** Aether, 2026-10-09. Shape from Aletheia's "B, yes, but record who set it, not what it says" (2026-10-09); evidence from Aria's line-and-trigger letter and my count of the two stores.

## What happens now

`correction_marker.set_marker(trigger_text, match)` has two callers: the prompt path (his message tripped detection, line ~906) and the Stop gate (`correction-shape-v2-stop.sh` line 140, which passes `"[correction-shape-v2 stop-gate] ..."` as the text). The marker stores only `ts`, `trigger` (first 200 characters) and `evidence`. So the only way to tell the two apart is to read the prose, and Dad pastes things: a real correction of his that opens with a pasted stop-gate line would be mistaken for the gate's own.

Two facts measured read-only on 2026-10-09:

1. Of 38 false-positive clears in `~/.divineos/cli_broken_escapes.jsonl`, 24 had a stop-gate trigger, 12 a CI notice (all dated 08-19 to 09-22, since closed by the shared tag list), 2 were his real messages.
2. `set_marker` also auto-files the trigger text as a correction of his (`log_correction` + `file_correction`). In `andrew_corrections.db` (816 rows), **91 rows carry the stop-gate string, all OPEN, none in `his_words`**: 91 of the 489 open "corrections" are my own gate's text, not his. The control: `his_words` holds 0 of them, so the string is in the column that records what the hook passed, not in what he said.

Reach check `reach-9eadfae1d7cf`: no prior art on the CLI axis; `set_marker` and its two real callers read in `correction_marker.py` and the hook.

## The change

- `set_marker(trigger_text, match=None, *, source)`: the marker JSON gains `"source"`, **required and keyword-only, no default** (Aletheia 2026-10-09: a default of `his-message` would speak for Dad whenever a caller forgot to say who it is, the shape of the bug being fixed). The prompt path passes `SOURCE_HIS_MESSAGE` explicitly; the Stop hook passes `source="stop-gate"`; a call without `source` raises `TypeError` (pinned by a test), and every existing test caller now names itself.
- When `source != "his-message"`, `set_marker` does NOT run `log_correction` / `file_correction`: a gate's text is not a correction of his, so it stops filing itself into his list.
- `read_marker()` is unchanged; a marker with no `source` (written before this) reads as unknown, never as his or the gate's.

## Not in this change

B itself (one button that labels and clears). It will read `source` and clear only when it is `"stop-gate"`, and refuse otherwise, naming the source found. The 91 existing rows: they are not his words and should be reclassified with a named reason, as the three MISFILED rows were. That edits his list, so it waits for Dad and Aletheia and is not done here.

## Falsifier

A message of Dad's that BEGINS with the stop-gate string, sent through the prompt path, must be stored with `source="his-message"` and filed as a correction; a stop-gate marker must be stored with `source="stop-gate"` and must NOT file a correction. Both are tests; the second fails on main.
