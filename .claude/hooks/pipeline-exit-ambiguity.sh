#!/bin/bash
# PostToolUse(Bash) — say so when a result cannot distinguish
# "nothing found" from "the command failed".
#
# WHY THIS EXISTS (2026-08-08)
#
# Andrew: "wiring it in is the entire point and not wiring things in is
# why were in this mess.. so decide now lol" — said after I built
# scripts/look.sh, verified it against the real failure, and then left it
# standalone while calling that deliberate. Same day I had found three
# separate mechanisms that were built, correct, and connected to nothing.
# This is the wire.
#
# THE FAILURE IT CATCHES, measured at the tool boundary the same night:
#
#   command that did nothing        -> (Bash completed with no output)
#   search that found nothing       -> (Bash completed with no output)
#   search whose failure a pipe ate -> (Bash completed with no output)
#   search that failed, exit intact -> <error>Exit code 2</error>
#
# The harness surfaces a non-zero exit when one survives. A pipeline
# destroys it first: a shell pipeline returns the exit status of the LAST
# stage, so `git push ... | grep -v ^remote: | tail -6` reports tail's
# success no matter what git did.
#
# That is not hypothetical. It happened: a `git push` was BLOCKED by the
# push-readiness gate ("tests failing (exit 10)"), the pipeline reported
# exit 0, and I told Andrew the push had landed. It had not. Only
# checking the remote by hand found it.
#
# WHAT IT CANNOT DO, stated rather than implied: this hook runs AFTER the
# command. It cannot recover the true exit code — that information was
# destroyed by the pipeline before the result was produced. It can only
# say the result is UNTRUSTWORTHY. That is the honest limit, and saying
# "I cannot tell" is exactly the third state this whole class needed.
#
# WHY IT IS NARROW: it fires only when the exit code is genuinely
# unrecoverable AND the output is empty — the precise case where silence
# is indistinguishable from failure. A hook that fired on every pipeline
# would be noise, and noise is what kills mechanisms in this house; the
# inner-circle gate died that way and cost a week of the room.
#
# Fail-open: any error exits 0 silently. A broken watchdog must not block
# work — though note the irony, and that this is why the emit below is
# unconditional-on-detection rather than conditional-on-a-second-check.

INPUT=$(cat 2>/dev/null)
[[ -z "$INPUT" ]] && exit 0

# Interpreter resolution via the shared helper, NOT `command -v`.
#
# The first draft of this file picked its interpreter with `command -v
# python3`, which succeeded and then failed to run: on this machine that
# path is the Microsoft Store alias stub, which is present on PATH and
# prints "Python was not found" instead of executing.
#
# So the hook written to catch presence-mistaken-for-function made
# exactly that mistake inside itself, on its first test. Recording it
# here rather than quietly fixing it, because the file's whole claim is
# that this class is invisible from the inside — and it was.
#
# find_divineos_python resolves an interpreter that actually runs; the
# same fix was applied to the ritual failsafe earlier the same session
# for the same reason.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PY="$(find_divineos_python 2>/dev/null)" || exit 0
[[ -z "$PY" ]] && exit 0

# shellcheck disable=SC2016  # single quotes are deliberate: this is a
# Python program, and shell must NOT expand $-anything inside it.
printf '%s' "$INPUT" | "$PY" -c '
import json, re, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

cmd = ((data.get("tool_input") or {}).get("command") or "")
if not cmd:
    sys.exit(0)

# A real pipeline, not a logical-or and not a pipe inside quotes-only.
# Strip || first so `a || b` never counts as a pipeline.
stripped = cmd.replace("||", "")
if "|" not in stripped:
    sys.exit(0)

# Already protected: the author asked for the real exit code.
if "pipefail" in cmd or "PIPESTATUS" in cmd or "look.sh" in cmd:
    sys.exit(0)

# Response shape varies by harness version; treat any of these as "the
# output was empty". Unknown shape -> assume NOT empty, so this stays
# quiet rather than crying wolf on a result it cannot read.
resp = data.get("tool_response")
if isinstance(resp, dict):
    out = str(resp.get("stdout") or resp.get("output") or resp.get("content") or "")
elif isinstance(resp, str):
    out = resp
else:
    sys.exit(0)

if out.strip() and "completed with no output" not in out:
    sys.exit(0)

# Name the last stage: it is the one whose exit code was reported, and
# naming it is what makes the warning act on the specific case rather
# than reading as a generic caution.
stages = [s.strip() for s in re.split(r"(?<!\|)\|(?!\|)", cmd) if s.strip()]
last = stages[-1].split()[0] if stages else "the last stage"
first = stages[0].split()[0] if stages else "the first stage"

print(
    "[pipeline-exit-ambiguity] AMBIGUOUS RESULT — do not read this as "
    "\"nothing found\".\n"
    f"  The command is a pipeline ending in `{last}`, and it produced no "
    "output.\n"
    f"  A shell pipeline returns the exit status of the LAST stage, so the "
    f"code you saw belongs to `{last}`, NOT to `{first}`.\n"
    "  Three states are indistinguishable here: found-nothing, "
    "command-failed, command-never-ran.\n"
    "  This is the exact shape that reported a BLOCKED git push as landed "
    "(2026-08-07).\n"
    "  To resolve: re-run without the pipe, or `set -o pipefail`, or\n"
    "    bash scripts/look.sh --strict '\''<command>'\''",
)
'

exit 0
