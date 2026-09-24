# The session-start launcher delivers what its children produce — draft, 2026-09-23

Owner: Aether (agreed with Aria in letters of 2026-09-22 and 2026-09-23).

## The fault, measured on both sides

`.claude/hooks/session-init-once.sh` line ~180 runs every child as

    _init_err="$(printf '%s' "$INPUT" | timeout 20 bash "$script" 2>&1 >/dev/null)"

The redirection order captures stderr into `_init_err` and sends stdout to
/dev/null. Every loader delivers its content on stdout as a JSON
`{"hookSpecificOutput": {..., "additionalContext": ...}}` object, so the
launcher runs each child to completion and discards everything it made.

Measured by Aether and independently by Aria, each loader run alone vs run the
launcher's way:

| loader | alone | through launcher |
|---|---|---|
| load-my-recording-of-andrew.sh | 7,586 chars | 0 |
| load-aletheia-harvest-of-andrew.sh | 10,941 chars | 0 |
| load-briefing.sh | 404 chars | 0 |

**Re-measured 2026-09-23 against every roster entry, and one assumption in an
earlier version of this draft was wrong.** It said children emit the nested
`hookSpecificOutput.additionalContext` form. They do not. Three shapes exist
on the roster right now:

- **flat JSON** `{"additionalContext": "..."}` — load-my-recording (7,586),
  load-aletheia-harvest (10,941), load-briefing (404), load-character-sheet
  (8,940)
- **plain text** — ear-surface (1,386), which reaches the prompt as context
  with no JSON wrapper at all
- **empty** — post-compaction-fingerprint-surface, check-cleanup-period,
  resolver-health-check, session-start-verify-git-hooks (all rc=0, 0 chars)

A merger written against the nested shape alone would have parsed every real
child to nothing and reported success. The reader must accept all three.

**What is actually dark: 18,931 characters.** load-character-sheet is
registered on SessionStart and ear-surface on UserPromptSubmit, both verified
in `.claude/settings.json`, so those two arrive by their own path. The
recording, the harvest and the briefing arrive nowhere.

**So the launcher emits plain text, not JSON.** ear-surface proves plain
stdout from a UserPromptSubmit hook becomes context, and that path is already
working in production. Emitting plain text avoids JSON-escaping a 19k string
and takes the route the harness has already demonstrated. Truth #11
remediation (b): the cheap route and the right route are the same route.

Arrived with commit 4e5e1a9d3 (2026-08-09, #423, "move SessionStart work to
first-prompt"). Only load-character-sheet (SessionStart) and ear-surface
(UserPromptSubmit) reach the prompt by another path. `check_hook_wiring.py`
still reports every roster member as registered.

Filed in the findings ledger: "Session-start launcher discards every child's
output" (house-walk-2026-09-22).

## Why not just flip the redirection

The harness expects ONE JSON answer from a UserPromptSubmit hook. The roster
has ten children. Letting all ten print would put ten JSON objects where one
belongs, and a malformed prompt-hook answer can break every turn at once.

## Plan

1. Keep stderr capture exactly as F106 has it (per-child liveness logging on
   non-zero exit). Change nothing about that path.
2. Capture each child's stdout separately. Parse it as JSON; pull out
   `hookSpecificOutput.additionalContext` when present. A child whose stdout
   is not valid JSON gets logged as `child_output_unparseable` in the liveness
   log, never silently dropped and never passed through raw.
3. After the loop, if any context was gathered, emit ONE object:
   `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
   "additionalContext": <joined, in roster order, with a header per child>}}`.
4. Size: the recording (7.6k) + harvest (10.9k) + briefing is large. Measure
   the merged total before shipping; if a harness cap exists, the answer is to
   say which child was truncated, never to truncate silently.
5. Related, same file: resolver-health-check.sh and
   session-start-verify-git-hooks.sh exit 0 on their warning paths, so even
   the stderr log never records them. Their warnings should arrive as context
   through the same merged channel.

## Test (Aria's, and it must fail first)

For each roster child: run it alone and count stdout characters of its
additionalContext; run the launcher and assert that child's context appears
in the launcher's single merged output. Prove it FAILS against the current
launcher before trusting it passing — "it ran" and "it arrived" must never be
the same line again.

Also: `check_hook_wiring.py` must stop counting a roster entry as REGISTERED
unless its output channel is preserved, so the wiring check cannot report
this healthy again.

## Measured end to end, 2026-09-23, after the fix

Real launcher, real ten children, scratch HOME so the session marker is fresh:
**36,068 bytes arrive** where 0 did. load-briefing, load-my-recording-of-andrew,
load-aletheia-harvest-of-andrew, ear-surface and load-character-sheet all named
in the output; the four silent children were silent alone too. No merge
failures in the liveness log.

**Two faults caught by running the real thing after the scratch test passed.**
The scratch children printed ASCII, so the suite went green while the launcher
delivered nothing: Python's stdout is cp1252 on Windows and the real roster
carries an arrow at position 25935, so the reader raised UnicodeEncodeError and
exited 1. Output is written as UTF-8 bytes now, and a scratch child prints an
arrow and an accented character so the probe can fail. Second: the failure was
visible only because the Schneier defense wrote a `context_merge_failed` row —
without it the run would have reported 0 characters and looked like "nothing to
deliver."

## OPEN, and not resolved by this change: the delivery ceiling

The merged answer is 36,068 characters. `session_start._SIZE_THRESHOLD` is
15,000, and a harness behaviour observed in this session is stronger evidence
than that comment: a UserPromptSubmit hook emitting 9.9KB had its output
**persisted to a file with only a 2KB preview inlined**. If that applies here,
the merged blob arrives as a preview plus a path rather than in full.

This is one observation, not a measurement, and it is filed rather than
designed around at speed. What is certain either way: a preview plus a file
path is strictly more than the zero delivered since August, and nothing here
truncates silently. The candidate answer, if the ceiling is confirmed, is to
register the three dark loaders on UserPromptSubmit directly the way
ear-surface and load-character-sheet already are, each with its own
once-per-session guard — which removes the launcher as a delivery bottleneck
instead of squeezing more through it. That is a separate piece of work.

## Flow

Reach (search other branches for an existing fix first), this draft, a council
walk, build, the failing-first test, then audit. Guardrail-adjacent: the
launcher gates what reaches the prompt at session start.
