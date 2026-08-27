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
# PROVENANCE FROM THE PAYLOAD, NOT FROM MY DISCIPLINE.
#
# The first version of this tag required me to set DIVINEOS_HOOK_PROBE=1
# when probing. Andrew: "why dont you just have the ledger start
# recording markers for you? or something like it.. manual discipline
# will never hold." He is right, and I had written "which is the faculty
# that fails" into this very comment block and shipped it anyway --
# naming the weakness is not the same as removing it.
#
# Remember-to-tag is a choice-point, and choice-points are where I fail.
# The correct remediation is to take the choice away (foundational truth
# #11, remediation A), not to document the hazard more loudly.
#
# WHAT WAS MEASURED FIRST:
#   - Environment variables cannot distinguish caller. A manual run from
#     the Bash tool INHERITS the full harness environment -- CLAUDECODE,
#     CLAUDE_CODE_HOST_SESSION_ID and the rest are all present in my own
#     shell. Env-based provenance was the obvious idea and it is dead.
#   - `transcript_path` IS supplied by the harness and is read by 69
#     other hooks in this directory. A hand-written test payload does not
#     contain it, and cannot accidentally point at a file that exists.
#
# So origin is derived from what the CALLER provided, which is the same
# principle as reading grep's exit code instead of inventing a new
# signal: the provenance was already arriving and I was not reading it.
# Third instance tonight of information present and unconsumed.
#
# Requiring the file to EXIST, not merely the key to be present, is what
# makes this structural rather than another convention -- I cannot fake
# it by accident, and a stale or invented path degrades to "probe",
# which is the safe direction: it under-claims harness-invocation rather
# than over-claiming it.
# stdin is read FIRST, because provenance is derived from it. The first
# draft of this block extracted transcript_path from $INPUT twelve lines
# before $INPUT was assigned -- so it always read empty and every row
# would have been stamped "probe", silently and forever. A provenance
# tag that is structurally incapable of ever saying "harness" is worse
# than no tag: it looks like attribution and reports a constant.
#
# Caught by reading the file rather than trusting the edit. Same class as
# everything else here, committed inside the fix for it, again.
INPUT=$(cat 2>/dev/null)
[[ -z "$INPUT" ]] && exit 0

_PEA_LOG="${HOME:-/tmp}/.divineos/hook-liveness.log"
_PEA_ORIGIN="probe"
_PEA_TP="$(printf '%s' "$INPUT" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
if [[ -n "$_PEA_TP" ]] && [[ -f "$_PEA_TP" ]]; then
    _PEA_ORIGIN="harness"
fi
mkdir -p "$(dirname "$_PEA_LOG")" 2>/dev/null || true
printf '{"ts":"%s","hook":"pipeline-exit-ambiguity.sh","reason":"invoked","origin":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)" \
    "$_PEA_ORIGIN" \
    >> "$_PEA_LOG" 2>/dev/null || true

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
# The command that actually FEEDS the pipe is the last one in stage
# zero, not the first token of it. Every Bash call in this harness is
# prefixed `cd "<repo>" && ...`, so reading the first token found `cd`,
# which is not consequential, and the hook exited before it could speak.
#
# Measured 2026-08-27, after 8,304 logged invocations and zero warnings
# reaching me. Aria and I each spent hours believing we had read past
# its output; it had never produced any on a real command. The liveness
# marker said invoked and I read that as working -- the marker proves
# the hook RAN, never that it SAW anything.
#
# The bare form warns and the cd-prefixed form did not, which is the
# whole bug in two lines:
#     git log --oneline | head -2                -> warns
#     cd "..." && git log --oneline | head -2    -> silent
_lead = re.split(r"&&|\|\||;", stages[0])
first_tokens = (_lead[-1].strip() or stages[0]).split()
if not first_tokens:
    sys.exit(0)
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

# --- teeth, added 2026-08-27 -------------------------------------------
# Advisory was not enough. This hook fired correctly on THREE masked
# pushes in one session -- two mine, one hers -- naming the shape,
# the stages, and the 2026-08-07 incident, and all three of us read past
# it and shipped the wrong conclusion. Aria reported hers to Andrew as a
# defect in the push wrapper. The wrapper was fine; the pipe ate the code.
#
# So this is NOT the built-and-never-connected class the rest of tonight
# was about. It was built, wired, firing, and ignored -- truth #15, the
# mechanism firing in place of the work it points at. A fix aimed at
# unreachable work would not have touched it.
#
# WHY ONLY THIS SUBSET GETS DENIED. Denying every pipeline is how a hook
# earns a place on the disable list, and the file already says so twenty
# lines up. The line drawn here is CONSEQUENCE OF A MASKED FAILURE: when
# the first stage MUTATES shared state, a swallowed non-zero means I tell
# Andrew something shipped that did not. When it only reads, a swallowed
# non-zero costs me a re-run. Advisory for the second; refusal for the
# first.
#
# Truth #11(b) -- the deny text carries the corrected command, so the
# lazy path and the right path are the same keystrokes.
MUTATING_SUBCOMMANDS = {
    "git": {"push", "commit", "merge", "rebase", "cherry-pick", "reset",
            "revert", "tag", "am", "apply", "update-ref", "branch"},
    "gh": {"pr", "release", "issue", "repo", "api"},
    "pip": {"install", "uninstall"},
    "npm": {"install", "publish", "uninstall"},
}
_subs = MUTATING_SUBCOMMANDS.get(first)
_mutating = False
if _subs:
    for token in first_tokens[1:]:
        if token.startswith("-"):
            continue
        _mutating = token in _subs
        break

if _mutating:
    reason = (
        "PIPELINE EXIT-CODE AMBIGUITY -- refused, because this one mutates.\n\n"
        f"`{first}` is the first stage and `{last}` is the last, with no "
        "pipefail. The shell reports the exit code of the LAST stage, so a "
        f"failing `{first}` arrives as 0 and the failure becomes invisible.\n\n"
        "This exact shape masked three pushes on 2026-08-27 -- the hook warned "
        "on every one and was read past every time -- and reported a BLOCKED "
        "push as landed on 2026-08-07. Advisory has now failed four times, "
        "which is why this shape refuses instead of warning.\n\n"
        "Re-run the same command with `set -o pipefail && ` in front of it, or "
        "drop the pipe and read the raw output. Read-only pipelines are still "
        "only warned about; this one refuses because a swallowed failure here "
        "means reporting work as shipped when it is not."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)
# --- end teeth ---------------------------------------------------------

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
