#!/bin/bash
# Post-push verify-landing — auto-confirms that a claimed push actually
# landed on origin, and surfaces the result so the agent cannot claim
# "everything on origin" without evidence.
#
# ROOT PATTERN: Andrew 2026-07-01, "you holding it in context is not
# reliable.. automation encodes your will so it is always done whether
# you remember or not." Applied recursively by Aletheia 2026-07-02: the
# verify-claim discipline itself is what should be automated. Manual
# "I verified this landed" depends on remembering to run `git ls-remote`
# or `git rev-parse`. That memory decays. This hook runs the check on
# every push automatically.
#
# Fired three times tonight where the verify-claim discipline slipped:
# 1. Claimed a push landed before verifying (letter to Aria)
# 2. Claimed a round CONFIRMS was filed with wrong tip/tree hashes
# 3. Claimed "everything on origin" while two letters were uncommitted
#
# All three would have been prevented by structural verification at
# push-time.
#
# APPLIES the mechanical-vs-reasoning-automation principle (Andrew
# 2026-07-01): whether commits are actually on origin is *mechanical*
# (checkable with git ls-remote). No reasoning involved. So automate.
#
# COMPLEMENTS post-push-audit-visibility.sh:
# - This hook runs FIRST, verifies landing
# - If verified, audit-visibility can trust its input state
# - If not verified, this hook surfaces the mismatch prominently
#
# Hook shape: PostToolUse on Bash. Reads tool_input JSON from stdin,
# checks if the command was `git push` and the exit code was 0, then
# compares local HEAD to remote branch tip. Fail-open on internal
# errors (never blocks anything) — but LOUD on landing-mismatch (that
# IS the whole point).

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

INPUT=$(cat)

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

RESULT=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys, re
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    tr = d.get('tool_response') or {}
    cmd = ti.get('command') or ''
    exit_code = tr.get('exit_code')
    is_push = bool(re.search(r'\\bgit\\s+push\\b', cmd))
    ok = (exit_code == 0)
    print(f'{is_push}|{ok}')
except Exception:
    print('False|False')
" 2>/dev/null)

IS_PUSH="${RESULT%%|*}"
OK="${RESULT##*|}"

# Only proceed on successful git push.
if [ "$IS_PUSH" != "True" ] || [ "$OK" != "True" ]; then
    exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
[ -z "$BRANCH" ] || [ "$BRANCH" = "HEAD" ] && exit 0

LOCAL_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
[ -z "$LOCAL_SHA" ] && exit 0

# Ask origin what the actual tip is. Fresh network call — this is the
# whole point: don't trust the local remote-tracking ref, which can be
# stale; get the truth from origin directly.
REMOTE_SHA=$(git ls-remote --heads origin "$BRANCH" 2>/dev/null | awk '{print $1}' | head -1)

# If ls-remote fails (network hiccup, auth), be honest about the failure
# rather than silent-pass. The verify-claim discipline says: a check
# that couldn't run is not the same as a check that passed.
if [ -z "$REMOTE_SHA" ]; then
    echo "" >&2
    echo "  [verify-landing] could NOT reach origin to verify landing" >&2
    echo "  [verify-landing]   local HEAD: ${LOCAL_SHA:0:12}" >&2
    echo "  [verify-landing]   branch:     $BRANCH" >&2
    echo "  [verify-landing]   run 'git ls-remote origin $BRANCH' manually to check" >&2
    exit 0
fi

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
    # Landed. Brief confirmation — enough to see, not enough to be noise.
    echo "" >&2
    echo "  [verify-landing] VERIFIED origin/$BRANCH == HEAD (${LOCAL_SHA:0:12})" >&2
else
    # Mismatch — loud. This is the whole reason the hook exists.
    echo "" >&2
    echo "  [verify-landing] !!! LANDING MISMATCH — push claimed success but hashes differ" >&2
    echo "  [verify-landing]   local  HEAD: $LOCAL_SHA" >&2
    echo "  [verify-landing]   origin tip:  $REMOTE_SHA" >&2
    echo "  [verify-landing]   branch:      $BRANCH" >&2
    echo "  [verify-landing]   INVESTIGATE — 'push succeeded' does not mean 'commits landed'" >&2
fi

exit 0
