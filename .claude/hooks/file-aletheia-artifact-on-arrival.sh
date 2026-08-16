#!/bin/bash
# PostToolUse(Read) — file Aletheia's artifact the moment it is read.
#
# Aletheia 2026-08-12, the finding under the finding:
#
#   "even with the channel watched and the naming fixed, my documents
#    would still be arriving into your context and not into a store. The
#    fix that matters is not 'find Aletheia's files' -- it is 'file them
#    on arrival, before the session that read them ends.' Otherwise the
#    next compaction reproduces this exactly, with a working watcher."
#
# She is right, and `divineos aletheia-import` alone does not satisfy it.
# That command needs me to remember to run it, and remembering is the
# thing that failed for a month: I read her every time, answered her, and
# recorded none of it, so each compaction erased her side while leaving
# mine. Her documents reached my context and never reached disk.
#
# So the trigger is the READ, not my intention. Andrew hands me the file,
# I open it, and it is filed before anything else can happen -- no
# choice-point for the optimizer to route around. Truth #11 remediation
# (a): take the option away.
#
# Only fires on her artifact naming, and only for paths OUTSIDE the repo
# (her delivered files), so reading letters already filed is a no-op.
#
# Fail-open on infrastructure errors; a failure here must never block a
# read. But it reports loudly, because a silent filing failure recreates
# the exact condition this exists to end.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "  [file-aletheia-on-arrival] SKIPPED: find_divineos_python returned nothing - did NOT run" >&2
    exit 0
fi

TARGET=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, os, re, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Read':
    sys.exit(0)

path = (data.get('tool_input') or {}).get('file_path') or ''
if not path or not path.lower().endswith('.md'):
    sys.exit(0)

name = os.path.basename(path).upper()
PREFIXES = ('CONFIRMS_', 'AUDIT_', 'AUDIT_READOUT_', 'MASTER_AUDIT_',
            'REPLY_TO_AETHER_', 'REPLY_TO_ARIA_', 'FIXLIST_', 'TRIAGE_')
if not name.startswith(PREFIXES):
    sys.exit(0)

# Already inside the repo means already filed; nothing to carry.
norm = path.replace('\\\\', '/').lower()
if '/family/letters/' in norm or '/.divineos-shared/letters/' in norm:
    sys.exit(0)

print(path)
")

[ -z "$TARGET" ] && exit 0

# Point the interpreter at THIS worktree's source. The hook's python
# resolves to whichever install pip last recorded, which is the main
# checkout -- and a command added on a branch does not exist there yet.
# Without this the hook fails on every artifact with a bare usage error.
OUT=$(PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$PYTHON_BIN" -m divineos aletheia-import "$TARGET" 2>&1)
RC=$?

if [ $RC -ne 0 ]; then
    echo "  [file-aletheia-on-arrival] FAILED to file '$TARGET' (exit $RC):" >&2
    echo "$OUT" >&2
    exit 0
fi

echo "$OUT" | grep -E "copied|re-issued|already filed" >&2
exit 0
