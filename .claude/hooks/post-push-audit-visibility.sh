#!/bin/bash
# INTENTIONALLY UNWIRED (2026-07-16, Aletheia cold-audit finding #2):
# Git has NO client-side post-push hook (only pre-push, and server-side
# post-receive). Attempts to invoke this from pre-push would run BEFORE
# the push succeeds, which defeats the purpose (prep-relay should reflect
# what actually landed on origin).
#
# Reach-for gap this hook wants to close (Andrew 2026-07-01: "you wont
# remember to reach for that tool son") remains OPEN. Candidate future
# wiring paths: (a) PostToolUse hook on Bash matching "git push" +
# post-check that push actually succeeded, (b) polling background monitor
# that watches for new commits on origin, (c) manual invocation via
# `divineos audit prep-relay` remains available in the interim.
#
# Follow-up task filed. Marker present so this stops being flagged as
# undocumented-dark on future audit passes.
#
# Post-push audit-visibility — auto-prepare the audit relay package.
#
# ROOT PATTERN: Andrew 2026-07-01, "you wont remember to reach for that
# tool son.. you will forget and then forget it even exists.. automation
# is how you wield the tool properly." The `divineos audit prep-relay`
# command was built 2026-05-18 (Aletheia's structural fix for the
# describe-then-CONFIRMS pattern). It was zero-uses in the event ledger
# because I never reached for it manually.
#
# THIS HOOK closes the reach-for gap structurally: on ANY successful
# `git push`, auto-run prep-relay against origin/main..HEAD and save the
# ready-to-copy relay template to ~/.divineos/pending-audits/. Andrew
# grabs the file when he's ready to send the package to Aletheia.
#
# APPLIES THE PRINCIPLE Andrew named 2026-07-01: "if the answer to
# 'should X ever NOT happen' is no, automate X." There is no case where
# I would want a substantive push to NOT have an audit package ready.
# So the preparation is mandatory-mechanical; the send-decision (which
# is reasoning, not mechanical) stays with Andrew — the file waiting in
# ~/.divineos/pending-audits/ IS the doorman that puts the material in
# front of him.
#
# COMPLEMENT to post-commit-audit-visibility.sh (which WARNS when work
# is unpushed). This hook fires AFTER push succeeds and PREPARES the
# next step so Andrew doesn't have to remember either half.
#
# Hook shape: PostToolUse on Bash. Reads tool_input JSON from stdin,
# checks if the command was `git push` and the exit code was 0, then
# runs prep-relay. Fail-open: any error exits 0.

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

# Read the PostToolUse payload from stdin. Format: JSON with
# tool_input.command, tool_response.stdout, tool_response.stderr,
# tool_response.exit_code (Claude Code hook contract).
INPUT=$(cat)

# Extract command + exit code. Python because bash JSON parsing is grim.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

RESULT=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    tr = d.get('tool_response') or {}
    cmd = ti.get('command') or ''
    exit_code = tr.get('exit_code')
    # Only fire on git push commands. Match 'git push' with word-boundary
    # after — so 'git pushed' or 'git-pushd' don't false-fire.
    import re
    is_push = bool(re.search(r'\\bgit\\s+push\\b', cmd))
    ok = (exit_code == 0)
    print(f'{is_push}|{ok}|{cmd[:80]}')
except Exception as e:
    print(f'False|False|error: {e}')
" 2>/dev/null)

IS_PUSH="${RESULT%%|*}"
REST="${RESULT#*|}"
OK="${REST%%|*}"

# Only proceed on successful git push.
if [ "$IS_PUSH" != "True" ] || [ "$OK" != "True" ]; then
    exit 0
fi

# Ensure the pending-audits directory exists.
PENDING_DIR="$HOME/.divineos/pending-audits"
mkdir -p "$PENDING_DIR" 2>/dev/null || exit 0

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
# Sanitize branch for filename — replace slashes with underscores.
BRANCH_SAFE="${BRANCH//\//_}"
TS=$(date -u +%Y-%m-%dT%H%M%SZ 2>/dev/null || echo "unknown")
OUT="$PENDING_DIR/${TS}-${BRANCH_SAFE}.txt"

# Determine the range. If we're on main, range is HEAD~1..HEAD (the just-
# pushed commit). Otherwise, origin/main..HEAD (the branch's ahead-of-main
# commits).
if [ "$BRANCH" = "main" ]; then
    RANGE="HEAD~1..HEAD"
else
    RANGE="origin/main..HEAD"
fi

# Run prep-relay. Capture stdout+stderr into the pending file.
{
    echo "# Auto-prepared audit relay — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# Branch: $BRANCH"
    echo "# Range: $RANGE"
    echo "# Triggered by: successful git push"
    echo ""
    "$PYTHON_BIN" -m divineos audit prep-relay --range "$RANGE" 2>&1
} > "$OUT" 2>&1

# Print a brief notification to stderr so Andrew sees it above the push
# summary in the chat. Keep it short — the file path is the load-bearing
# information; details are in the file itself.
echo "" >&2
echo "  [post-push] audit relay prepared: $OUT" >&2
echo "  [post-push]   grab it when ready to send to Aletheia (or delete to skip)" >&2

exit 0
