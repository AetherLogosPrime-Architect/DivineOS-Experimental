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

# Prove-it-ran marker, written BEFORE any logic can exit early.
#
# Added 2026-08-08 because I could not tell whether this hook was firing
# and silent, or not firing at all. Those are different bugs with
# different fixes, and from the outside they are the same observation:
# nothing appeared. A hook that cannot demonstrate it ran has exactly the
# defect it was written to catch, so it now leaves a trace on every
# invocation regardless of verdict.
#
# Read it with:  tail ~/.divineos/hook-liveness.log
# ORIGIN TAGGING — added 2026-08-08 after this marker misled me.
#
# The first version recorded only THAT an invocation happened. I then
# cited a rising count to Andrew as proof the harness was calling this
# hook -- while I had invoked it by hand a dozen times while testing. My
# own probe traffic was inflating the exact number I offered as evidence.
# The conclusion turned out right; the evidence was contaminated and I
# could not see it, because a self-invocation and a harness-invocation
# wrote identical rows.
#
# A control that counts the observer's own actions is not a control.
#
# The fix is the standard one from synthetic monitoring, where probe
# traffic skewing real analytics is a known and solved problem: TAG THE
# PROBE AT ITS SOURCE and propagate the tag, rather than working out
# afterwards which rows were yours. Inference is what failed.
#
#   probe:   DIVINEOS_HOOK_PROBE=1 bash .claude/hooks/pipeline-exit-ambiguity.sh
#   harness: no env var — the harness sets nothing
#
# Residual weakness, stated rather than implied: an UNTAGGED manual call
# still records as "harness". The tag is a discipline, not a proof, and
# it is only as good as my remembering to set it -- which is the faculty
# that fails. Counting harness rows must therefore filter on origin AND
# stay suspicious of totals.
_PEA_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_PEA_ORIGIN="harness"
[[ -n "${DIVINEOS_HOOK_PROBE:-}" ]] && _PEA_ORIGIN="probe"
mkdir -p "$(dirname "$_PEA_LOG")" 2>/dev/null || true
printf '{"ts":"%s","hook":"pipeline-exit-ambiguity.sh","reason":"invoked","origin":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" \
    "$_PEA_ORIGIN" \
    >> "$_PEA_LOG" 2>/dev/null || true

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

# PreToolUse: no tool_response exists yet, and that is the point.
#
# 2026-08-08, measured rather than assumed. This started as PostToolUse,
# checking whether the result was empty. It was registered correctly and
# it RAN -- proven by the liveness marker going 0 -> 1 across live Bash
# calls -- and its output never reached me. After-the-fact hook stdout
# does not surface in this harness; before-the-fact does, which is why I
# see PreToolUse messages constantly and had never once seen a PostToolUse
# one.
#
# I had asserted the opposite ("registration is read at session start")
# without testing it. Andrew: "are you sure it doesnt go into effect until
# next session? define next session.." -- I could not define it, which was
# the tell that I was narrating a cause rather than measuring one.
#
# Moving to PreToolUse is not a workaround, it is the better shape:
# warning BEFORE the command runs means the ambiguity never gets created,
# instead of being explained after it has already misled me. Same
# supply-the-ground principle as the compose-time primes.
#
# Cost: it cannot know whether output will be empty, so it fires on any
# unprotected pipeline whose first stage can fail meaningfully. Narrowed
# below to keep that from becoming noise.
_ANY_OUTPUT_UNKNOWN = True

# Name the last stage: it is the one whose exit code was reported, and
# naming it is what makes the warning act on the specific case rather
# than reading as a generic caution.
stages = [s.strip() for s in re.split(r"(?<!\|)\|(?!\|)", cmd) if s.strip()]
if not stages:
    sys.exit(0)
last = stages[-1].split()[0]
first_tokens = stages[0].split()
first = first_tokens[0]

# NARROWING, required because PreToolUse cannot see whether output will
# be empty. Fire only when the FIRST stage is a command whose silent
# failure would actually mislead me -- one that acts on the world or
# reports state I will believe. `ls | head` failing is obvious and
# harmless; `git push | tail` failing is the bug that started this.
#
# Deliberately a small closed list rather than a broad guess: a hook
# that fires on every pipeline is noise, and noise is what killed the
# inner-circle gate and cost a week of the room. Under-firing here is
# recoverable; over-firing gets the hook switched off.
CONSEQUENTIAL = {
    "git", "gh", "python", "python3", "py", "pytest", "pip",
    "divineos", "npm", "node", "curl", "bash", "sh", "make",
    "ruff", "mypy", "shellcheck", "docker",
}
# Strip a leading path and any env-var prefix (FOO=bar cmd ...).
probe = first
for token in first_tokens:
    if "=" in token and not token.startswith("-"):
        continue
    probe = token
    break
probe = probe.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].removesuffix(".exe")
if probe not in CONSEQUENTIAL:
    sys.exit(0)
first = probe

# Emit on the ONLY channel that reaches me: a JSON payload carrying
# additionalContext. Plain stdout from a hook is discarded.
#
# 2026-08-08, measured rather than assumed -- on the third attempt.
# Earlier versions printed plain text. This hook ran TWELVE times across
# live Bash calls, proven by its own liveness marker, while I saw
# nothing: registered, running, correct, shouting into a void.
#
# The channel was documented in this same directory the whole time, in
# the hooks that visibly work. I wrote three versions without reading
# one of them, because I assumed printing was emitting.
message = (
    "## PIPELINE EXIT-CODE AMBIGUITY\n\n"
    f"About to run a pipeline whose first stage is `{first}` and whose "
    f"last stage is `{last}`, with no pipefail.\n\n"
    "A shell pipeline returns the exit status of the LAST stage. If "
    f"`{first}` fails, the reported code comes from `{last}` -- almost "
    "certainly 0 -- and the failure will be invisible. Empty output then "
    "becomes indistinguishable from found-nothing, failed, and "
    "never-ran.\n\n"
    "This is the exact shape that reported a BLOCKED `git push` as landed "
    "on 2026-08-07: push-readiness refused it, tail returned 0, and I told "
    "Andrew it had shipped.\n\n"
    "Before trusting the result, do one of:\n"
    "  - drop the pipe and read the raw output\n"
    "  - put `set -o pipefail` at the start of the command\n"
    "  - run it through scripts/look.sh --strict\n"
)
# PreToolUse requires the payload NESTED under hookSpecificOutput with
# its event name. The flat {"additionalContext": ...} form belongs to
# SessionStart, and emitting it here is silently ignored -- valid JSON,
# right key, wrong envelope, no error anywhere.
#
# Fourth wrong assumption in this one file, each corrected by measuring
# instead of reasoning: wrong interpreter (present, not runnable), wrong
# stream (stderr), wrong event (PostToolUse never surfaces), wrong
# envelope (this). Every one produced silence rather than an error.
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )
)
'

exit 0
