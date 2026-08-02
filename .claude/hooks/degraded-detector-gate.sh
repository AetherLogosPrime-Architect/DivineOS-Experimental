#!/bin/bash
# PreToolUse — a guard that reported it could not run must cost something.
#
# WHY. On 2026-08-02 Andrew found 24 orphaned processes on his machine. The
# sweep built to catch exactly that had been printing a perfect warning at
# every SessionStart for days -- names the detector, names the cause, names
# the fix, refuses to call itself clean. I read it at the top of the session
# and worked anyway.
#
# Andrew: "if detectors are working and you are just ignoring them they dont
# do much good so it needs teeth."
#
# More warning would not have helped. The message was already loud, specific
# and correct; the unreliable component is me, and SessionStart output is
# print-only -- structurally unable to require anything.
#
# NOT A CAGE, and the substrate's 92 bypass events in 14 days say that matters:
#   - self-healing degradations never reach this gate
#   - a fixed detector clears itself on its next successful run, with no
#     acknowledgement step to perform or fake
#   - an unfixable one is deferred in one command, with a written reason
# The only state that blocks is broken + unfixable + undeferred, which is a
# down guard nobody has spoken about.
#
# Fail-open throughout: any error exits 0. A gate about broken detectors must
# not become the broken detector.

set -u
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

export PYTHONIOENCODING=utf-8

BLOCK_MSG="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null
import json, os, sys

try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)

# Substantive work only. Reads, searches and the substrate-consult commands
# stay open -- blocking those would block the investigation of the block.
if data.get('tool_name', '') not in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
    sys.exit(0)

try:
    from divineos.core.degraded_detectors import blocking_degradations, format_block
except Exception:
    sys.exit(0)

try:
    entries = blocking_degradations()
except Exception:
    sys.exit(0)

if not entries:
    sys.exit(0)

sys.stdout.write(format_block(entries))
sys.exit(2)
PYEOF
)"
RC=$?

if [ "$RC" -eq 2 ] && [ -n "$BLOCK_MSG" ]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi
exit 0
