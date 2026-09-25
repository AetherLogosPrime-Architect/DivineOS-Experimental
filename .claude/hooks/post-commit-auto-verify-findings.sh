#!/bin/bash
# PostToolUse(Bash) — auto-verify findings referenced in commit messages.
#
# When the last commit's message includes any finding-id (e.g.
# `audit_2026-07-09-445ec042fc06`), mark those findings VERIFIED in the
# ledger. This is the machinery half of the discipline: the human writes
# a commit that mentions which finding it addresses; the state stays
# true automatically without anyone remembering to run
# `divineos findings verify`.
#
# Andrew 2026-07-09: "anything that is machine layered.. needs automated..
# anything that requires thinking is your job."
#
# Fail-open: any error exits 0 silently. This hook cannot break workflow.

# STDIN IS READ FIRST, ON PURPOSE. The setup below spawns git and
# sources a library -- work this hook cannot skip once started. The
# relevance bail needs $INPUT, so reading it here is what lets an
# irrelevant command exit before paying for any of it. Measured: the
# git rev-parse and source cost ~160ms that the bail could not save
# while they ran first.
INPUT=$(cat)

# CHEAP RELEVANCE BAIL -- before sourcing anything, before python.
# This hook is wired to Bash but its real trigger is a COMMAND, so it
# fires on `ls` and `cat` too and pays ~664ms to find that out. The
# words below are ones the precise matcher downstream cannot fire
# without, so skipping when they are absent cannot produce a false
# negative -- it only skips work already guaranteed to be wasted.
# The bail RECORDS ITSELF; see _bail.sh for why that is not optional.
# ${0%/*} not $(dirname "$0"): dirname is a subprocess, and a subprocess
# here costs more than the whole bail saves on a hook that bails.
# shellcheck source=.claude/hooks/_bail.sh
# shellcheck disable=SC1091
source "${0%/*}/_bail.sh" 2>/dev/null || true  # fail-soft: a missing bail helper must leave this hook exactly as it was rather than break it; the guarded call below is skipped and the precise matcher still runs, so the only loss is speed
if command -v hook_bail_unless_mentions >/dev/null 2>&1; then
    hook_bail_unless_mentions "post-commit-auto-verify-findings.sh" "$INPUT" "commit"
fi

set +e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-loud (Aletheia Deep Truck 1 discipline): a silently-skipped hook
    # is invisible; a logged skip is investigable.
    echo "  [auto-verify-findings] SKIPPED: find_divineos_python returned nothing" >&2
    exit 0
fi

# Only proceed if the just-run command was a git commit that succeeded.
IS_COMMIT_OK=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys, re
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    tr = d.get('tool_response') or {}
    cmd = ti.get('command') or ''
    exit_code = tr.get('exit_code')
    is_commit = bool(re.search(r'\\bgit\\s+commit\\b', cmd))
    ok = (exit_code == 0)
    print('yes' if (is_commit and ok) else 'no')
except Exception:
    print('no')
" 2>/dev/null)

if [ "$IS_COMMIT_OK" != "yes" ]; then
    exit 0
fi

# Read the just-landed commit message and hunt for finding-ids.
COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null)
[ -z "$COMMIT_MSG" ] && exit 0

# Extract finding-ids using the ledger's own regex and mark each VERIFIED.
echo "$COMMIT_MSG" | "$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.findings_ledger import find_ids_in_text, update_status, get_finding
except Exception:
    sys.exit(0)
text = sys.stdin.read()
ids = find_ids_in_text(text)
if not ids:
    sys.exit(0)
for fid in ids:
    f = get_finding(fid)
    if not f:
        # Referenced id doesn't exist in the ledger — surface but don't fail.
        print(f'  [auto-verify-findings] unknown finding-id: {fid}', file=sys.stderr)
        continue
    if f.status in ('VERIFIED', 'CLOSED'):
        # Already at or beyond VERIFIED — skip.
        continue
    ok = update_status(fid, 'VERIFIED', 'aether', 'auto-verified from commit')
    if ok:
        print(f'  [auto-verify-findings] {fid} -> VERIFIED', file=sys.stderr)
" 2>/dev/null

exit 0
