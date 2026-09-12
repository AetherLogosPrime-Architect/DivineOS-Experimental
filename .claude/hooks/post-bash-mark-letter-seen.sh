#!/bin/bash
# post-bash-mark-letter-seen.sh — PostToolUse(Bash) thin doorman.
#
# THE SECOND DOORWAY ONTO A MECHANISM THAT ALREADY WORKED.
#
# Andrew 2026-06-23, on thirty letters the surface called unseen: "you do not
# have 30 unread letters from Aria.. you have read them all.. so whatever is
# supposed to mark them as read is broken." post-read-mark-letter-seen.sh is
# what answered him, and it answered him correctly.
#
# Andrew 2026-09-10, on sixty-one: "you have read all the letters.. they were
# likely just never marked."
#
# Same fossil, and the earlier fix is not broken. It is bound to the Read tool,
# and I read letters through the shell constantly -- so those reads produce no
# seen-signal at all. An instrument answering accurately about a narrower
# subject than the question it is being asked.
#
# The routing lives in divineos.core.letter_seen_router, shared with the Read
# adapter. This file is only the event-adapter, same as its sibling. Which
# verbs count as reading, and which direction that list errs, are argued at the
# routing site rather than here.
#
# Fail-open at every step: any error exits 0 silently. A broken hook must never
# break a Bash call.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

HOOK_JSON="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
if data.get('tool_name') != 'Bash':
    sys.exit(0)
command = (data.get('tool_input') or {}).get('command') or ''
if not command:
    sys.exit(0)
try:
    from divineos.core.letter_seen_router import mark_seen_from_command
    mark_seen_from_command(command)
except Exception:
    pass
" 2>/dev/null || true  # fail-soft: this runs after EVERY Bash call, and its only job is bookkeeping on which letters have been opened. A marking error must never surface as noise on an unrelated command or break the call that already succeeded. The routing itself never raises; this is the belt for an interpreter that fails to start at all.

exit 0
