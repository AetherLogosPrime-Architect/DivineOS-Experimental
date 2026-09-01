#!/bin/bash
# Cheap relevance bail for hooks whose trigger is a COMMAND, not a tool.
#
# Claude Code matchers select on TOOL NAME only. So every hook that really
# cares about `git push`, `git commit`, or a `gh pr` verb is wired to Bash and
# fires on `ls`, `cat`, and `echo` too -- then sources two libraries, runs git
# rev-parse, starts Python, imports divineos, and only THEN looks at the
# command to discover it was irrelevant. Measured 2026-08-22 on `ls -la`:
#
#     bash startup            45ms
#     source _lib.sh          63ms
#     find_divineos_python   100ms   (spawns git rev-parse)
#     python + import        210ms
#     hook's own logic      ~250ms
#                          ------
#                           664ms   to conclude "not my command"
#
# check-branch-on-push.sh worked this out first and fixed it inline. This is
# that fix extracted, because it was the only hook that had it -- the same
# one-sibling-has-it shape that left two `gh pr` gates carrying a defect the
# third had already fixed.
#
# ON EXTRACTING IT AT ALL. The original decided against a shared helper:
# "a shared helper here would cost more than the thing it records." That is
# true of _lib.sh (63ms) and NOT true of this file. Measured: sourcing this is
# 51ms against a 54ms bare-bash floor -- inside the noise. The premise was
# right about the library it was written beside and wrong as a general rule,
# so the duplication it justified is not needed.
#
# ---------------------------------------------------------------------------
# THE TRAP THIS FILE EXISTS TO KEEP CLOSED
#
# A bail that just `exit 0`s writes NO start row and NO end row, so every cheap
# run vanishes from hook_timing.jsonl. check-branch-on-push.sh got faster --
# 1010ms to 61ms -- and its RECORDED median ROSE by 945ms, because only the
# expensive path survived in the log. Silence read as absence rather than as
# speed.
#
# So the bail RECORDS ITSELF. A quiet path must still be able to say it ran.
# Anyone adding a filter without calling this will make their hook invisible
# and then measure the wrong thing, which is how this was found in the first
# place.
# ---------------------------------------------------------------------------
#
# Pure builtins on purpose: no git, no python, no subprocess. The record has
# to cost less than the work it saves, or it defeats itself.

# hook_bail_and_log <hook-name> <reason>
#   Append a "bailed" row. Does NOT exit -- the caller does, so the exit stays
#   visible at the call site instead of hiding inside a function.
hook_bail_and_log() {
    local hook="$1" reason="$2" ms secs frac log
    ms="${EPOCHREALTIME:-}"
    case "$ms" in
        *.*) secs="${ms%%.*}"; frac="${ms#*.}"; ms="${secs}${frac:0:3}" ;;
        *)   ms=0 ;;
    esac
    log="${HOME:-/tmp}/.divineos/hook_timing.jsonl"
    # fail-soft: a log append must never block a tool call, and the bail is
    # correct whether or not the record lands.
    if [ -d "${log%/*}" ]; then
        printf '{"id":"%s-%s-%s","hook":"%s","pid":%s,"session":"%s","wpid":"%s","phase":"bailed","ts_ms":%s,"duration_ms":0,"reason":"%s"}\n' \
            "$hook" "$$" "$ms" "$hook" "$$" \
            "${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-}}" "${CLAUDE_PID:-}" \
            "$ms" "$reason" \
            >> "$log" 2>/dev/null  # fail-soft: a log append must never block a tool call, and the bail decision is correct whether or not the record lands
    fi
}

# hook_bail_unless_mentions <hook-name> <input> <word> [word...]
#   Exit 0 -- recording the bail -- unless <input> contains at least one <word>.
#
#   SAFE BY CONSTRUCTION, NOT BY JUDGEMENT. Pass only words the hook's REAL
#   matcher cannot fire without. If the precise matcher is anchored on
#   `git push`, every command it could ever fire on must contain "push", so
#   bailing when "push" is absent cannot produce a false negative -- it only
#   skips work already guaranteed to be wasted.
#
#   Deliberately a dumb substring test. Every narrowing here is a chance to
#   silently disarm a gate, and the anchored matcher downstream must stay the
#   only thing making real decisions. A false negative here is invisible; that
#   asymmetry is the whole reason this stays dumb.
hook_bail_unless_mentions() {
    local hook="$1" input="$2"
    shift 2
    local word
    for word in "$@"; do
        case "$input" in
            *"$word"*) return 0 ;;
        esac
    done
    hook_bail_and_log "$hook" "command-cannot-contain: $*"
    exit 0
}
